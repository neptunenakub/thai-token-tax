"""Stage 2, `ttt count`: run every tokenizer in registry/models.toml over every sentence.

Reads  registry/models.toml, the normalized sentences from `ttt prepare`
Writes one result set per source (open, openai, gemini, anthropic):
       counts_<date>_<source>.csv        one row per sentence x language x tokenizer
       counts_<date>_<source>.meta.json  what was measured (versions, hashes, overhead)
                                         and what was blocked, with the real error

A model marked `sample_of = "<other model>"` in the registry is counted on a fixed
random sample of sentences only. `ttt analyze` then checks whether it gives exactly
the same counts as the fully measured model, so one tokenizer generation does not
need thousands of repeated API calls.
"""
from __future__ import annotations

import csv
import json
import random
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from .. import Stop, new_file, sha256_file, utc_now
from ..data import DATASET, SOURCE_FILE, SPLIT, load_sentences
from . import tiktoken_counter
from .base import Blocked, Counter

COLUMNS = [
    "run_date_utc", "dataset", "split", "sent_id", "lang",
    "family", "model_id", "tokenizer", "library", "n_chars", "n_tokens",
]
# counter kind -> the source (result file) it belongs to
SOURCE_OF = {
    "tiktoken": "open", "hf": "open",
    "openai_api": "openai", "gemini": "gemini", "anthropic": "anthropic",
}
SOURCES = ("open", "openai", "gemini", "anthropic")
RATE_LIMITS: dict[str, float] = {}  # source -> requests per minute, from the registry
SAMPLE_SIZE = 100
SAMPLE_SEED = 20261110


def load_models(path: Path) -> tuple[list[dict], dict]:
    """-> ([model entries], openai_lookup table) from registry/models.toml."""
    reg = tomllib.loads(path.read_text(encoding="utf-8"))
    models = reg["model"]
    ids = [m["id"] for m in models]
    if len(set(ids)) != len(ids):
        raise Stop(f"{path}: duplicate model id")
    for m in models:
        if m["counter"] not in SOURCE_OF:
            raise Stop(f"{path}: {m['id']} has unknown counter {m['counter']!r}")
        if not m.get("family"):
            raise Stop(f"{path}: {m['id']} has no family")
        if "sample_of" in m and m["sample_of"] not in ids:
            raise Stop(f"{path}: {m['id']} is a sample of unknown model {m['sample_of']!r}")
    RATE_LIMITS.update(reg.get("rate_limits", {}))
    return models, reg.get("openai_lookup", {})


def build_counter(entry: dict, cache_dir: Path) -> Counter:
    """Create the counter a registry entry asks for. Raises Blocked if it cannot run.
    Imports are local so that using one provider never needs another provider's library."""
    kind, model_id = entry["counter"], entry["id"]
    rpm = RATE_LIMITS.get(SOURCE_OF[kind])
    if kind == "tiktoken":
        return tiktoken_counter.TiktokenCounter(model_id, entry["encoding"], cache_dir)
    if kind == "hf":
        from .hf_counter import HFCounter

        return HFCounter(model_id, entry.get("revision"), cache_dir)
    if kind == "openai_api":
        from .openai_api_counter import OpenAIApiCounter

        return OpenAIApiCounter(model_id, cache_dir, rpm)
    if kind == "gemini":
        from .gemini_counter import GeminiCounter

        return GeminiCounter(model_id, cache_dir, rpm)
    from .anthropic_counter import AnthropicCounter

    return AnthropicCounter(model_id, cache_dir, rpm)


def sample_ids(sent_ids: list[int]) -> list[int]:
    """The fixed random sample used for `sample_of` models."""
    return sorted(random.Random(SAMPLE_SEED).sample(sent_ids, min(SAMPLE_SIZE, len(sent_ids))))


def run(
    root: Path, out_dir: Path, sources=SOURCES, build=build_counter, only=None, label=None,
    dataset: str = DATASET,
) -> list[Path]:
    """Count the chosen sources. `build` is replaceable so tests need no network.

    `only` limits the run to some model ids; `label` then names the add-on result set
    (counts_<date>_<source>-<label>.csv), so earlier files are never overwritten."""
    if only and not label:
        raise Stop("--model needs --label: a partial run is saved as its own labelled result set")
    models, openai_lookup = load_models(root / "registry" / "models.toml")
    sent_ids, texts = load_sentences(root, dataset)
    dataset_sha = json.loads((root / "data" / SOURCE_FILE[dataset]).read_text(encoding="utf-8"))
    dataset_sha = dataset_sha["normalized_tsv"]["sha256"]
    sample = set(sample_ids(sent_ids))
    written = []

    for source in sources:
        entries = [m for m in models if SOURCE_OF[m["counter"]] == source and (not only or m["id"] in only)]
        if not entries:
            continue
        name = f"{source}-{label}" if label else source
        started = datetime.now(UTC)
        date = started.strftime("%Y-%m-%d")
        csv_path = new_file(out_dir / f"counts_{date}_{name}.csv")
        meta_path = new_file(csv_path.with_suffix(".meta.json"))
        print(f"[{source}] {len(sent_ids)} sentences x {len(texts)} languages x {len(entries)} models")

        measured, blocked, rows = [], [], []
        for entry in entries:
            wanted = [i for i, s in enumerate(sent_ids) if "sample_of" not in entry or s in sample]
            try:
                counter = build(entry, root / ".cache")
                counts = {lang: counter.count([lines[i] for i in wanted]) for lang, lines in texts.items()}
                info = {"family": entry["family"], "counter": entry["counter"], **counter.describe()}
            except Blocked as e:
                blocked.append({"family": entry["family"], "model_id": entry["id"], **e.record()})
                print(f"  BLOCKED  {entry['id']}: {e.reason} {blocked[-1]['error_first_line'][:120]}")
                continue
            info["coverage"] = "sample" if "sample_of" in entry else "full"
            if "sample_of" in entry:
                info["sample_of"] = entry["sample_of"]
            info["sentences_counted"] = len(wanted)
            for lang, lines in texts.items():
                for i, tokens in zip(wanted, counts[lang], strict=True):
                    rows.append([
                        date, dataset, SPLIT, sent_ids[i], lang, info["family"], info["model_id"],
                        info["tokenizer"], info["library"], len(lines[i]), tokens,
                    ])
            measured.append(info)
            print(f"  ok       {entry['id']} ({info['coverage']})")

        meta = {
            "source": name,
            "run_started_utc": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_finished_utc": utc_now(),
            "dataset": {
                "name": dataset, "split": SPLIT, "sentences": len(sent_ids),
                "languages": list(texts), "sha256": dataset_sha,
            },
            "what_is_counted": "content tokens of the normalized sentence; no BOS/EOS/chat template, "
                               "and for API sources the measured fixed overhead is subtracted",
            "n_chars_definition": "Unicode code points of the normalized sentence",
            "sample": {"seed": SAMPLE_SEED, "size": len(sample), "sent_ids": sorted(sample)},
            "python": sys.version.split()[0],
            "measured": measured,
            "blocked": blocked,
        }
        if source == "open":
            meta["openai_encoding_lookup"] = {
                "method": "tiktoken.encoding_name_for_model(model_id); null = not known to this tiktoken",
                "source": tiktoken_counter.LOOKUP_SOURCE,
                "models_page": openai_lookup.get("models_page"),
                "models_page_fetched": openai_lookup.get("fetched"),
                "model_to_encoding": tiktoken_counter.lookup_models(openai_lookup.get("model_ids", [])),
            }
        blocked_path = out_dir / f"counts_{date}_{name}.blocked.json"
        blocked_path.unlink(missing_ok=True)
        if not measured:
            # Nothing measured: leave no result set, only a record of why. It is
            # replaced when the source is unblocked later the same day.
            blocked_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"[{source}] nothing measured, {len(blocked)} blocked -> {blocked_path}")
            continue

        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(COLUMNS)
            writer.writerows(rows)
        meta["counts_csv"] = {"file": csv_path.name, "sha256": sha256_file(csv_path)}
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[{source}] measured {len(measured)}, blocked {len(blocked)} -> {csv_path}")
        written.append(csv_path)
    return written
