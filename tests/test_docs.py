"""README.md, README.th.md and docs/methodology.md say only what the result files say. No network."""
import csv
import json
import re
import shutil
import tomllib

import pytest

from thai_token_tax import Stop, __version__, docs, site


@pytest.fixture(scope="module")
def built(repo):
    return docs.build(repo, repo / "results")


@pytest.fixture(scope="module")
def data(repo):
    return site.build(repo, repo / "results")


def test_committed_documents_are_what_the_results_produce(repo, built):
    for target, text in built.items():
        assert (repo / target).read_text(encoding="utf-8") == text, f"{target} is stale: run `ttt docs`"


def test_no_placeholder_is_left_unfilled(built):
    assert set(built) == {"README.md", "README.th.md", "docs/methodology.md",
                          "blog/thai-token-tax.th.md", "blog/thai-token-tax.en.md", "blog/posts.md"}
    for target, text in built.items():
        assert "{{" not in text and "}}" not in text, target


def test_templates_contain_no_measured_number(repo, data):
    """Numbers must come from the result files when `ttt docs` runs, never be typed into a template."""
    head = data["headline"]
    typed = {f"{head['same_price_ratio']:.2f}", f"{head['claude_over_gemini_tokens']:.2f}",
             f"{data['exchange_rate']['thb_per_usd']}", f"{data['dataset']['sentence_pairs']:,}",
             str(data["dataset"]["sentence_pairs"]), str(data["billing_check"]["texts"]),
             str(len(data["models"])), f"{data['dataset']['thai_chars']:,}",
             f"{data['dataset']['english_chars']:,}", f"{data['dataset']['english_chars_per_thai_char']:.3f}"}
    for group in data["groups"]:
        typed |= {f"{group['thai_tokens_per_1k_chars']:.0f}", f"{group['thai_tokens_per_1k_chars']:.1f}",
                  f"{group['english_tokens_per_1k_chars']:.1f}", f"{group['premium']:.2f}",
                  f"{group['premium']:.3f}", f"{group['premium_ci_low']:.3f}",
                  f"{group['premium_ci_high']:.3f}"}
    for costs in data["costs"].values():
        for cost in costs.values():
            typed.add(f"{cost['thai_thb']:,.2f}")
            if cost["thai_thb"] >= 100:  # smaller amounts round to numbers like "4" or "11"
                typed.add(f"{cost['thai_thb']:,.0f}")
    for template in docs.TARGETS:
        text = (repo / template).read_text(encoding="utf-8")
        found = [n for n in typed if re.search(rf"(?<![\d.,]){re.escape(n)}(?![\d.,]*\d)", text)]
        assert found == [], template


def test_unknown_placeholder_stops():
    with pytest.raises(Stop, match="unknown placeholder"):
        docs.render("a {{not_a_value}} b", {"x": "1"}, "t.md")
    assert docs.render("a {{x}} b", {"x": "1"}, "t.md").endswith("a 1 b")


def test_headline_is_recomputed_from_the_raw_counts(repo, built):
    """Independent of summary, site and docs code: straight from the per-sentence count files."""
    results = repo / "results"
    latest = json.loads((results / "latest.json").read_text(encoding="utf-8"))

    def thai_tokens_per_1k_chars(source, model_id):
        tokens = chars = 0
        with (results / latest["counts"][source]).open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row["model_id"] == model_id and row["lang"] == "tha_Thai":
                    tokens += int(row["n_tokens"])
                    chars += int(row["n_chars"])
        assert chars > 0
        return 1000 * tokens / chars

    claude = thai_tokens_per_1k_chars("anthropic", "claude-opus-5-5")
    gpt = thai_tokens_per_1k_chars("openai", "gpt-5.5")
    gemini = thai_tokens_per_1k_chars("gemini", "gemini-3.8-flash")
    english = (f"**The same Thai text takes {claude / gpt:.2f}× the tokens on Claude as on GPT, "
               f"and {claude / gemini:.2f}× as on Gemini.**")
    assert english in built["README.md"]
    assert f"| {claude:.1f} |" in built["README.md"] and f"| {gpt:.1f} |" in built["README.md"]
    assert f"มากกว่า GPT {claude / gpt:.2f} เท่า" in built["README.th.md"]
    rates = f"{claude:.1f} (Claude), {gpt:.1f} (GPT), {gemini:.1f} (Gemini 3.x)"
    assert rates in built["docs/methodology.md"]


def test_both_readmes_give_the_same_three_commands(repo, built):
    config = json.loads((repo / "site" / "config.json").read_text(encoding="utf-8"))
    address = config["repo_url"] or "REPO_URL"  # a placeholder until the repository exists
    commands = (f"```\ngit clone {address} thai-token-tax && cd thai-token-tax\n"
                "pip install -e .\nttt all --out rerun\n```")
    for target in ("README.md", "README.th.md", "blog/thai-token-tax.th.md", "blog/thai-token-tax.en.md"):
        assert commands in built[target], target


def test_methodology_tables_equal_the_verification_and_billing_files(repo, built):
    results = repo / "results"
    latest = json.loads((results / "latest.json").read_text(encoding="utf-8"))
    text = built["docs/methodology.md"]
    overheads = 0
    for name in latest["verification"].values():
        for check in json.loads((results / name).read_text(encoding="utf-8"))["checks"]:
            if "overhead_subtracted" in check:
                overheads += 1
                row = (rf"\| `{re.escape(check['model_id'])}` \| `POST [^|]+` \| "
                       rf"{check['overhead_subtracted']} \| constant \| constant \| 0 differ \|")
                assert re.search(row, text)
    assert overheads >= 6
    billing = json.loads((results / latest["billing_check"]).read_text(encoding="utf-8"))
    for model, b in billing["models"].items():
        assert f"| `{model}` | {b['texts_compared']} | equal for every request |" in text
    assert f"${billing['cost']['actual_usd']:.6f}" in text


def copy_inputs(repo, tmp_path):
    """A copy of what docs.build reads (without the large per-sentence files)."""
    shutil.copytree(repo / "results", tmp_path / "results",
                    ignore=shutil.ignore_patterns("counts_*.csv", "open_counts_*.csv", "floresplus"))
    for folder in ("registry", "templates"):
        shutil.copytree(repo / folder, tmp_path / folder)
    (tmp_path / "data").mkdir()
    for name in ("source.json", "source_floresplus.json", "normalization_log.json"):
        shutil.copy(repo / "data" / name, tmp_path / "data")
    (tmp_path / "site").mkdir()
    shutil.copy(repo / "site" / "config.json", tmp_path / "site")
    return tmp_path


def code_blocks(text, heading):
    """The fenced blocks under one `## heading` of blog/posts.md."""
    section = text.split(f"## {heading}\n")[1].split("\n## ")[0]
    return re.findall(r"```\n(.*?)\n```", section, flags=re.S)


def x_length(post):
    """Length as X counts it: a link is 23, most scripts (Latin, Thai) are 1 per character, the rest 2."""
    post = re.sub(r"https?://\S+|SITE_URL|REPO_URL", "x" * 23, post)
    light = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))
    return sum(1 if any(a <= ord(c) <= b for a, b in light) else 2 for c in post)


def test_post_drafts_fit_their_limits_and_use_only_the_two_hashtags(built):
    posts = built["blog/posts.md"]
    for heading in ("X thread, Thai", "X thread, English"):
        thread = code_blocks(posts, heading)
        assert 1 <= len(thread) <= 6, heading
        assert all(x_length(post) <= 280 for post in thread), [x_length(post) for post in thread]
    title = code_blocks(posts, "Show HN")[0]
    assert title.startswith("Show HN: ") and len(title) <= 80
    for heading in ("LinkedIn, English", "LinkedIn, Thai", "Facebook groups (Thai developers / AI)"):
        assert len(code_blocks(posts, heading)) == 1
    hashtags = set(re.findall(r"#[^\s#`]+", "\n".join(re.findall(r"```\n(.*?)\n```", posts, flags=re.S))))
    assert hashtags == {"#ภาษีภาษา", "#ThaiTokenTax"}
    assert "@" not in posts.replace("noreply@", "")  # nobody is tagged


def test_articles_give_finding_size_and_caveat_before_the_first_section(built, data):
    head = data["headline"]
    pairs = f"{data['dataset']['sentence_pairs']:,}"
    english = built["blog/thai-token-tax.en.md"]
    lead = english.split("\n## ")[0]
    assert f"{head['claude_over_gpt_tokens']:.2f}×" in lead
    assert f"{head['claude_over_gemini_tokens']:.2f}×" in lead
    assert pairs in lead and "not answer" in lead
    prose = re.sub(r"```.*?```|<!--.*?-->", "", english, flags=re.S)
    words = len(" ".join(line for line in prose.splitlines() if not line.startswith("|")).split())
    assert 700 <= words <= 1100, words
    thai_lead = built["blog/thai-token-tax.th.md"].split("\n## ")[0]
    assert f"{head['same_price_ratio']:.2f} เท่า" in thai_lead and pairs in thai_lead
    assert "ไม่ได้วัดคุณภาพคำตอบ" in thai_lead


def test_a_price_refresh_does_not_block_site_and_documents(repo, tmp_path):
    """A later `ttt prices` and `ttt cost` add a newer price and cost set. The billing check still
    points at the older prices file; that must not stop `ttt site` or `ttt docs`."""
    from thai_token_tax import pricing

    root = copy_inputs(repo, tmp_path)
    results = root / "results"
    latest = json.loads((results / "latest.json").read_text(encoding="utf-8"))
    prices = json.loads((results / latest["prices"]).read_text(encoding="utf-8"))
    for source in prices["sources"].values():
        source["fetched_utc"] = "2099-01-02T03:04:05Z"
    (results / "prices_2099-01-02.json").write_text(json.dumps(prices), encoding="utf-8")
    pricing.run(root, results)
    latest = json.loads((results / "latest.json").read_text(encoding="utf-8"))
    assert latest["prices"] == "prices_2099-01-02.json"
    assert site.build(root, results)["dates"]["prices"] == "2099-01-02"
    assert "2 January 2099" in docs.build(root, results)["README.md"]


def test_repo_url_from_the_config_fills_the_clone_command(repo, tmp_path):
    root = copy_inputs(repo, tmp_path)
    (root / "site" / "config.json").write_text('{"repo_url": "https://example.org/x/thai-token-tax"}',
                                               encoding="utf-8")
    text = docs.build(root, root / "results")["README.md"]
    assert "git clone https://example.org/x/thai-token-tax thai-token-tax" in text
    assert "REPO_URL" not in text


def test_documents_are_not_written_when_a_stated_claim_stops_being_true(repo, tmp_path):
    """The templates say in words that billed input equalled count_tokens. If a rerun finds otherwise,
    `ttt docs` must stop rather than keep the sentence."""
    root = copy_inputs(repo, tmp_path)
    latest = json.loads((root / "results" / "latest.json").read_text(encoding="utf-8"))
    path = root / "results" / latest["billing_check"]
    billing = json.loads(path.read_text(encoding="utf-8"))
    next(iter(billing["models"].values()))["billed_input_vs_count_tokens"] = "different for 1 text"
    path.write_text(json.dumps(billing), encoding="utf-8")
    with pytest.raises(Stop, match="billed input tokens equal count_tokens"):
        docs.build(root, root / "results")


def test_licence_files_version_and_citation_agree(repo):
    licences = tomllib.loads((repo / "registry" / "display.toml").read_text(encoding="utf-8"))["licences"]
    mit = (repo / "LICENSE").read_text(encoding="utf-8")
    cc = (repo / "LICENSE-DATA").read_text(encoding="utf-8")
    assert licences["code"] == "MIT" and mit.startswith("MIT License") and licences["holder"] in mit
    assert licences["results"] == "CC BY 4.0" and "Attribution 4.0 International" in cc
    assert licences["holder"] in cc and "CC BY-SA 4.0" in cc  # FLORES attribution
    page = (repo / "site" / "index.html").read_text(encoding="utf-8")
    assert "CC BY" not in page and "MIT" not in page  # licence names reach the page through data.json
    project = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    citation = (repo / "CITATION.cff").read_text(encoding="utf-8")
    assert project["version"] == __version__
    assert re.search(rf"^version: {re.escape(__version__)}$", citation, re.M)
    assert f"## {__version__}" in (repo / "CHANGELOG.md").read_text(encoding="utf-8")
