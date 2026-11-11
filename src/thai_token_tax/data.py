"""Stage 1, `ttt prepare`: download FLORES-200, check it, normalize it, check alignment.

Reads  registry/languages.toml
Writes data/raw/            the downloaded tarball and the original files (not in git)
       data/flores200_devtest.tsv   normalized sentences, one column per language (not in git)
       data/source.json     where the data came from, hashes, license notes
       data/normalization_log.json   what normalization changed (sentence ids only)

Nothing here is estimated: every value written is read from the downloaded files.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import tarfile
import tomllib
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from . import Stop, sha256_file, utc_now

DATASET, SPLIT = "flores200", "devtest"
FLORES200_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"
# SHA-256 of the tarball as downloaded on 2026-11-10. Meta publishes no checksum; this pin
# makes a later run stop loudly if the upstream file ever changes.
FLORES200_SHA256 = "b8b0b76783024b85797e5cc75064eb83fc5288b41e9654dabc7be6ae944011f6"
MEMBER = "./flores200_dataset/devtest/{code}.devtest"
METADATA_MEMBER = "./flores200_dataset/metadata_devtest.tsv"

# The newer FLORES+ is preferred but gated. We only probe it and record the answer.
FLORES_PLUS_REPO = "openlanguagedata/flores_plus"
FLORES_PLUS_FILE = (
    f"https://huggingface.co/datasets/{FLORES_PLUS_REPO}/resolve/main/devtest/tha_Thai.jsonl"
)

TSV_NAME = "flores200_devtest.tsv"
# The core set is FLORES-200. FLORES+ is a second, separately labelled set (prepare_floresplus).
SOURCE_FILE = {"flores200": "source.json", "floresplus": "source_floresplus.json"}
TSV_FILE = {"flores200": TSV_NAME, "floresplus": "floresplus_devtest.tsv"}
FLORES_PLUS_LICENSE = "CC BY-SA 4.0"
SPOTCHECK_SEED = 20261110
# Control characters that act as whitespace become one space, so words are never glued together.
WHITESPACE_CONTROLS = {"\t", "\n", "\r", "\x0b", "\x0c"}


# --- registry ---------------------------------------------------------------------------

def load_languages(path: Path) -> tuple[str, list[str]]:
    """-> (baseline code, [target codes]) from registry/languages.toml."""
    reg = tomllib.loads(path.read_text(encoding="utf-8"))
    baseline = reg["baseline"]["code"]
    targets = [t["code"] for t in reg["target"]]
    if not targets:
        raise Stop(f"{path}: no [[target]] language")
    if baseline in targets or len(set(targets)) != len(targets):
        raise Stop(f"{path}: baseline and targets must all be different languages")
    return baseline, targets


# --- normalization and alignment (pure functions, covered by tests) -------------------------

def normalize(text: str) -> tuple[str, dict]:
    """The normalization applied before every tokenizer.

    1. Unicode NFC.
    2. Category Cc (control): TAB/LF/CR/VT/FF -> one space; every other Cc is deleted.
       Category Cf (format: zero-width space/joiner/non-joiner, word joiner, BOM,
       soft hyphen, bidi marks, ...) is deleted.
    3. Leading and trailing whitespace is trimmed.
    Nothing else is touched (inner spaces, NBSP and punctuation stay as they are).
    """
    removed: Counter = Counter()
    composed = unicodedata.normalize("NFC", text)
    kept = []
    for ch in composed:
        category = unicodedata.category(ch)
        if category == "Cc":
            removed[ch] += 1
            if ch in WHITESPACE_CONTROLS:
                kept.append(" ")
        elif category == "Cf":
            removed[ch] += 1
        else:
            kept.append(ch)
    stripped = "".join(kept)
    trimmed = stripped.strip()
    return trimmed, {
        "nfc_changed": composed != text,
        "strip_changed": stripped != composed,
        "trim_changed": trimmed != stripped,
        "changed": trimmed != text,
        "removed": removed,
    }


def split_lines(blob: bytes) -> list[str]:
    """Split on LF only. str.splitlines() also splits on U+2028, VT, FF, ... and would
    silently shift the sentence alignment. A bad UTF-8 byte stops the run."""
    lines = blob.decode("utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def check_alignment(sentences: dict[str, list[str]], expected_rows: int) -> None:
    """Every language must have the same number of non-empty, TAB-free sentences."""
    for code, lines in sentences.items():
        if len(lines) != expected_rows:
            raise Stop(f"{code} has {len(lines)} sentences, expected {expected_rows}: not aligned")
        empty = [i for i, s in enumerate(lines, start=1) if not s]
        if empty:
            raise Stop(f"{code} has empty sentences at {empty[:10]}: alignment cannot be trusted")
        if any("\t" in s for s in lines):
            raise Stop(f"{code}: a TAB survived normalization; the TSV would be corrupt")


def _codepoint(ch: str) -> str:
    return f"U+{ord(ch):04X} {unicodedata.name(ch, '<unnamed>')}"


def normalize_all(lines: list[str]) -> tuple[list[str], dict]:
    """Normalize one language and build its log entry."""
    out, removed = [], Counter()
    ids: dict[str, list[int]] = {"nfc": [], "strip": [], "trim": [], "any": []}
    for i, line in enumerate(lines, start=1):
        new, stats = normalize(line)
        out.append(new)
        removed.update(stats["removed"])
        for key, flag in (("nfc", "nfc_changed"), ("strip", "strip_changed"),
                          ("trim", "trim_changed"), ("any", "changed")):
            if stats[flag]:
                ids[key].append(i)
    return out, {
        "sentences": len(lines),
        "changed_by_nfc": len(ids["nfc"]),
        "changed_by_control_or_format_strip": len(ids["strip"]),
        "changed_by_trim": len(ids["trim"]),
        "changed_total": len(ids["any"]),
        "removed_or_replaced_characters": {_codepoint(c): n for c, n in sorted(removed.items())},
        "sent_ids_changed_by_nfc": ids["nfc"],
        "sent_ids_changed_by_control_or_format_strip": ids["strip"],
        "sent_ids_changed_by_trim": ids["trim"],
    }


# --- download ---------------------------------------------------------------------------

def _http_status(url: str, token: str | None = None) -> int | str:
    """Status of a GET whose body is not read. Only used to probe access."""
    request = urllib.request.Request(url, headers={"User-Agent": "python-urllib"})
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status
    except urllib.error.HTTPError as e:
        return e.code
    except OSError as e:  # network problem: report it, do not guess
        return f"error: {type(e).__name__}: {e}"


def probe_flores_plus() -> dict:
    token = os.environ.get("HF_TOKEN")
    info = {
        "repo": FLORES_PLUS_REPO,
        "probe_file": FLORES_PLUS_FILE,
        "checked_utc": utc_now(),
        "anonymous_http_status": _http_status(FLORES_PLUS_FILE),
        "hf_token_present": bool(token),
    }
    if token:
        info["with_token_http_status"] = _http_status(FLORES_PLUS_FILE, token)
    return info


def download_flores200(raw_dir: Path, previous: dict) -> dict:
    """Download the tarball unless a copy with the pinned hash is already there."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    tar_path = raw_dir / "flores200_dataset.tar.gz"
    info: dict = {"url": FLORES200_URL}
    if tar_path.exists() and sha256_file(tar_path) == FLORES200_SHA256:
        info["download"] = "reused existing file (sha256 matches)"
        if previous.get("downloaded_utc"):  # keep the time of the real download
            info["downloaded_utc"] = previous["downloaded_utc"]
    else:
        part = tar_path.with_suffix(".part")
        with urllib.request.urlopen(FLORES200_URL, timeout=300) as response, part.open("wb") as f:
            while chunk := response.read(1 << 20):
                f.write(chunk)
        part.replace(tar_path)
        info["download"] = "downloaded"
        info["downloaded_utc"] = utc_now()
    info["bytes"] = tar_path.stat().st_size
    info["sha256"] = sha256_file(tar_path)
    if info["sha256"] != FLORES200_SHA256:
        raise Stop(
            f"tarball sha256 {info['sha256']} differs from the pinned {FLORES200_SHA256}. "
            "The upstream file changed; review it before using it."
        )
    return info


def read_members(tar_path: Path, names: list[str], out_dir: Path) -> dict[str, bytes]:
    """Read only the members we need. We write the bytes ourselves, so a path inside the
    archive can never decide where a file lands."""
    out_dir.mkdir(parents=True, exist_ok=True)
    blobs = {}
    with tarfile.open(tar_path, mode="r:gz") as tar:
        for name in names:
            member = tar.getmember(name)
            if not member.isfile():
                raise Stop(f"{name} is not a regular file in the tarball")
            blobs[name] = tar.extractfile(member).read()
            (out_dir / Path(name).name).write_bytes(blobs[name])
    return blobs


# --- the stage --------------------------------------------------------------------------

def prepare(root: Path) -> Path:
    data_dir = root / "data"
    raw_dir = data_dir / "raw" / "flores200"
    source_path = data_dir / "source.json"
    baseline, targets = load_languages(root / "registry" / "languages.toml")
    codes = [baseline, *targets]

    previous = {}
    if source_path.exists():
        previous = json.loads(source_path.read_text(encoding="utf-8")).get("official_release", {})

    print("probing FLORES+ (preferred source, gated) ...")
    plus = probe_flores_plus()
    print(f"  anonymous HTTP {plus['anonymous_http_status']}, HF_TOKEN present: {plus['hf_token_present']}")
    print("fetching the official FLORES-200 release ...")
    release = download_flores200(raw_dir, previous)
    print(f"  {release['download']}, sha256 ok")

    members = {code: MEMBER.format(code=code) for code in codes}
    blobs = read_members(
        raw_dir / "flores200_dataset.tar.gz", [*members.values(), METADATA_MEMBER], raw_dir / "extracted"
    )
    metadata_rows = len(split_lines(blobs[METADATA_MEMBER])) - 1  # minus the header row

    sentences, log = {}, {}
    for code in codes:
        sentences[code], log[code] = normalize_all(split_lines(blobs[members[code]]))
        print(
            f"  {code}: {log[code]['sentences']} sentences, {log[code]['changed_total']} changed "
            f"(nfc {log[code]['changed_by_nfc']}, control/format "
            f"{log[code]['changed_by_control_or_format_strip']}, trim {log[code]['changed_by_trim']})"
        )
    check_alignment(sentences, metadata_rows)

    tsv_path = data_dir / TSV_NAME
    with tsv_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(["sent_id", *codes]) + "\n")
        for i, row in enumerate(zip(*(sentences[c] for c in codes), strict=True), start=1):
            f.write("\t".join([str(i), *row]) + "\n")

    source = {
        "dataset": "FLORES-200",
        "split": SPLIT,
        "languages": codes,
        "sent_id": "1-based line number in the original .devtest files",
        "official_release": release,
        "license": "CC BY-SA 4.0 (https://github.com/facebookresearch/flores/blob/main/README.md)",
        "member_sha256": {name: hashlib.sha256(b).hexdigest() for name, b in blobs.items()},
        "preferred_source_probe_flores_plus": plus,
        "normalized_tsv": {
            "path": tsv_path.relative_to(root).as_posix(),
            "sha256": sha256_file(tsv_path),
            "rows": metadata_rows,
        },
        "prepared_utc": utc_now(),
    }
    source_path.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rules = [line.strip() for line in normalize.__doc__.splitlines()[2:] if line.strip()]
    normlog = {
        "rules": rules,
        "unicode_data_version": unicodedata.unidata_version,
        "python": sys.version.split()[0],
        "aligned_sentences": metadata_rows,
        **log,
        "prepared_utc": utc_now(),
    }
    (data_dir / "normalization_log.json").write_text(
        json.dumps(normlog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    write_spotcheck(data_dir / "spotcheck_20.md", sentences)
    print(f"wrote {tsv_path.relative_to(root)} sha256={source['normalized_tsv']['sha256']}")
    return tsv_path


def write_spotcheck(path: Path, sentences: dict[str, list[str]]) -> None:
    """20 random sentence pairs (fixed seed) for a human to check the translations."""
    n = len(next(iter(sentences.values())))
    picks = sorted(random.Random(SPOTCHECK_SEED).sample(range(1, n + 1), 20))
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(f"# Spot check: 20 random FLORES-200 devtest sentences (seed {SPOTCHECK_SEED})\n\n")
        f.write("Does every translation say the same thing as the baseline?\n\n")
        for i in picks:
            f.write(f"## {i}\n\n")
            for code, lines in sentences.items():
                f.write(f"- {code}: {lines[i - 1]}\n")
            f.write("- OK? [ ]\n\n")


def load_sentences(root: Path, dataset: str = DATASET) -> tuple[list[int], dict[str, list[str]]]:
    """Read the normalized TSV, after checking it is the exact file prepare() recorded."""
    tsv_path = root / "data" / TSV_FILE[dataset]
    source_path = root / "data" / SOURCE_FILE[dataset]
    if not tsv_path.exists() or not source_path.exists():
        raise Stop(f"{tsv_path} is missing. Run `ttt prepare` first.")
    expected = json.loads(source_path.read_text(encoding="utf-8"))["normalized_tsv"]["sha256"]
    if sha256_file(tsv_path) != expected:
        raise Stop(f"{tsv_path.name} does not match data/{source_path.name}. Run `ttt prepare`.")
    ids: list[int] = []
    with tsv_path.open(encoding="utf-8", newline="") as f:
        header = f.readline().rstrip("\n").split("\t")
        texts: dict[str, list[str]] = {code: [] for code in header[1:]}
        for line in f:
            sent_id, *cells = line.rstrip("\n").split("\t")
            ids.append(int(sent_id))
            for code, cell in zip(texts, cells, strict=True):
                texts[code].append(cell)
    return ids, texts


# --- FLORES+ (second dataset, for comparison) -----------------------------------------------

def read_jsonl(blob: bytes) -> dict[int, str]:
    """FLORES+ jsonl: one JSON object per line with an integer `id` and the `text`."""
    rows: dict[int, str] = {}
    for line in blob.decode("utf-8").split("\n"):
        if line:
            record = json.loads(line)
            if record["id"] in rows:
                raise Stop(f"duplicate FLORES+ id {record['id']}")
            rows[record["id"]] = record["text"]
    return rows


def prepare_floresplus(root: Path) -> Path:
    """Fetch FLORES+ devtest from Hugging Face (gated: needs the HF_TOKEN of an account that
    accepted the terms), normalize it like FLORES-200 and compare it with FLORES-200.

    Writes data/floresplus_devtest.tsv and data/spotcheck_floresplus_changes.md (both NOT in git:
    the dataset asks not to be re-hosted where web crawlers can read it) and
    data/source_floresplus.json (provenance and change counts, no sentence text).
    Sentence ids are 1-based like FLORES-200 (FLORES+ ids are 0-based).
    """
    from huggingface_hub import HfApi, hf_hub_download

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise Stop("HF_TOKEN is not set (FLORES+ is gated)")
    repo = FLORES_PLUS_REPO
    baseline, targets = load_languages(root / "registry" / "languages.toml")
    codes = [baseline, *targets]
    try:
        info = HfApi(token=token).dataset_info(repo)
        paths = {
            code: Path(hf_hub_download(
                repo, f"devtest/{code}.jsonl", repo_type="dataset", revision=info.sha,
                token=token, local_dir=root / "data" / "raw" / "floresplus",
            ))
            for code in codes
        }
    except Exception as e:  # gated, offline, ...: stop with the real reason, use nothing else
        raise Stop(f"cannot fetch FLORES+ ({type(e).__name__}): {str(e).splitlines()[0][:200]}") from e

    _, flores200 = load_sentences(root)
    rows = len(next(iter(flores200.values())))
    sentences, log, changed = {}, {}, {}
    for code in codes:
        raw = read_jsonl(paths[code].read_bytes())
        if sorted(raw) != list(range(len(raw))):
            raise Stop(f"FLORES+ {code}: ids are not 0..n-1")
        sentences[code], log[code] = normalize_all([raw[i] for i in range(len(raw))])
        if len(sentences[code]) != rows:
            raise Stop(f"FLORES+ has {len(sentences[code])} {code} sentences, FLORES-200 has {rows}")
        changed[code] = [
            i for i, (a, b) in enumerate(zip(sentences[code], flores200[code], strict=True)) if a != b
        ]
    check_alignment(sentences, rows)
    both = set.intersection(*(set(v) for v in changed.values()))

    tsv_path = root / "data" / TSV_FILE["floresplus"]
    with tsv_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(["sent_id", *codes]) + "\n")
        for i, row in enumerate(zip(*(sentences[c] for c in codes), strict=True), start=1):
            f.write("\t".join([str(i), *row]) + "\n")

    with (root / "data" / "spotcheck_floresplus_changes.md").open("w", encoding="utf-8", newline="\n") as f:
        f.write("# FLORES+ sentences that differ from FLORES-200 (first 30 pairs, after normalization)\n\n")
        f.write("Local file, not in git. Is the FLORES+ version a correction?\n\n")
        for i in sorted(set().union(*changed.values()))[:30]:
            f.write(f"## {i + 1}\n\n")
            for code in codes:
                f.write(f"- {code} FLORES-200: {flores200[code][i]}\n")
                f.write(f"- {code} FLORES+   : {sentences[code][i]}\n")
            f.write("\n")

    modified = info.last_modified
    source = {
        "dataset": "FLORES+",
        "name_in_results": "floresplus",
        "split": SPLIT,
        "languages": codes,
        "source": f"https://huggingface.co/datasets/{repo}",
        "revision": info.sha,
        "dataset_last_modified": modified.strftime("%Y-%m-%dT%H:%M:%SZ") if modified else None,
        "version_in_changelog": "5.0 (CHANGELOG.md at this revision)",
        "license": FLORES_PLUS_LICENSE + " (https://creativecommons.org/licenses/by-sa/4.0/)",
        "redistribution_request": (
            "The dataset terms ask users not to re-host FLORES+ where web crawlers can pick it up "
            "and not to use it as training data. No FLORES+ sentence is committed to this repository."
        ),
        "sent_id": "FLORES+ id + 1: the same 1-based numbering as FLORES-200",
        "files": {
            code: {"path": f"devtest/{code}.jsonl", "sha256": sha256_file(paths[code])} for code in codes
        },
        "normalized_tsv": {
            "path": tsv_path.relative_to(root).as_posix(),
            "sha256": sha256_file(tsv_path),
            "rows": rows,
        },
        "comparison_with_flores200": {
            "pairs": rows,
            **{f"{code}_sentences_that_differ": len(changed[code]) for code in codes},
            "pairs_where_both_languages_differ": len(both),
            "differing_sent_ids": {code: [i + 1 for i in changed[code]] for code in codes},
        },
        "normalization": log,
        "prepared_utc": utc_now(),
    }
    (root / "data" / SOURCE_FILE["floresplus"]).write_text(
        json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"FLORES+ ({FLORES_PLUS_LICENSE}) revision {info.sha[:10]}: {rows} pairs")
    for code in codes:
        print(f"  {code}: {len(changed[code])} sentences differ from FLORES-200 after normalization")
    print(f"  pairs where both languages differ: {len(both)}")
    return tsv_path
