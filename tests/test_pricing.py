"""Reading prices off a page and the cost arithmetic. No network."""
import csv
import json
from datetime import date

import pytest

from thai_token_tax import Stop, pricing

MARKDOWN_PAGE = """
### Standard pricing data

| Model | Short context input | Short context output | Long context input |
| --- | --- | --- | --- |
| model-a | $2.00 | $10.00 | $4.00 |
| model-b (<272K context length) | $5.00 | $30.00 | - |

| Model | Input | Output |
| --- | --- | --- |
| model-c | $1.75 | $14.00 |

### Batch pricing data

| Model | Short context input | Short context output | Long context input |
| --- | --- | --- | --- |
| model-a | $1.00 | $5.00 | $2.00 |
"""

GEMINI_PAGE = """
## Model One  {% id="model-one" %}

{% tabs %}
  {% tab title="Standard" %}
  {% table %}
  * Feature
  * Free Tier
  * Paid Tier, per 1M tokens in USD

  ---

  * Input price
  * Free of charge
  * $0.75 through December 31, 2026.
  $1.50 starting January 1, 2027.

  ---

  * Output price (including thinking tokens)
  * Free of charge
  * $3.75 through December 31, 2026.
  $7.50 starting January 1, 2027.

  ---

  * Context caching price
  * Free of charge
  * $0.075

## Model Two  {% id="model-two" %}

  * Input price
  * Not available
  * $2.00, prompts <= 200k tokens
  $4.00, prompts > 200k tokens
"""


def test_money():
    assert pricing.money("$4 / MTok") == 4.0
    assert pricing.money("$0.125") == 0.125
    assert pricing.money("$0.20 / MTok<sup>1</sup>") == 0.20
    assert pricing.money("-") is None


def test_table_row_is_taken_from_the_standard_section_only():
    args = (["Short context input", "Input"], "### Standard pricing data", "### Batch pricing data")
    row = pricing.table_row(MARKDOWN_PAGE, "model-a", *args)
    assert (row["Short context input"], row["Short context output"]) == ("$2.00", "$10.00")  # not batch
    assert pricing.table_row(MARKDOWN_PAGE, "model-c", *args)["Output"] == "$14.00"
    long_name = pricing.table_row(MARKDOWN_PAGE, "model-b (<272K context length)", *args)
    assert long_name["Short context input"] == "$5.00"
    assert pricing.table_row(MARKDOWN_PAGE, "model-b", *args) is None  # the label must match exactly
    assert pricing.table_row(MARKDOWN_PAGE, "model-z", *args) is None  # missing stays missing


def test_gemini_cell_reads_the_paid_tier_of_the_right_model():
    cell = pricing.gemini_cell(GEMINI_PAGE, "model-one", "Input price")
    assert cell == "$0.75 through December 31, 2026. $1.50 starting January 1, 2027."
    assert pricing.gemini_cell(GEMINI_PAGE, "model-one", "Output price").startswith("$3.75")
    assert pricing.gemini_cell(GEMINI_PAGE, "model-two", "Input price").startswith("$2.00, prompts <=")
    assert pricing.gemini_cell(GEMINI_PAGE, "model-three", "Input price") is None


def test_pick_price_uses_the_price_in_force_today():
    dated = "$0.75 through December 31, 2026. $1.50 starting January 1, 2027."
    assert pricing.pick_price(dated, date(2026, 11, 10)) == 0.75
    assert pricing.pick_price(dated, date(2026, 12, 31)) == 0.75
    assert pricing.pick_price(dated, date(2027, 1, 1)) == 1.50
    tiered = "$2.00, prompts <= 200k tokens $4.00, prompts > 200k tokens"
    assert pricing.pick_price(tiered, date(2026, 1, 1)) == 2.0
    assert pricing.pick_price("$0.30 (text / image / video / audio)", date(2026, 1, 1)) == 0.30
    assert pricing.pick_price("Not available", date(2026, 1, 1)) is None


def test_bank_of_thailand_rate():
    answer = {
        "description": "<p>Weighted-average Interbank Exchange Rate&nbsp;=&nbsp;<span>33.527</span> Baht</p>",
        "date": "Date 09 November 2026",
    }
    assert pricing.bot_rate(answer) == (33.527, "09 November 2026")
    with pytest.raises(Stop):
        pricing.bot_rate({"description": "<p>maintenance</p>", "date": ""})


def test_fetch_prices_records_missing_models_instead_of_guessing(tmp_path):
    (tmp_path / "registry").mkdir()
    (tmp_path / "registry" / "pricing.toml").write_text(
        '[provider.shop]\nurl = "https://shop.example/prices"\nformat = "markdown"\n'
        'start = "### Standard pricing data"\nend = "### Batch pricing data"\n'
        'input_columns = ["Short context input", "Input"]\n'
        'output_columns = ["Short context output", "Output"]\n'
        '[provider.shop.rows]\n"a" = "model-a"\n"gone" = "model-z"\n'
        '[provider.g]\nurl = "https://g.example/prices"\nformat = "gemini"\n'
        '[provider.g.rows]\n"one" = "model-one"\n"two" = "model-two"\n'
        '[exchange_rate]\nwhat = "test rate"\npage = "https://bank.example"\nurl = "https://bank.example/data"\n',
        encoding="utf-8",
    )
    pages = {
        "https://shop.example/prices": MARKDOWN_PAGE,
        "https://g.example/prices": GEMINI_PAGE,
        "https://bank.example/data": json.dumps(
            {"description": "Weighted-average Interbank Exchange Rate = 33.527", "date": "Date 9 Nov"}
        ),
    }
    out = pricing.fetch_prices(tmp_path, tmp_path / "results", fetch=lambda url: pages[url].encode())
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["models"]["a"]["input_usd_per_mtok"] == 2.0
    assert saved["models"]["a"]["output_usd_per_mtok"] == 10.0
    assert saved["models"]["one"]["output_usd_per_mtok"] in (3.75, 7.50)  # depends on today's date
    assert [m["model_id"] for m in saved["missing"]] == ["gone", "two"]  # "two" has no output price
    assert saved["exchange_rate"]["thb_per_usd"] == 33.527
    assert saved["sources"]["shop"]["url"] == "https://shop.example/prices"


def test_scenario_chars_with_and_without_history():
    once = {"system_chars": 100, "input_chars": 10, "output_chars": 40, "turns": 3}
    assert pricing.scenario_chars(once) == (3 * 110, 3 * 40)
    # turn 1 sends 110; turn 2 sends 110 + (10+40); turn 3 sends 110 + 2*(10+40)
    assert pricing.scenario_chars({**once, "resend_history": True}) == (330 + 50 + 100, 120)
    assert pricing.scenario_chars({"system_chars": 5, "input_chars": 20, "output_chars": 7}) == (25, 7)


SUMMARY = [
    {"source": "api", "family": "F", "model_id": "full", "coverage": "full", "same_counts_as": "",
     "target_tokens_per_1k_chars": "500.0", "baseline_tokens_per_1k_chars": "200.0",
     "baseline_chars": "1100", "target_chars": "1000"},
    {"source": "api", "family": "F", "model_id": "sampled", "coverage": "sample", "same_counts_as": "full",
     "target_tokens_per_1k_chars": "", "baseline_tokens_per_1k_chars": "",
     "baseline_chars": "", "target_chars": ""},
    {"source": "api", "family": "F", "model_id": "unmatched", "coverage": "sample", "same_counts_as": "",
     "target_tokens_per_1k_chars": "", "baseline_tokens_per_1k_chars": "",
     "baseline_chars": "", "target_chars": ""},
    {"source": "open", "family": "O", "model_id": "open-model", "coverage": "full", "same_counts_as": "",
     "target_tokens_per_1k_chars": "300.0", "baseline_tokens_per_1k_chars": "200.0",
     "baseline_chars": "1100", "target_chars": "1000"},
]
PRICES = {
    "exchange_rate": {"thb_per_usd": 30.0, "rate_date": "today", "what": "test rate"},
    "sources": {"api": {"fetched_utc": "now"}},
    "models": {
        "full": {"input_usd_per_mtok": 2.0, "output_usd_per_mtok": 10.0},
        "sampled": {"input_usd_per_mtok": 1.0, "output_usd_per_mtok": 5.0},
    },
}
SCENARIO = {"id": "s", "name": "S", "unit": "jobs", "unit_singular": "job", "units": 1000,
            "turns": 1, "system_chars": 0, "input_chars": 2000, "output_chars": 1000}


def test_cost_arithmetic_on_a_tiny_fixture():
    rows = {r["model_id"]: r for r in pricing.cost_rows(SUMMARY, PRICES, [SCENARIO])}

    full = rows["full"]
    # 1,000 jobs x 2,000 chars in = 2,000,000 chars -> x 500 / 1,000 = 1,000,000 Thai input tokens
    assert full["thai_input_tokens"] == 1_000_000 and full["thai_output_tokens"] == 500_000
    assert full["thai_usd"] == pytest.approx(1.0 * 2.0 + 0.5 * 10.0)  # $7
    assert full["thai_thb"] == pytest.approx(7.0 * 30.0)  # 210 baht
    # the same content in English is 1.1x the characters at 200 tokens per 1,000 chars
    assert full["english_input_tokens"] == pytest.approx(2_000_000 * 1.1 * 200 / 1000)
    assert full["english_thb"] == pytest.approx((0.44 * 2.0 + 0.22 * 10.0) * 30.0)
    assert full["thai_over_english_cost"] == pytest.approx(500 / (1.1 * 200))  # = the premium

    sampled = rows["sampled"]  # token rate of the full model it matched, but its own price
    assert sampled["token_rate_from"] == "full" and sampled["thai_input_tokens"] == 1_000_000
    assert sampled["thai_thb"] == pytest.approx((1.0 * 1.0 + 0.5 * 5.0) * 30.0)

    open_model = rows["open-model"]  # no list price: tokens only
    assert open_model["thai_input_tokens"] == 600_000 and open_model["thai_thb"] is None
    assert "unmatched" not in rows  # a sample that matched nothing has no token rate at all


def test_more_tokens_can_still_be_cheaper():
    summary = [dict(SUMMARY[0], model_id="many-tokens", target_tokens_per_1k_chars="900.0"),
               dict(SUMMARY[0], model_id="few-tokens", target_tokens_per_1k_chars="300.0")]
    prices = dict(PRICES, models={"many-tokens": {"input_usd_per_mtok": 0.1, "output_usd_per_mtok": 0.5},
                                  "few-tokens": {"input_usd_per_mtok": 10.0, "output_usd_per_mtok": 50.0}})
    rows = {r["model_id"]: r for r in pricing.cost_rows(summary, prices, [SCENARIO])}
    assert rows["many-tokens"]["thai_input_tokens"] > rows["few-tokens"]["thai_input_tokens"]
    assert rows["many-tokens"]["thai_thb"] < rows["few-tokens"]["thai_thb"]


def test_cost_stage_writes_files_and_updates_latest(tmp_path):
    results = tmp_path / "results"
    (tmp_path / "registry").mkdir()
    results.mkdir()
    (tmp_path / "registry" / "scenarios.toml").write_text(
        '[[scenario]]\nid = "s"\nname = "S"\nunit = "jobs"\nunit_singular = "job"\nunits = 1000\n'
        "turns = 1\nsystem_chars = 0\ninput_chars = 2000\noutput_chars = 1000\n", encoding="utf-8")
    with (results / "summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(SUMMARY[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(SUMMARY)
    (results / "latest.json").write_text(json.dumps({"summary_csv": "summary.csv"}), encoding="utf-8")
    (results / "prices_2026-01-01.json").write_text(json.dumps(PRICES), encoding="utf-8")

    pricing.run(tmp_path, results)
    latest = json.loads((results / "latest.json").read_text(encoding="utf-8"))
    assert latest["costs_csv"] == "costs_2026-01-01.csv" and latest["prices"] == "prices_2026-01-01.json"
    text = (results / "costs_2026-01-01.md").read_text(encoding="utf-8")
    assert "210.00" in text and all(limit in text for limit in pricing.LIMITS)
    with pytest.raises(Stop):  # never overwritten
        pricing.run(tmp_path, results)
