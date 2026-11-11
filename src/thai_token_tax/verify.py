"""`ttt verify`: recount in a second, independent way and report any disagreement.

Reads  a counts CSV and its .meta.json (same repo revisions as the count run)
Writes verification_<date>_<source>.json next to it. The counts file is never changed.

  tiktoken encodings
    - recount from scratch == CSV
    - decode(encode(text)) == text for every sentence (nothing lost)
  Hugging Face tokenizers
    - transformers.AutoTokenizer recount == CSV  (what a transformers user gets)
    - decode(encode(text)) == text
    - number of <unk> tokens                     (an <unk> would hide real cost)
    - if the repo also ships a SentencePiece tokenizer.model: recount with the
      sentencepiece library. A difference is reported, not hidden.
  API counters (fully measured models): is the subtracted overhead really constant?
    - length:  "a", "a a", ... up to 500 words. raw count - number of words must be
               the same overhead every time (one more " a" = exactly one more token).
    - content: for real sentences X, Y, Z in both languages, the raw count of the
               conversation [X, Y, Z] minus the raw counts of X, Y and Z alone must be
               one constant. Any overhead that depended on script, language or length
               would make it vary.
    - repeat:  50 sentences are sent a second time; the endpoint must give the same answer.
    - OpenAI models that tiktoken knows: API count - overhead == tiktoken, every sentence.
"""
from __future__ import annotations

import csv
import json
import os
import random
from collections import defaultdict
from pathlib import Path

from . import Stop, counters, new_file
from .analyze import COUNTS_NAME
from .data import load_sentences

LENGTH_STEPS = (1, 2, 5, 20, 100, 500)
CONTENT_TRIPLES = 24
CONTENT_SEED = 20261110
REPEATS = 50


def load_csv_counts(path: Path) -> dict:
    """-> {model_id: {lang: {sent_id: tokens}}}"""
    by_id: dict = defaultdict(lambda: defaultdict(dict))
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            by_id[row["model_id"]][row["lang"]][int(row["sent_id"])] = int(row["n_tokens"])
    return by_id


def mismatches(expected: dict[int, int], sent_ids: list[int], got: list[int]) -> int:
    return sum(expected[s] != g for s, g in zip(sent_ids, got, strict=True))


def check_tiktoken(info: dict, sent_ids, texts: dict, expected: dict) -> dict:
    import tiktoken

    encoding = tiktoken.get_encoding(info["tokenizer"])
    result = {}
    for lang, lines in texts.items():
        tokens = [encoding.encode(t, disallowed_special=()) for t in lines]
        result[lang] = {
            "recount_mismatch": mismatches(expected[lang], sent_ids, [len(t) for t in tokens]),
            "roundtrip_exact": sum(encoding.decode(t) == s for t, s in zip(tokens, lines, strict=True)),
        }
    return result


def check_hf(info: dict, sent_ids, texts: dict, expected: dict, cache_dir: Path) -> dict:
    import sentencepiece
    from huggingface_hub import hf_hub_download
    from huggingface_hub.utils import EntryNotFoundError
    from tokenizers import Tokenizer
    from transformers import AutoTokenizer

    repo, revision = info["model_id"], info["repo_revision"]
    token = os.environ.get("HF_TOKEN") or None
    common = {"revision": revision, "cache_dir": cache_dir / "hf", "token": token}
    path = hf_hub_download(repo, "tokenizer.json", **common)
    tokenizer = Tokenizer.from_file(path)
    tokenizer.no_truncation()
    tokenizer.no_padding()
    unk = (json.loads(Path(path).read_text(encoding="utf-8")).get("model") or {}).get("unk_token")
    unk_id = tokenizer.token_to_id(unk) if unk else None
    auto = AutoTokenizer.from_pretrained(repo, trust_remote_code=False, **common)
    try:
        sp_path = hf_hub_download(repo, "tokenizer.model", **common)
        sp = sentencepiece.SentencePieceProcessor(model_file=sp_path)
    except EntryNotFoundError:
        sp = None

    result: dict = {"transformers_class": type(auto).__name__, "has_sentencepiece_model": sp is not None}
    for lang, lines in texts.items():
        encoded = tokenizer.encode_batch(lines, add_special_tokens=False)
        decoded = [tokenizer.decode(e.ids, skip_special_tokens=False) for e in encoded]
        auto_counts = [len(auto(t, add_special_tokens=False)["input_ids"]) for t in lines]
        result[lang] = {
            "recount_mismatch": mismatches(expected[lang], sent_ids, [len(e.ids) for e in encoded]),
            "roundtrip_exact": sum(d == s for d, s in zip(decoded, lines, strict=True)),
            "unk_tokens": sum(e.ids.count(unk_id) for e in encoded) if unk_id is not None else 0,
            "transformers_mismatch": mismatches(expected[lang], sent_ids, auto_counts),
            "transformers_total": sum(auto_counts),
        }
        if sp is not None:
            sp_counts = [len(sp.encode(t)) for t in lines]
            result[lang]["sentencepiece_mismatch"] = mismatches(expected[lang], sent_ids, sp_counts)
            result[lang]["sentencepiece_total"] = sum(sp_counts)
    return result


def check_api(counter, sent_ids, texts: dict, expected: dict) -> dict:
    """Is the overhead the counter subtracted really a constant? See the module docstring."""
    length = {k: counter.raw_count([" ".join(["a"] * k)]) - k for k in LENGTH_STEPS}

    rng = random.Random(CONTENT_SEED)
    pool = [(lang, i) for lang in texts for i in range(len(sent_ids))]
    differences = []
    for _ in range(CONTENT_TRIPLES):
        turns = [texts[lang][i] for lang, i in rng.sample(pool, 3)]
        alone = sum(counter.raw_count([t]) for t in turns)
        differences.append(counter.raw_count(turns) - alone)

    repeat_mismatch = 0
    for lang, i in rng.sample(pool, min(REPEATS, len(pool))):
        counter.wait_for_turn()
        repeat_mismatch += counter.call([texts[lang][i]]) != counter.raw_count([texts[lang][i]])

    result = {
        "overhead_subtracted": counter.overhead,
        "repeat_check_sentences": min(REPEATS, len(pool)),
        "repeat_check_mismatch": repeat_mismatch,
        "length_check_raw_minus_words": length,
        "length_check_constant": set(length.values()) == {counter.overhead},
        "content_check_triples": CONTENT_TRIPLES,
        "content_check_distinct_differences": sorted(set(differences)),
        "content_check_constant": len(set(differences)) == 1,
    }
    try:
        import tiktoken

        encoding = tiktoken.encoding_for_model(counter.model_id)
    except KeyError:
        result["tiktoken_check"] = "tiktoken does not know this model"
    else:
        result["tiktoken_check"] = {
            "encoding": encoding.name,
            **{
                lang: mismatches(
                    expected[lang], sent_ids, [len(encoding.encode(t, disallowed_special=())) for t in lines]
                )
                for lang, lines in texts.items()
            },
        }
    return result


def run(root: Path, counts_csv: Path, build=counters.build_counter) -> Path:
    match = COUNTS_NAME.search(counts_csv.name)
    if not match:
        raise Stop(f"{counts_csv.name} is not named counts_<date>_<source>.csv")
    out = new_file(counts_csv.with_name(f"verification_{match[1]}_{match[2]}.json"))
    meta = json.loads(counts_csv.with_suffix(".meta.json").read_text(encoding="utf-8"))
    csv_counts = load_csv_counts(counts_csv)
    all_ids, all_texts = load_sentences(root, meta["dataset"]["name"])
    entries = {m["id"]: m for m in counters.load_models(root / "registry" / "models.toml")[0]}

    checks = []
    for info in meta["measured"]:
        expected = csv_counts[info["model_id"]]
        keep = [i for i, s in enumerate(all_ids) if s in expected[next(iter(all_texts))]]
        sent_ids = [all_ids[i] for i in keep]
        texts = {lang: [lines[i] for i in keep] for lang, lines in all_texts.items()}
        if info["counter"] == "tiktoken":
            result = check_tiktoken(info, sent_ids, texts, expected)
        elif info["counter"] == "hf":
            result = check_hf(info, sent_ids, texts, expected, root / ".cache")
        elif info["coverage"] == "full":
            result = check_api(build(entries[info["model_id"]], root / ".cache"), sent_ids, texts, expected)
        else:
            continue  # a sampled API model is checked by comparing it with its full model in analyze
        checks.append({"model_id": info["model_id"], **result})
        print(f"  {info['model_id']}: {json.dumps(summary_line(result))}")

    out.write_text(json.dumps({
        "input": counts_csv.name,
        "checks": checks,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return out


def summary_line(result: dict) -> dict:
    """The few fields worth printing: anything that is not as it should be, plus the key facts."""
    if "overhead_subtracted" in result:
        return {k: result[k] for k in (
            "overhead_subtracted", "length_check_constant", "content_check_constant",
            "repeat_check_mismatch", "tiktoken_check")}
    langs = {k: v for k, v in result.items() if isinstance(v, dict)}
    problems = {
        f"{lang}.{key}": value for lang, values in langs.items() for key, value in values.items()
        if (key.endswith("_mismatch") or key == "unk_tokens") and value
    }
    return {"roundtrip": {lang: v["roundtrip_exact"] for lang, v in langs.items()}, "issues": problems}
