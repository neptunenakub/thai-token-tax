"""Official prices + exchange rate -> baht.

`ttt prices`  fetch the official pricing pages and the Bank of Thailand rate
              -> results/prices_<date>.json           (needs network, no keys)
`ttt cost`    measured tokens x official price x exchange rate, for each scenario
              -> results/costs_<date>.csv / .json / .md (offline)

    baht = tokens x (USD per 1,000,000 tokens) / 1,000,000 x (baht per USD)
    tokens = characters x measured tokens per 1,000 characters / 1,000

Prices are read from the pages on the day of the run and saved with URL, time and a
hash of the page. A model that is not found on its page is recorded as missing, never
filled in. Read LIMITS below before quoting any baht number.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import tomllib
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path

from . import Stop, new_file, sha256_file, utc_now

LIMITS = [
    "This is token cost only. It says nothing about answer quality.",
    "Token rates were measured on FLORES-200 (news and encyclopedia style text). Chat messages or "
    "other kinds of text may tokenize differently.",
    "Output tokens are assumed to have the same tokens-per-character as input text of that language.",
    "Reasoning/thinking tokens, prompt caching, batch discounts, free tiers and long-context price "
    "tiers are not included. Standard list prices only.",
    "Claude token rates come from count_tokens, which Anthropic documents as an estimate.",
    "Open models have no per-token price of their own: only their token counts are reported.",
    "The English column is the same content in English: character counts are scaled by the measured "
    "English/Thai character ratio of FLORES-200.",
    "Scenario sizes (characters, turns, volumes) are assumptions written in registry/scenarios.toml, "
    "not measurements.",
]
USER_AGENT = "Mozilla/5.0 (thai-token-tax price check)"


# --- reading prices off a page (pure functions, covered by tests) --------------------------

def money(cell: str) -> float | None:
    """'$4 / MTok' -> 4.0, '$0.125' -> 0.125, '-' -> None."""
    match = re.search(r"\$\s*(\d+(?:\.\d+)?)", cell)
    return float(match[1]) if match else None


def table_row(page: str, label: str, needs_column: list[str], start: str = "", end: str = "") -> dict | None:
    """Find the Markdown table row whose first cell is exactly `label`, in a table that has
    one of the `needs_column` headers, between the optional `start` and `end` markers.
    -> {header: cell} or None."""
    if start:
        if start not in page:
            return None
        page = page.split(start, 1)[1]
    if end and end in page:
        page = page.split(end, 1)[0]
    header: list[str] = []
    lines = page.splitlines()
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            header = []
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            header = cells
        elif header and cells[0] == label and any(c in header for c in needs_column):
            return dict(zip(header, cells, strict=False))
    return None


def gemini_cell(page: str, section_id: str, feature: str) -> str | None:
    """The paid-tier cell of a feature row ("Input price", ...) in the first (Standard) table of
    a model section on the Gemini pricing page."""
    marker = f'id="{section_id}"'
    if marker not in page:
        return None
    section = page.split(marker, 1)[1].split("\n## ", 1)[0]
    lines = section.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(f"* {feature}"):
            cell, bullets = [], 0
            for following in lines[i + 1:]:
                text = following.strip()
                if text == "---" or text.startswith("{%"):
                    break
                if text.startswith("* "):
                    bullets += 1
                    text = text[2:]
                if bullets >= 2 and text:  # bullet 1 is the free tier, bullet 2 the paid tier
                    cell.append(text)
            return " ".join(cell) or None
    return None


def pick_price(cell: str, today: date) -> float | None:
    """The standard price that applies today from a cell such as
    '$0.75 through December 31, 2026. $1.50 starting January 1, 2027.' or
    '$2.00, prompts <= 200k tokens $4.00, prompts > 200k tokens' or '$0.30 (text / image)'."""
    for match in re.finditer(r"\$(\d+(?:\.\d+)?)([^$]*)", cell):
        price, rest = float(match[1]), match[2]
        day = re.search(r"(through|starting) ([A-Z][a-z]+ \d{1,2}, \d{4})", rest)
        if day:
            limit = datetime.strptime(day[2], "%B %d, %Y").date()
            if (day[1] == "through" and today > limit) or (day[1] == "starting" and today < limit):
                continue
        if re.search(r"prompts\s*>", rest):  # the long-context tier
            continue
        return price
    return None


def bot_rate(answer: dict) -> tuple[float, str]:
    """(baht per US dollar, date text) from the Bank of Thailand exchange-rate page data."""
    text = re.sub(r"<[^>]+>|&nbsp;", " ", answer["description"])
    match = re.search(r"Weighted-average Interbank Exchange Rate\s*=\s*(\d+\.\d+)", text)
    if not match:
        raise Stop("the Bank of Thailand page data has no weighted-average interbank rate")
    return float(match[1]), answer["date"].replace("Date", "").strip()


# --- `ttt prices` -------------------------------------------------------------------------

def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def fetch_prices(root: Path, out_dir: Path, fetch=fetch) -> Path:
    config = tomllib.loads((root / "registry" / "pricing.toml").read_text(encoding="utf-8"))
    today = datetime.now(UTC).date()
    out = new_file(out_dir / f"prices_{today}.json")
    cache = root / ".cache" / "pricing" / str(today)
    cache.mkdir(parents=True, exist_ok=True)

    sources, models, missing = {}, {}, []
    for provider, spec in config["provider"].items():
        raw = fetch(spec["url"])
        (cache / f"{provider}.txt").write_bytes(raw)  # kept locally for checking, not in git
        page = raw.decode("utf-8")
        sources[provider] = {
            "url": spec["url"], "fetched_utc": utc_now(),
            "page_sha256": hashlib.sha256(raw).hexdigest(), "page_bytes": len(raw),
        }
        for model_id, label in spec["rows"].items():
            if spec["format"] == "gemini":
                cells = {k: gemini_cell(page, label, f"{k.capitalize()} price") for k in ("input", "output")}
                prices = {k: pick_price(v, today) if v else None for k, v in cells.items()}
            else:
                bounds = (spec.get("start", ""), spec.get("end", ""))
                row = table_row(page, label, spec["input_columns"], *bounds)
                cells = {
                    k: next((row[c] for c in spec[f"{k}_columns"] if row and c in row), None)
                    for k in ("input", "output")
                }
                prices = {k: money(v) if v else None for k, v in cells.items()}
                cells["whole_row"] = row  # also shows cached and long-context prices, which are not used
            if prices["input"] is None or prices["output"] is None:
                missing.append({"model_id": model_id, "provider": provider, "looked_for": label,
                                "reason": "row or price not found on the page"})
                continue
            models[model_id] = {
                "provider": provider,
                "input_usd_per_mtok": prices["input"],
                "output_usd_per_mtok": prices["output"],
                "page_row": label,
                "page_text_input": cells["input"],
                "page_text_output": cells["output"],
                **({"page_row_cells": cells["whole_row"]} if cells.get("whole_row") else {}),
            }

    rate_url = config["exchange_rate"]["url"]
    raw = fetch(rate_url)
    (cache / "bot.json").write_bytes(raw)
    rate, rate_date = bot_rate(json.loads(raw))
    prices_file = {
        "created_utc": utc_now(),
        "unit": "US dollars per 1,000,000 tokens",
        "tier": "standard list price for text: not batch, not cached, shortest-context tier, "
                "the price in force on the fetch date",
        "sources": sources,
        "models": models,
        "missing": missing,
        "exchange_rate": {
            "thb_per_usd": rate,
            "rate_date": rate_date,
            "what": config["exchange_rate"]["what"],
            "page": config["exchange_rate"]["page"],
            "url": rate_url,
            "fetched_utc": utc_now(),
            "data_sha256": hashlib.sha256(raw).hexdigest(),
        },
    }
    out.write_text(json.dumps(prices_file, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(models)} prices, {len(missing)} missing, {rate} THB/USD ({rate_date}) -> {out}")
    return out


# --- the cost model (pure functions, covered by tests) ------------------------------------

def scenario_chars(scenario: dict) -> tuple[int, int]:
    """(input characters, output characters) of ONE unit of a scenario.
    Every request sends the system prompt and the new message; with resend_history it also
    sends all earlier messages and replies of the conversation again."""
    turns = scenario.get("turns", 1)
    sent = received = 0
    for turn in range(1, turns + 1):
        sent += scenario["system_chars"] + scenario["input_chars"]
        if scenario.get("resend_history", False):
            sent += (turn - 1) * (scenario["input_chars"] + scenario["output_chars"])
        received += scenario["output_chars"]
    return sent, received


def tokens(chars: float, tokens_per_1k_chars: float) -> float:
    return chars * tokens_per_1k_chars / 1000.0


def usd(input_tokens: float, output_tokens: float, price: dict) -> float:
    return (
        input_tokens * price["input_usd_per_mtok"] + output_tokens * price["output_usd_per_mtok"]
    ) / 1_000_000.0


def token_rates(summary_rows: list[dict]) -> dict[str, dict]:
    """model id -> its measured tokens per 1,000 characters. A model measured on a sample only
    takes the rates of the fully measured model it matched; with no match it gets none."""
    full = {r["model_id"]: r for r in summary_rows if r["coverage"] == "full"}
    rates = {}
    for r in summary_rows:
        origin = r if r["coverage"] == "full" else full.get(r["same_counts_as"])
        if origin is None:
            continue
        rates[r["model_id"]] = {
            "source": r["source"],
            "family": r["family"],
            "rate_from": origin["model_id"],
            "coverage": r["coverage"],
            "target": float(origin["target_tokens_per_1k_chars"]),
            "baseline": float(origin["baseline_tokens_per_1k_chars"]),
            "baseline_chars_per_target_char": int(origin["baseline_chars"]) / int(origin["target_chars"]),
        }
    return rates


def cost_rows(summary_rows: list[dict], prices: dict, scenarios: list[dict]) -> list[dict]:
    rate = prices["exchange_rate"]["thb_per_usd"]
    rows = []
    for scenario in scenarios:
        sent, received = scenario_chars(scenario)
        sent, received = sent * scenario["units"], received * scenario["units"]
        for model_id, r in token_rates(summary_rows).items():
            scale = r["baseline_chars_per_target_char"]  # the same content is this much longer in English
            th_in, th_out = tokens(sent, r["target"]), tokens(received, r["target"])
            en_in, en_out = tokens(sent * scale, r["baseline"]), tokens(received * scale, r["baseline"])
            price = prices["models"].get(model_id)
            row = {
                "scenario": scenario["id"], "source": r["source"], "family": r["family"],
                "model_id": model_id, "token_rate_from": r["rate_from"], "coverage": r["coverage"],
                "input_usd_per_mtok": price["input_usd_per_mtok"] if price else None,
                "output_usd_per_mtok": price["output_usd_per_mtok"] if price else None,
                "thai_input_tokens": th_in, "thai_output_tokens": th_out,
                "english_input_tokens": en_in, "english_output_tokens": en_out,
                "thai_usd": None, "thai_thb": None, "english_usd": None, "english_thb": None,
                "thai_over_english_cost": None,
            }
            if price:
                th, en = usd(th_in, th_out, price), usd(en_in, en_out, price)
                row.update({"thai_usd": th, "thai_thb": th * rate, "english_usd": en,
                            "english_thb": en * rate, "thai_over_english_cost": th / en})
            rows.append(row)
    return rows


# --- `ttt cost` ---------------------------------------------------------------------------

def cell(value) -> str:
    if value is None:
        return ""
    return f"{value:.6f}" if isinstance(value, float) else str(value)


def markdown(rows: list[dict], scenarios: list[dict], prices: dict) -> str:
    rate = prices["exchange_rate"]
    lines = [
        f"Exchange rate: {rate['thb_per_usd']} baht per US dollar ({rate['what']}, {rate['rate_date']}).",
        "Prices: standard list prices fetched "
        + ", ".join(f"{p} {s['fetched_utc']}" for p, s in prices["sources"].items()) + ".",
        "",
        "Read before quoting:",
        *[f"- {limit}" for limit in LIMITS],
    ]
    for scenario in scenarios:
        sent, received = scenario_chars(scenario)
        lines += [
            "", f"## {scenario['name']}", "",
            f"Assumptions: {scenario['units']:,} {scenario['unit']}; {scenario.get('turns', 1)} turn(s); "
            f"system prompt {scenario['system_chars']:,} chars; each message {scenario['input_chars']:,} "
            f"chars in, {scenario['output_chars']:,} chars out; history resent: "
            f"{'yes' if scenario.get('resend_history') else 'no'}. Per {scenario['unit_singular']}: "
            f"{sent:,} Thai chars sent, {received:,} received.", "",
            "| model | token rate from | $ in / out per 1M | Thai tokens in | Thai tokens out "
            "| Thai, baht | same content in English, baht | Thai ÷ English |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
        priced = [r for r in rows if r["scenario"] == scenario["id"] and r["thai_thb"] is not None]
        for r in sorted(priced, key=lambda r: r["thai_thb"]):
            origin = f"`{r['token_rate_from']}` (sample matched)"
            if r["coverage"] == "full":
                origin = "own full run"
            lines.append(
                f"| `{r['model_id']}` | {origin} "
                f"| {r['input_usd_per_mtok']:g} / {r['output_usd_per_mtok']:g} "
                f"| {r['thai_input_tokens']:,.0f} | {r['thai_output_tokens']:,.0f} | {r['thai_thb']:,.2f} "
                f"| {r['english_thb']:,.2f} | {r['thai_over_english_cost']:.3f} |"
            )
    return "\n".join(lines) + "\n"


def run(root: Path, results: Path, label: str | None = None) -> Path:
    latest_path = results / "latest.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    summary_path = results / latest["summary_csv"]
    price_files = sorted(results.glob("prices_*.json"))
    if not price_files:
        raise Stop(f"no prices_<date>.json in {results}. Run `ttt prices` first.")
    prices_path = price_files[-1]
    prices = json.loads(prices_path.read_text(encoding="utf-8"))
    scenarios = tomllib.loads((root / "registry" / "scenarios.toml").read_text(encoding="utf-8"))["scenario"]
    with summary_path.open(encoding="utf-8", newline="") as f:
        summary_rows = list(csv.DictReader(f))
    rows = cost_rows(summary_rows, prices, scenarios)

    stem = prices_path.stem.replace("prices_", "costs_") + (f"_{label}" if label else "")
    out_csv = new_file(results / f"{stem}.csv")
    out_json = new_file(results / f"{stem}.json")
    out_md = new_file(results / f"{stem}.md")
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(rows[0].keys())
        writer.writerows([cell(v) for v in r.values()] for r in rows)
    out_json.write_text(json.dumps({
        "computed_utc": utc_now(),
        "formula": "baht = tokens x USD per 1,000,000 tokens / 1,000,000 x baht per USD; "
                   "tokens = characters x measured tokens per 1,000 characters / 1,000",
        "inputs": {
            "summary": {"file": summary_path.name, "sha256": sha256_file(summary_path)},
            "prices": {"file": prices_path.name, "sha256": sha256_file(prices_path)},
        },
        "exchange_rate": prices["exchange_rate"],
        "limits": LIMITS,
        "scenarios": scenarios,
        "priced_models_without_token_rate": sorted(set(prices["models"]) - {r["model_id"] for r in rows}),
        "rows": rows,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(markdown(rows, scenarios, prices), encoding="utf-8", newline="\n")

    latest.update({"prices": prices_path.name, "costs_csv": out_csv.name,
                   "costs_json": out_json.name, "costs_md": out_md.name, "updated_utc": utc_now()})
    latest_path.write_text(json.dumps(latest, indent=2) + "\n", encoding="utf-8")
    print(f"{len(rows)} cost rows ({len(scenarios)} scenarios) -> {out_csv}")
    return out_csv
