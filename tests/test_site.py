"""The site shows only what the result files say. No network (one test uses Node if it is installed)."""
import csv
import json
import re
import shutil
import subprocess

import pytest

from thai_token_tax import Stop, site


@pytest.fixture(scope="module")
def sources(repo):
    """The result files, read directly (not through site.build)."""
    results = repo / "results"
    latest = json.loads((results / "latest.json").read_text(encoding="utf-8"))

    def rows(name):
        with (results / name).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    return {
        "latest": latest,
        "summary": {r["model_id"]: r for r in rows(latest["summary_csv"])},
        "costs": rows(latest["costs_csv"]),
        "prices": json.loads((results / latest["prices"]).read_text(encoding="utf-8")),
        "billing": json.loads((results / latest["billing_check"]).read_text(encoding="utf-8")),
    }


@pytest.fixture(scope="module")
def data(repo):
    return json.loads((repo / "site" / "data.json").read_text(encoding="utf-8"))


def test_committed_data_json_is_what_the_results_produce(repo, data):
    assert site.build(repo, repo / "results") == data  # stale? run `ttt site`


def test_every_group_value_equals_the_summary_file(data, sources):
    summary = sources["summary"]
    assert len(data["models"]) == len(summary)
    for group in data["groups"]:
        row = summary[group["leader"]]
        assert row["coverage"] == "full" and row["same_counts_as"] == ""
        assert group["thai_tokens_per_1k_chars"] == float(row["target_tokens_per_1k_chars"])
        assert group["english_tokens_per_1k_chars"] == float(row["baseline_tokens_per_1k_chars"])
        assert group["premium"] == float(row["premium"])
        assert group["premium_ci_low"] == float(row["ci95_low"])
        assert group["premium_ci_high"] == float(row["ci95_high"])
        assert group["thai_tokens"] == int(row["target_tokens"])
        for member in group["members"]:  # every member really gave the leader's counts
            source = summary[member["model_id"]]
            assert member["model_id"] == group["leader"] or source["same_counts_as"] == group["leader"]
            assert member["coverage"] == source["coverage"]
            assert member["sentence_pairs"] == int(source["n_sentences"])
    grouped = [m["model_id"] for g in data["groups"] for m in g["members"]]
    assert sorted(grouped) == sorted(m["model_id"] for m in data["models"] if m["group"])


def test_prices_costs_and_rate_equal_the_result_files(data, sources):
    prices = sources["prices"]
    assert data["exchange_rate"]["thb_per_usd"] == prices["exchange_rate"]["thb_per_usd"]
    for model in data["models"]:
        price = prices["models"].get(model["model_id"])
        assert model["input_usd_per_mtok"] == (price["input_usd_per_mtok"] if price else None)
        assert model["output_usd_per_mtok"] == (price["output_usd_per_mtok"] if price else None)
    priced = [r for r in sources["costs"] if r["thai_thb"]]
    assert sum(len(v) for v in data["costs"].values()) == len(priced)
    for r in priced:
        shown = data["costs"][r["scenario"]][r["model_id"]]
        assert shown == {"thai_thb": float(r["thai_thb"]), "english_thb": float(r["english_thb"])}


def test_headline_numbers_are_ratios_of_published_values(data, sources):
    summary, head = sources["summary"], data["headline"]

    def per_1k(model_id):
        row = summary[model_id]
        return float(summary[row["same_counts_as"] or model_id]["target_tokens_per_1k_chars"])

    assert head["claude_thai_tokens_per_1k_chars"] == per_1k("claude-opus-5-5")
    assert head["claude_over_gpt_tokens"] == per_1k("claude-opus-5-5") / per_1k("gpt-5.5")
    assert head["claude_over_gemini_tokens"] == per_1k("claude-opus-5-5") / per_1k("gemini-3.8-flash")
    chat = {r["model_id"]: float(r["thai_thb"]) for r in sources["costs"]
            if r["scenario"] == head["scenario"] and r["thai_thb"]}
    for pair in data["same_price_pairs"]:
        a, b = sources["prices"]["models"][pair["a"]], sources["prices"]["models"][pair["b"]]
        assert a["input_usd_per_mtok"] == b["input_usd_per_mtok"] == pair["input_usd_per_mtok"]
        assert a["output_usd_per_mtok"] == b["output_usd_per_mtok"] == pair["output_usd_per_mtok"]
        assert pair["ratio"] == chat[pair["a"]] / chat[pair["b"]]
    assert head["same_price_ratio"] == data["same_price_pairs"][0]["ratio"]
    billed = sources["billing"]["models"].values()
    assert data["billing_check"]["texts"] == sum(m["texts_compared"] for m in billed)


def test_not_measured_lists_only_models_without_any_measurement(data, sources):
    measured = set(sources["summary"])
    assert data["blocked"] and all(b["model_id"] not in measured for b in data["blocked"])
    assert {b["kind"] for b in data["blocked"]} <= {"gated", "custom_code", "withdrawn", "other"}


def test_the_page_contains_no_measured_number(repo, data):
    """Numbers must come from data.json at run time, never be typed into the page."""
    page = (repo / "site" / "index.html").read_text(encoding="utf-8")
    page = site.with_og(page, "")  # the link-preview tags are generated; they have their own test
    head = data["headline"]
    typed = {f"{head['same_price_ratio']:.2f}", f"{head['claude_over_gemini_tokens']:.2f}",
             f"{data['exchange_rate']['thb_per_usd']}", f"{data['dataset']['sentence_pairs']:,}",
             str(data["dataset"]["sentence_pairs"]), str(data["billing_check"]["texts"])}
    for group in data["groups"]:
        typed |= {f"{group['thai_tokens_per_1k_chars']:.0f}", f"{group['thai_tokens_per_1k_chars']:.1f}",
                  f"{group['premium']:.2f}", f"{group['premium']:.3f}"}
    for pair in data["same_price_pairs"]:
        typed |= {f"{pair['a_thai_thb']:,.0f}", f"{pair['b_thai_thb']:,.0f}"}
    found = [n for n in typed if re.search(rf"(?<![\d.,#]){re.escape(n)}(?![\d.,]|px|rem|em|%|deg)", page)]
    assert found == []


def copy_inputs(repo, tmp_path):
    """A small copy of what site.build reads, so a test can break one input."""
    latest = json.loads((repo / "results" / "latest.json").read_text(encoding="utf-8"))
    names = [latest[k] for k in ("summary_csv", "costs_csv", "costs_json", "prices", "billing_check")]
    names += ["latest.json", *latest["counts_meta"].values()]
    (tmp_path / "results").mkdir()
    for name in names:
        shutil.copy(repo / "results" / name, tmp_path / "results" / name)
    shutil.copytree(repo / "registry", tmp_path / "registry")
    (tmp_path / "data").mkdir()
    shutil.copy(repo / "data" / "source_floresplus.json", tmp_path / "data")
    return tmp_path


def edit(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_build_stops_when_a_label_names_a_model_outside_its_group(repo, tmp_path):
    root = copy_inputs(repo, tmp_path)
    wrong = 'named = ["gemini-4-argon", "gpt-5.5"]'
    edit(root / "registry" / "display.toml", 'named = ["gemini-4-argon"]', wrong)
    with pytest.raises(Stop, match="did not give the same counts"):
        site.build(root, root / "results")


def test_build_stops_when_a_scenario_changed_after_the_costs(repo, tmp_path):
    root = copy_inputs(repo, tmp_path)
    edit(root / "registry" / "scenarios.toml", "turns = 6", "turns = 7")
    with pytest.raises(Stop, match="Run `ttt cost`"):
        site.build(root, root / "results")


def test_build_stops_when_same_price_pairs_no_longer_share_a_price(repo, tmp_path):
    root = copy_inputs(repo, tmp_path)
    edit(root / "registry" / "display.toml", 'b = "gpt-5.6-sol"', 'b = "gpt-5.5"')
    with pytest.raises(Stop, match="same list price"):
        site.build(root, root / "results")


def test_build_stops_when_costs_belong_to_another_summary(repo, tmp_path):
    root = copy_inputs(repo, tmp_path)
    latest = json.loads((root / "results" / "latest.json").read_text(encoding="utf-8"))
    with (root / "results" / latest["summary_csv"]).open("a", encoding="utf-8") as f:
        f.write("\n")
    with pytest.raises(Stop, match="not computed from the current summary"):
        site.build(root, root / "results")


def test_the_page_formula_gives_the_published_cost_table(repo, data, sources, tmp_path):
    """Run the calculator's own JavaScript (cut out of the page) on every preset and priced model."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed; the page also runs this check itself on load")
    page = (repo / "site" / "index.html").read_text(encoding="utf-8")
    formula = page.split("/* CALC-START", 1)[1].split("*/", 1)[1].split("/* CALC-END */", 1)[0]
    script = tmp_path / "check.js"
    script.write_text(formula + """
const D = JSON.parse(require("fs").readFileSync(process.argv[2], "utf8"));
const out = [];
for (const s of D.scenarios) for (const m of D.models) {
  if (m.input_usd_per_mtok == null || !m.group) continue;
  const g = D.groups.find((x) => x.leader === m.group);
  const rates = { thai: g.thai_tokens_per_1k_chars, english: g.english_tokens_per_1k_chars };
  const c = estimateCost(s, rates, m, D.exchange_rate.thb_per_usd, D.dataset.english_chars_per_thai_char);
  out.push([s.id, m.model_id, c.thai.thb, c.english.thb, c.thai.input_tokens, c.thai.output_tokens]);
}
console.log(JSON.stringify(out));
""", encoding="utf-8")
    answer = subprocess.run([node, str(script), str(repo / "site" / "data.json")],
                            capture_output=True, text=True, check=True)
    computed = {(s, m): values for s, m, *values in json.loads(answer.stdout)}
    published = [r for r in sources["costs"] if r["thai_thb"]]
    assert len(computed) == len(published) > 0
    for r in published:
        thai, english, tokens_in, tokens_out = computed[(r["scenario"], r["model_id"])]
        assert thai == pytest.approx(float(r["thai_thb"]), abs=1e-5)
        assert english == pytest.approx(float(r["english_thb"]), abs=1e-5)
        assert tokens_in == pytest.approx(float(r["thai_input_tokens"]), abs=1e-3)
        assert tokens_out == pytest.approx(float(r["thai_output_tokens"]), abs=1e-3)


def test_link_preview_tags_are_generated_and_absent_without_a_site_url(repo, data):
    page = (repo / "site" / "index.html").read_text(encoding="utf-8")
    config = json.loads((repo / "site" / "config.json").read_text(encoding="utf-8"))
    assert site.with_og(page, site.og_block(data, config)) == page  # stale? run `ttt site`
    assert site.og_block(data, {"site_url": None}) == ""
    assert "og:image" not in site.with_og(page, "")

    block = site.og_block(data, {"site_url": "https://example.org/thai-token-tax", "og_lang": "th"})
    assert '<meta property="og:image" content="https://example.org/thai-token-tax/card.th.png">' in block
    assert '<meta property="og:url" content="https://example.org/thai-token-tax/">' in block
    assert f"GPT {data['headline']['same_price_ratio']:.2f} เท่า" in block
    english = site.og_block(data, {"site_url": "https://example.org/x/", "og_lang": "en"})
    assert "https://example.org/x/card.en.png" in english
    assert f"{data['headline']['claude_over_gpt_tokens']:.2f}× the tokens on Claude" in english
    filled = site.with_og(page, block)
    assert block in filled and site.with_og(filled, "") == site.with_og(page, "")  # can be undone
