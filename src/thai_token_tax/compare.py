"""`ttt compare`: the same tokenizers on FLORES-200 and on FLORES+.

Reads  the FLORES-200 counts named in results/latest.json, and the counts in results/floresplus/
Writes results/comparison_flores200_vs_floresplus_<date>.csv / .json / .md

For every tokenizer measured in full on both sets it reports premium and tokens per 1,000
Thai characters with 95% bootstrap CIs, whether the FLORES+ value falls inside the FLORES-200 CI,
and whether the per-sentence counts are identical (the strongest possible agreement).
FLORES-200 stays the core set; this file is a separate, labelled comparison.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from . import Stop, new_file, sha256_file, utc_now
from .analyze import find_counts, load_counts, resample_weights


def ratio_ci(top: np.ndarray, bottom: np.ndarray, weights: np.ndarray, scale: float = 1.0):
    """(value, low, high) of scale * sum(top) / sum(bottom), percentile bootstrap over sentences."""
    resampled = scale * (weights @ top) / (weights @ bottom)
    low, high = np.percentile(resampled, [2.5, 97.5])
    return float(scale * top.sum() / bottom.sum()), float(low), float(high)


def measures(langs: dict, baseline: str, target: str, weights: np.ndarray) -> dict:
    ids = sorted(langs[baseline])
    base_tok = np.array([langs[baseline][s][1] for s in ids], dtype=np.int64)
    targ_tok = np.array([langs[target][s][1] for s in ids], dtype=np.int64)
    targ_chars = np.array([langs[target][s][0] for s in ids], dtype=np.int64)
    premium = ratio_ci(targ_tok, base_tok, weights)
    per_1k = ratio_ci(targ_tok, targ_chars, weights, 1000.0)
    return {
        "ids": ids, "base_tok": base_tok.tolist(), "targ_tok": targ_tok.tolist(),
        "premium": premium, "per_1k": per_1k, "target_tokens": int(targ_tok.sum()),
    }


def compare(core, plus, baseline: str, target: str) -> list[dict]:
    """core and plus are load_counts() results. One row per tokenizer measured in full on both."""
    _, core_order, core_data = core
    _, plus_order, plus_data = plus
    by_model = {key[2]: key for key in core_order}
    rows = []
    for key in plus_order:
        model_id = key[2]
        if model_id not in by_model:
            continue
        a, b = core_data[by_model[model_id]], plus_data[key]
        if len(a[baseline]) != len(b[baseline]) or len(a[target]) != len(b[target]):
            continue  # a sample on one side: not comparable as a full run
        weights = resample_weights(len(a[baseline]))
        old, new = measures(a, baseline, target, weights), measures(b, baseline, target, weights)
        same = all(old[k] == new[k] for k in ("ids", "base_tok", "targ_tok"))
        row = {"source": key[0], "family": key[1], "model_id": model_id, "identical_counts": same}
        for name, label in (("premium", "premium"), ("per_1k", "tokens_per_1k_thai_chars")):
            for tag, m in (("flores200", old), ("floresplus", new)):
                row[f"{label}_{tag}"], row[f"{label}_{tag}_ci_low"], row[f"{label}_{tag}_ci_high"] = m[name]
            row[f"{label}_floresplus_inside_flores200_ci"] = (
                old[name][1] <= new[name][0] <= old[name][2]
            )
        row["thai_tokens_flores200"] = old["target_tokens"]
        row["thai_tokens_floresplus"] = new["target_tokens"]
        rows.append(row)
    return rows


def interval(r: dict, prefix: str, digits: int) -> str:
    low, high = r[f"{prefix}_ci_low"], r[f"{prefix}_ci_high"]
    return f"{r[prefix]:.{digits}f} ({low:.{digits}f}–{high:.{digits}f})"


def yes(flag: bool) -> str:
    return "yes" if flag else "NO"


def markdown(rows: list[dict]) -> str:
    lines = [
        "| tokenizer | identical per-sentence counts | premium FLORES-200 (95% CI) | premium FLORES+ "
        "| inside CI | Thai tokens / 1,000 chars FLORES-200 (95% CI) | FLORES+ | inside CI |",
        "|---|---|---|---:|---|---|---:|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['model_id']}` | {yes(r['identical_counts'])} "
            f"| {interval(r, 'premium_flores200', 3)} | {r['premium_floresplus']:.3f} "
            f"| {yes(r['premium_floresplus_inside_flores200_ci'])} "
            f"| {interval(r, 'tokens_per_1k_thai_chars_flores200', 1)} "
            f"| {r['tokens_per_1k_thai_chars_floresplus']:.1f} "
            f"| {yes(r['tokens_per_1k_thai_chars_floresplus_inside_flores200_ci'])} |"
        )
    return "\n".join(lines) + "\n"


def run(results: Path, baseline: str, target: str) -> Path:
    latest = json.loads((results / "latest.json").read_text(encoding="utf-8"))
    core_files = [results / name for name in latest["counts"].values()]
    plus_files = find_counts(results / "floresplus", None)
    core, plus = load_counts(core_files), load_counts(plus_files)
    if core[0] != plus[0]:
        raise Stop(f"the two sets were counted on different dates: {core[0]} and {plus[0]}")
    rows = compare(core, plus, baseline, target)
    if not rows:
        raise Stop("no tokenizer was measured in full on both sets")

    stem = f"comparison_flores200_vs_floresplus_{core[0]}"
    out_csv, out_json, out_md = (new_file(results / f"{stem}{ext}") for ext in (".csv", ".json", ".md"))
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(rows[0].keys())
        for r in rows:
            writer.writerow([f"{v:.6f}" if isinstance(v, float) else v for v in r.values()])
    out_json.write_text(json.dumps({
        "computed_utc": utc_now(),
        "inputs": {
            "flores200": [{"file": p.name, "sha256": sha256_file(p)} for p in core_files],
            "floresplus": [{"file": f"floresplus/{p.name}", "sha256": sha256_file(p)} for p in plus_files],
        },
        "ci": "95% percentile bootstrap over sentence pairs, 10,000 resamples, same seed as `ttt analyze`",
        "rows": rows,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(markdown(rows), encoding="utf-8", newline="\n")
    print(f"{len(rows)} tokenizers compared; identical counts: {sum(r['identical_counts'] for r in rows)} "
          f"-> {out_csv}")
    return out_csv
