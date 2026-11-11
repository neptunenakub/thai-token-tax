"""`ttt billing-check`: does Claude bill what count_tokens says?

Anthropic documents count_tokens as an estimate. This check sends a small fixed sample of
sentences twice, as the identical request: once to count_tokens (free) and once to the real
Messages API with max_tokens=1 (billed), and compares count_tokens with usage.input_tokens.

THIS COMMAND SPENDS MONEY. Safeguards:
  - the expected cost is computed first from the already measured token counts and the saved
    official prices, printed, and the run aborts if it exceeds the cap (default 0.10 USD);
  - every billable request is sent exactly once: answers are checkpointed, the SDK's automatic
    retries are off, and only a rate-limit refusal (which bills nothing) is tried again;
  - `--dry-run` prints the estimate and sends nothing billable.

Writes results/billing_check_<date>.json / .md and adds it to latest.json.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import time
from datetime import UTC, datetime
from pathlib import Path

from . import Stop, new_file, sha256_file, utc_now
from .data import load_sentences

CAP_USD = 0.10
SEED = 20261110
MAX_TOKENS = 1
SECONDS_BETWEEN_REQUESTS = 1.5  # two requests per text -> about 80 requests a minute
# (model, number of sentence pairs, model whose full-run counts give the expected tokens)
PLAN = [
    ("claude-haiku-5-5", 20, "claude-opus-5-5"),  # sampled on day 2: same counts as claude-opus-5-5
    ("claude-haiku-4-5-20251001", 20, "claude-haiku-4-5-20251001"),
    ("claude-opus-5-5", 5, "claude-opus-5-5"),  # the first 5 of the same pairs
]


# --- pure logic (covered by tests) --------------------------------------------------------

def sample_pairs(sent_ids: list[int], n: int) -> list[int]:
    """The first n ids of one fixed shuffle, so a smaller sample is a subset of a larger one."""
    shuffled = list(sent_ids)
    random.Random(SEED).shuffle(shuffled)
    return shuffled[:n]


def billed_input(usage: dict) -> int:
    """Everything billed on the input side, cache fields included (they should be zero here)."""
    return (
        usage.get("input_tokens", 0)
        + (usage.get("cache_creation_input_tokens") or 0)
        + (usage.get("cache_read_input_tokens") or 0)
    )


def cost_usd(input_tokens: int, output_tokens: int, price: dict) -> float:
    return (
        input_tokens * price["input_usd_per_mtok"] + output_tokens * price["output_usd_per_mtok"]
    ) / 1_000_000.0


def classify(differences: list[int]) -> str:
    """What the per-text differences (billed input - count_tokens) look like."""
    distinct = set(differences)
    if distinct == {0}:
        return "equal for every text"
    if len(distinct) == 1:
        return f"differ by a constant ({differences[0]:+d} tokens on every text)"
    return f"differ irregularly (differences from {min(distinct):+d} to {max(distinct):+d})"


def estimate(plan_rows: list[dict], prices: dict) -> float:
    """Expected cost of the billable requests, from token counts measured earlier."""
    return sum(
        cost_usd(r["expected_input_tokens"], MAX_TOKENS, prices["models"][r["model_id"]]) for r in plan_rows
    )


def summarize(rows: list[dict], prices: dict) -> dict:
    """Per-model verdicts and the actual cost, from the recorded answers."""
    models = {}
    for model_id in dict.fromkeys(r["model_id"] for r in rows):
        mine = [r for r in rows if r["model_id"] == model_id and r.get("usage")]
        differences = [billed_input(r["usage"]) - r["count_tokens"] for r in mine]
        overheads = sorted({billed_input(r["usage"]) - r["content_tokens_published"] for r in mine})
        models[model_id] = {
            "texts_compared": len(mine),
            "texts_failed": sum(1 for r in rows if r["model_id"] == model_id and not r.get("usage")),
            "billed_input_vs_count_tokens": classify(differences) if mine else "no answer",
            "count_tokens_minus_published_content": sorted(
                {r["count_tokens"] - r["content_tokens_published"] for r in mine}
            ),
            "billed_input_minus_published_content": overheads,
            "overhead_subtracted_in_results": mine[0]["overhead_published"] if mine else None,
            "any_cache_tokens": any(billed_input(r["usage"]) != r["usage"]["input_tokens"] for r in mine),
            "output_tokens": sorted({r["usage"]["output_tokens"] for r in mine}),
            "billed_input_tokens": sum(billed_input(r["usage"]) for r in mine),
            "billed_output_tokens": sum(r["usage"]["output_tokens"] for r in mine),
            "actual_cost_usd": sum(
                cost_usd(billed_input(r["usage"]), r["usage"]["output_tokens"], prices["models"][model_id])
                for r in mine
            ),
        }
    return models


def same_billing(rows: list[dict], model_a: str, model_b: str) -> dict:
    """Do two models bill the same input tokens for the texts they both got?"""
    def billed(model_id: str) -> dict:
        mine = [r for r in rows if r["model_id"] == model_id and r.get("usage")]
        return {(r["lang"], r["sent_id"]): billed_input(r["usage"]) for r in mine}

    a, b = billed(model_a), billed(model_b)
    shared = sorted(set(a) & set(b))
    return {"texts_in_common": len(shared), "texts_billed_differently": sum(a[k] != b[k] for k in shared)}


# --- the run ------------------------------------------------------------------------------

def build_plan(root: Path, results: Path) -> list[dict]:
    """One row per (model, language, sentence) with the tokens we expect from earlier results."""
    latest = json.loads((results / "latest.json").read_text(encoding="utf-8"))
    csv_path = results / latest["counts"]["anthropic"]
    meta = json.loads(csv_path.with_suffix(".meta.json").read_text(encoding="utf-8"))
    overhead = {m["model_id"]: m["overhead_tokens_subtracted"] for m in meta["measured"]}
    counts: dict = {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            counts[(r["model_id"], r["lang"], int(r["sent_id"]))] = int(r["n_tokens"])
    sent_ids, texts = load_sentences(root)
    position = {s: i for i, s in enumerate(sent_ids)}
    rows = []
    for model_id, pairs, counts_from in PLAN:
        for sent_id in sample_pairs(sent_ids, pairs):
            for lang, lines in texts.items():
                content = counts[(counts_from, lang, sent_id)]
                rows.append({
                    "model_id": model_id, "lang": lang, "sent_id": sent_id,
                    "text": lines[position[sent_id]],
                    "content_tokens_published": content,
                    "overhead_published": overhead[model_id],
                    "expected_input_tokens": content + overhead[model_id],
                })
    return rows


def run(
    root: Path, results: Path, dry_run: bool = False, cap_usd: float = CAP_USD, client=None
) -> Path | None:
    latest_path = results / "latest.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    prices_path = results / latest["prices"]
    prices = json.loads(prices_path.read_text(encoding="utf-8"))
    plan = build_plan(root, results)

    expected = estimate(plan, prices)
    print(f"{len(plan)} billable requests planned ({len(plan)} count_tokens requests, free).")
    for model_id, _, _ in PLAN:
        mine = [r for r in plan if r["model_id"] == model_id]
        print(f"  {model_id}: {len(mine)} texts, expected {sum(r['expected_input_tokens'] for r in mine):,} "
              f"input tokens + {len(mine) * MAX_TOKENS} output tokens = ${estimate(mine, prices):.6f}")
    print(f"expected cost ${expected:.6f}, cap ${cap_usd:.2f}")
    if expected > cap_usd:
        raise Stop(f"the expected cost ${expected:.6f} is above the cap ${cap_usd:.2f}; nothing was sent")
    if dry_run:
        print("dry run: nothing billable was sent")
        return None

    date = datetime.now(UTC).strftime("%Y-%m-%d")
    out_json = new_file(results / f"billing_check_{date}.json")
    out_md = new_file(results / f"billing_check_{date}.md")
    if client is None:
        import anthropic

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise Stop("ANTHROPIC_API_KEY is not set")
        client = anthropic.Anthropic(max_retries=0)  # never resend a billable request automatically

    checkpoint = root / ".cache" / "billing" / "answers.jsonl"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            done[entry["key"]] = entry

    sent_now = 0
    for row in plan:
        text = row.pop("text")
        key = hashlib.sha256(f"{row['model_id']}\x1e{text}".encode()).hexdigest()
        if key not in done:
            messages = [{"role": "user", "content": text}]
            entry = {"key": key, **ask(client, row["model_id"], messages)}
            with checkpoint.open("a", encoding="utf-8") as f:  # saved at once: never billed twice
                f.write(json.dumps(entry) + "\n")
            done[key] = entry
            sent_now += 1
        row.update({k: v for k, v in done[key].items() if k != "key"})

    models = summarize(plan, prices)
    actual = sum(m["actual_cost_usd"] for m in models.values())
    report = {
        "run_utc": utc_now(),
        "what": "the identical request sent to count_tokens (free) and to the Messages API with "
                f"max_tokens={MAX_TOKENS} (billed): no system prompt, no tools, no cache_control, "
                "default thinking settings",
        "sample": {"seed": SEED, "dataset": "flores200 devtest",
                   "pairs": {model: pairs for model, pairs, _ in PLAN}},
        "prices_file": {"file": prices_path.name, "sha256": sha256_file(prices_path)},
        "cost": {"cap_usd": cap_usd, "expected_usd": expected, "actual_usd": actual,
                 "billable_requests_sent_this_run": sent_now,
                 "billable_requests_answered_in_total": sum(1 for r in plan if r.get("usage")),
                 "actual_is": "usage of each answer x the official list price in the prices file"},
        "models": models,
        "claude-opus-5-5_vs_claude-haiku-5-5": same_billing(plan, "claude-opus-5-5", "claude-haiku-5-5"),
        "rows": plan,
    }
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(markdown(report), encoding="utf-8", newline="\n")
    latest.update({"billing_check": out_json.name, "updated_utc": utc_now()})
    latest_path.write_text(json.dumps(latest, indent=2) + "\n", encoding="utf-8")
    print(markdown(report))
    return out_json


def ask(client, model_id: str, messages: list[dict]) -> dict:
    """count_tokens, then the real request. Only a rate-limit refusal is retried: it bills nothing."""
    import anthropic

    def paced(call):
        for _ in range(6):
            time.sleep(SECONDS_BETWEEN_REQUESTS)
            try:
                return call()
            except anthropic.RateLimitError as e:
                time.sleep(float(e.response.headers.get("retry-after", "5")))
        raise Stop("still rate limited after 6 tries; run again later (answers so far are saved)")

    counted = paced(lambda: client.messages.count_tokens(model=model_id, messages=messages)).input_tokens
    try:
        request = {"model": model_id, "max_tokens": MAX_TOKENS, "messages": messages}
        answer = paced(lambda: client.messages.create(**request))
    except anthropic.APIError as e:  # not retried: we cannot know whether it was billed
        return {"count_tokens": counted, "usage": None, "error": f"{type(e).__name__}: {str(e)[:200]}"}
    return {"count_tokens": counted, "usage": answer.usage.to_dict(), "stop_reason": answer.stop_reason}


def markdown(report: dict) -> str:
    cost = report["cost"]
    lines = [
        f"Billing check, {report['run_utc']}. {report['what']}.",
        "",
        f"Cost: expected ${cost['expected_usd']:.6f}, actual ${cost['actual_usd']:.6f} "
        f"(cap ${cost['cap_usd']:.2f}); {cost['billable_requests_answered_in_total']} billable requests.",
        "",
        "| model | texts | billed input vs count_tokens | billed input - published content tokens "
        "| overhead subtracted in results | cache tokens | output tokens | cost USD |",
        "|---|---:|---|---|---:|---|---|---:|",
    ]
    for model_id, m in report["models"].items():
        lines.append(
            f"| `{model_id}` | {m['texts_compared']} | {m['billed_input_vs_count_tokens']} "
            f"| {m['billed_input_minus_published_content']} | {m['overhead_subtracted_in_results']} "
            f"| {'YES' if m['any_cache_tokens'] else 'none'} | {m['output_tokens']} "
            f"| {m['actual_cost_usd']:.6f} |"
        )
    same = report["claude-opus-5-5_vs_claude-haiku-5-5"]
    lines += [
        "",
        f"claude-opus-5-5 vs claude-haiku-5-5 on the same texts: {same['texts_billed_differently']} of "
        f"{same['texts_in_common']} billed a different number of input tokens.",
    ]
    return "\n".join(lines) + "\n"
