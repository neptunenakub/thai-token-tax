"""Stage 3, `ttt analyze`: merge the raw counts of all sources into one summary table.

Reads  counts_<date>_<source>.csv files, registry/languages.toml (which language is the baseline)
Writes summary_<date>.csv / .json / .md and latest.json

Two different questions, two different numbers:
  premium                  target tokens / baseline tokens WITHIN one tokenizer:
                           "in this model, how much more does Thai cost than English?"
  tokens per 1,000 chars   absolute cost of the same text ACROSS tokenizers:
                           "which model needs the fewest tokens for this Thai text?"
Premiums of two models must not be compared with each other: their baselines differ.

A model counted on a sample only (coverage = "sample") gets no numbers of its own. Its
row says which fully measured model gives exactly the same counts on the sampled sentences.

This measures token cost only, not answer quality.
"""
from __future__ import annotations

import csv
import json
import os
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import Stop, new_file, sha256_file, utc_now

N_BOOT = 10_000
SEED = 20261110
# <source> is a plain source (open, openai, ...) or <source>-<label> for an add-on set
COUNTS_NAME = re.compile(r"counts_(\d{4}-\d{2}-\d{2})_([a-z]+(?:-[a-z0-9]+)?)\.csv$")
NUMBER_COLUMNS = (
    "baseline_tokens", "target_tokens", "premium", "ci95_low", "ci95_high",
    "baseline_chars", "target_chars", "baseline_tokens_per_1k_chars", "target_tokens_per_1k_chars",
    "baseline_chars_per_token", "target_chars_per_token",
)


# --- the math (pure functions, covered by tests) ---------------------------------------------

def premium(target_tokens: np.ndarray, baseline_tokens: np.ndarray) -> float:
    """sum(target tokens) / sum(baseline tokens) over all sentence pairs."""
    return float(target_tokens.sum() / baseline_tokens.sum())


def tokens_per_1k_chars(tokens: int, chars: int) -> float:
    return 1000.0 * tokens / chars


def resample_weights(n_sentences: int, n_boot: int = N_BOOT, seed: int = SEED) -> np.ndarray:
    """weights[b, i] = how many times sentence pair i is drawn in bootstrap resample b."""
    rng = np.random.default_rng(seed)
    return rng.multinomial(n_sentences, np.full(n_sentences, 1.0 / n_sentences), size=n_boot)


def bootstrap_ci(
    target_tokens: np.ndarray, baseline_tokens: np.ndarray, weights: np.ndarray
) -> tuple[float, float]:
    """95% percentile interval of the premium. Sentence PAIRS are resampled, so the target
    and baseline of one sentence always stay together."""
    resampled = (weights @ target_tokens) / (weights @ baseline_tokens)
    low, high = np.percentile(resampled, [2.5, 97.5])
    return float(low), float(high)


# --- the stage --------------------------------------------------------------------------

def find_counts(directory: Path, date: str | None) -> list[Path]:
    """The counts files of one run date (default: the newest), in a fixed source order."""
    found = defaultdict(dict)
    for path in directory.glob("counts_*.csv"):
        match = COUNTS_NAME.search(path.name)
        if match:
            found[match[1]][match[2]] = path
    if not found:
        raise Stop(f"no counts_<date>_<source>.csv file in {directory}")
    date = date or max(found)
    if date not in found:
        raise Stop(f"no counts file for {date} in {directory}")
    order = ("open", "openai", "gemini", "anthropic")
    def rank(source: str) -> tuple[int, str]:
        base = source.split("-")[0]
        return (order.index(base) if base in order else len(order), source)

    sources = sorted(found[date], key=rank)
    return [found[date][s] for s in sources]


def load_counts(paths: list[Path]):
    """-> (date, [tokenizer keys in file order], {key: {lang: {sent_id: (chars, tokens)}}})
    A key is (source, family, model_id, tokenizer, library)."""
    order: list[tuple] = []
    data: dict = defaultdict(lambda: defaultdict(dict))
    dates = set()
    for path in paths:
        match = COUNTS_NAME.search(path.name)
        source = match[2] if match else "open"
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                key = (source, row["family"], row["model_id"], row["tokenizer"], row["library"])
                if key not in data:
                    order.append(key)
                sent_id = int(row["sent_id"])
                if sent_id in data[key][row["lang"]]:
                    raise Stop(f"duplicate row: {row['model_id']} {row['lang']} sent_id={sent_id}")
                data[key][row["lang"]][sent_id] = (int(row["n_chars"]), int(row["n_tokens"]))
                dates.add(row["run_date_utc"])
    if len(dates) != 1:
        raise Stop(f"the counts files must share one run date, found {sorted(dates)}")
    if len({key[2] for key in order}) != len(order):
        raise Stop("a model id appears in more than one source or with two tokenizers")
    return dates.pop(), order, data


def summarize(order, data, baseline: str, targets: list[str]) -> list[dict]:
    """One row per tokenizer x target language, in file order."""
    all_ids = sorted(set().union(*(data[key][baseline] for key in order)))
    weights = resample_weights(len(all_ids))  # the same resamples for every tokenizer
    rows: list[dict] = []
    full: list[tuple[str, str, dict, dict]] = []  # (model_id, target, baseline counts, target counts)

    for key in order:
        source, family, model_id, tokenizer, library = key
        langs = data[key]
        for target in targets:
            ids = sorted(langs[baseline])
            if not ids or sorted(langs[target]) != ids:
                raise Stop(f"{model_id}: need one {baseline} and one {target} row per sentence")
            base_tok = np.array([langs[baseline][s][1] for s in ids], dtype=np.int64)
            targ_tok = np.array([langs[target][s][1] for s in ids], dtype=np.int64)
            if base_tok.min() <= 0 or targ_tok.min() <= 0:
                raise Stop(f"{model_id}: a sentence has zero tokens")
            row = {
                "source": source, "family": family, "model_id": model_id, "tokenizer": tokenizer,
                "library": library, "baseline_lang": baseline, "target_lang": target,
                "coverage": "full" if ids == all_ids else "sample", "n_sentences": len(ids),
                **dict.fromkeys(NUMBER_COLUMNS), "same_counts_as": "",
            }
            mine = (
                dict(zip(ids, base_tok.tolist(), strict=True)),
                dict(zip(ids, targ_tok.tolist(), strict=True)),
            )
            if row["coverage"] == "full":
                base_chars = sum(langs[baseline][s][0] for s in ids)
                targ_chars = sum(langs[target][s][0] for s in ids)
                low, high = bootstrap_ci(targ_tok, base_tok, weights)
                row.update({
                    "baseline_tokens": int(base_tok.sum()),
                    "target_tokens": int(targ_tok.sum()),
                    "premium": premium(targ_tok, base_tok),
                    "ci95_low": low,
                    "ci95_high": high,
                    "baseline_chars": base_chars,
                    "target_chars": targ_chars,
                    "baseline_tokens_per_1k_chars": tokens_per_1k_chars(int(base_tok.sum()), base_chars),
                    "target_tokens_per_1k_chars": tokens_per_1k_chars(int(targ_tok.sum()), targ_chars),
                    "baseline_chars_per_token": base_chars / float(base_tok.sum()),
                    "target_chars_per_token": targ_chars / float(targ_tok.sum()),
                })
                row["same_counts_as"] = next(
                    (m for m, t, b, tg in full if t == target and (b, tg) == mine), ""
                )
                full.append((model_id, target, *mine))
            rows.append((row, mine))

    # A sampled model points at the first fully measured model that agrees on every sampled sentence.
    for row, (base, targ) in rows:
        if row["coverage"] == "sample":
            row["same_counts_as"] = next(
                (
                    m for m, t, b, tg in full
                    if t == row["target_lang"]
                    and all(b[s] == base[s] and tg[s] == targ[s] for s in base)
                ),
                "",
            )
    return [row for row, _ in rows]


def cell(value) -> str:
    if value is None:
        return ""
    return f"{value:.6f}" if isinstance(value, float) else str(value)


def markdown_table(rows: list[dict]) -> str:
    lines = [
        "| source | family | model / encoding | language | premium vs baseline | 95% CI | tokens "
        "| tokens per 1,000 chars | baseline tokens | baseline tokens per 1,000 chars "
        "| sentences | same counts as |",
        "|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        same = f"`{r['same_counts_as']}`" if r["same_counts_as"] else ""
        start = f"| {r['source']} | {r['family']} | `{r['model_id']}` | {r['target_lang']} "
        if r["coverage"] == "sample":
            lines.append(f"{start}| | | | | | | {r['n_sentences']} (sample) | {same or 'NO MATCH'} |")
            continue
        lines.append(
            f"{start}| {r['premium']:.3f} | {r['ci95_low']:.3f}–{r['ci95_high']:.3f} "
            f"| {r['target_tokens']} | {r['target_tokens_per_1k_chars']:.1f} | {r['baseline_tokens']} "
            f"| {r['baseline_tokens_per_1k_chars']:.1f} | {r['n_sentences']} | {same} |"
        )
    return "\n".join(lines) + "\n"


def run(
    counts_csvs: list[Path], baseline: str, targets: list[str], out_dir: Path, label: str | None = None
) -> Path:
    date, order, data = load_counts(counts_csvs)
    datasets = set()
    for path in counts_csvs:  # every source must have counted the very same sentences
        meta_path = path.with_suffix(".meta.json")
        if meta_path.exists():
            datasets.add(json.loads(meta_path.read_text(encoding="utf-8"))["dataset"]["sha256"])
    if len(datasets) > 1:
        raise Stop(f"the counts files were made from different sentence files: {sorted(datasets)}")
    rows = summarize(order, data, baseline, targets)

    stem = f"summary_{date}" + (f"_{label}" if label else "")
    out_csv = new_file(out_dir / f"{stem}.csv")
    out_json = new_file(out_dir / f"{stem}.json")
    out_md = new_file(out_dir / f"{stem}.md")

    def relative(path: Path) -> str:
        return Path(os.path.relpath(path, out_dir)).as_posix()

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(rows[0].keys())
        for r in rows:
            writer.writerow([cell(v) for v in r.values()])

    inputs = [{"file": relative(p), "sha256": sha256_file(p)} for p in counts_csvs]
    details = {
        "computed_utc": utc_now(),
        "inputs": inputs,
        "premium": "sum(target tokens) / sum(baseline tokens) over all sentence pairs, within one tokenizer",
        "tokens_per_1k_chars": "1000 * sum(tokens) / sum(Unicode code points); comparable across tokenizers",
        "ci": {
            "level": 0.95, "method": "percentile bootstrap over sentence pairs (paired)",
            "resamples": N_BOOT, "seed": SEED, "rng": "numpy.random.default_rng (PCG64)",
            "numpy": np.__version__,
        },
        "coverage": "full = every sentence counted; sample = counted on a fixed random sample only",
        "same_counts_as": "full rows: first earlier tokenizer with identical per-sentence counts in both "
                          "languages; sample rows: first fully measured tokenizer that agrees on every "
                          "sampled sentence (empty = no match, the model needs a full run)",
        "scope_note": "This measures token cost, not answer quality.",
        "rows": rows,
    }
    out_json.write_text(json.dumps(details, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(markdown_table(rows), encoding="utf-8", newline="\n")

    # latest.json is the one pointer that is rewritten: the site and README read only this.
    previous = out_dir / "latest.json"
    kept = {}
    if previous.exists():  # entries written by other commands (cost, billing-check, ...) survive
        old = json.loads(previous.read_text(encoding="utf-8"))
        owned = {"run_date_utc", "summary_csv", "summary_json", "summary_md", "counts", "counts_meta",
                 "verification", "updated_utc"}
        kept = {k: v for k, v in old.items() if k not in owned}
    latest: dict = {
        **kept,
        "run_date_utc": date,
        "summary_csv": out_csv.name,
        "summary_json": out_json.name,
        "summary_md": out_md.name,
        "counts": {},
        "counts_meta": {},
        "verification": {},
        "updated_utc": utc_now(),
    }
    for path in counts_csvs:
        match = COUNTS_NAME.search(path.name)
        source = match[2] if match else "open"
        latest["counts"][source] = relative(path)
        for label_, candidate in (
            ("counts_meta", path.with_suffix(".meta.json")),
            ("verification", path.with_name(f"verification_{date}_{source}.json")),
        ):
            if candidate.exists():
                latest[label_][source] = relative(candidate)
    (out_dir / "latest.json").write_text(json.dumps(latest, indent=2) + "\n", encoding="utf-8")

    print(f"{len(rows)} rows from {len(counts_csvs)} sources, {N_BOOT} bootstrap resamples -> {out_csv}")
    return out_csv
