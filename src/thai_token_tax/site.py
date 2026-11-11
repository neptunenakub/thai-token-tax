"""`ttt site`: write site/data.json, the only thing the web page reads.

Reads  results/latest.json and the files it points to (summary, costs, prices, billing check,
       counts metadata), data/source_floresplus.json, registry/scenarios.toml, registry/display.toml
Writes site/data.json, and the link-preview tags in site/index.html (only when site/config.json
       has a site_url; see og_block)

The page (site/index.html) contains no measured number: it renders this file. The file is a
pure function of its inputs (no timestamp), so a test can rebuild it and compare.
Before writing, the inputs are checked against each other; a mismatch stops the build
instead of publishing numbers that do not belong together.
"""
from __future__ import annotations

import csv
import json
import tomllib
from datetime import datetime
from html import escape
from pathlib import Path

from . import Stop, sha256_file

SCENARIO_NUMBERS = ("units", "turns", "system_chars", "input_chars", "output_chars", "resend_history")
OG_START = "<!-- OG-START: written by `ttt site` from data.json once site/config.json has a site_url -->"
OG_END = "<!-- OG-END -->"
CARD_SIZE = 1080  # the share cards written by `ttt card`
# Wording of the link preview. Numbers are filled from the data.
OG_TEXT = {
    "th": {
        "locale": "th_TH",
        "title": "ราคาป้ายเท่ากัน แต่งานภาษาไทยบน Claude จ่ายแพงกว่า GPT {ratio_price} เท่า",
        "description": "วัดต้นทุน ไม่ใช่คุณภาพคำตอบ · {models} โมเดล · คู่ประโยคไทย–อังกฤษ {pairs} คู่ · "
                       "ราคาป้าย ณ {date_prices}",
    },
    "en": {
        "locale": "en_US",
        "title": "The same Thai text takes {ratio_gpt}× the tokens on Claude as on GPT, "
                 "and {ratio_gemini}× as on Gemini",
        "description": "Cost, not answer quality · {models} models · {pairs} parallel Thai–English "
                       "sentences · list prices as of {date_prices}",
    },
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def blocked_kind(entry: dict) -> str:
    """Why a model could not be measured, as one of a few plain categories."""
    if entry["error_type"] == "GatedRepoError":
        return "gated"
    if "no tokenizer.json" in entry["reason"]:
        return "custom_code"
    if "no longer available" in entry["error_first_line"]:
        return "withdrawn"
    return "other"


def build(root: Path, results: Path) -> dict:
    latest = read_json(results / "latest.json")
    summary = read_csv(results / latest["summary_csv"])
    costs_json = read_json(results / latest["costs_json"])
    costs = read_csv(results / latest["costs_csv"])
    prices = read_json(results / latest["prices"])
    billing = read_json(results / latest["billing_check"])
    display = tomllib.loads((root / "registry" / "display.toml").read_text(encoding="utf-8"))
    scenarios = tomllib.loads((root / "registry" / "scenarios.toml").read_text(encoding="utf-8"))["scenario"]
    flores_plus = read_json(root / "data" / "source_floresplus.json")

    # --- the inputs must belong together ---------------------------------------------------
    for label, name in (("summary", latest["summary_csv"]), ("prices", latest["prices"])):
        if costs_json["inputs"][label]["sha256"] != sha256_file(results / name):
            raise Stop(f"the costs were not computed from the current {label} file. Run `ttt cost`.")
    # The billing check may have used an older prices file: what it found (billed tokens equal
    # counted tokens) does not depend on a price, and its own cost is not shown as a current price.
    used = {s["id"]: s for s in costs_json["scenarios"]}
    for s in scenarios:
        if any(used.get(s["id"], {}).get(k) != s.get(k) for k in SCENARIO_NUMBERS):
            raise Stop(f"scenario {s['id']} changed after the costs were computed. Run `ttt cost`.")

    api_families = set(display["api_families"])
    by_id = {r["model_id"]: r for r in summary}
    full = {m: r for m, r in by_id.items() if r["coverage"] == "full"}

    def leader_of(row: dict) -> str | None:
        if row["same_counts_as"]:
            return row["same_counts_as"]
        return row["model_id"] if row["coverage"] == "full" else None  # an unmatched sample has none

    # --- tokenizer groups: models with identical counts ----------------------------------------
    labels = {g["leader"]: g for g in display.get("group", [])}
    groups = []
    for leader, row in full.items():
        if row["same_counts_as"]:
            continue
        members = [r for r in summary if leader_of(r) == leader]
        ids = {r["model_id"] for r in members}
        label = labels.get(leader, {"en": leader, "th": leader, "named": []})
        missing = [m for m in label.get("named", []) if m not in ids]
        if missing:
            raise Stop(f"registry/display.toml names {missing} in the group of {leader}, "
                       "but they did not give the same counts")
        groups.append({
            "leader": leader,
            "label": {"en": label["en"], "th": label["th"]},
            "api": any(r["family"] in api_families for r in members),
            "thai_tokens_per_1k_chars": float(row["target_tokens_per_1k_chars"]),
            "english_tokens_per_1k_chars": float(row["baseline_tokens_per_1k_chars"]),
            "premium": float(row["premium"]),
            "premium_ci_low": float(row["ci95_low"]),
            "premium_ci_high": float(row["ci95_high"]),
            "thai_tokens": int(row["target_tokens"]),
            "english_tokens": int(row["baseline_tokens"]),
            "members": [
                {"model_id": r["model_id"], "coverage": r["coverage"],
                 "sentence_pairs": int(r["n_sentences"])}
                for r in members
            ],
        })
    groups.sort(key=lambda g: -g["thai_tokens_per_1k_chars"])

    # --- every measured model, for the table and the calculator ---------------------------
    models = []
    for r in summary:
        leader = leader_of(r)
        price = prices["models"].get(r["model_id"])
        models.append({
            "model_id": r["model_id"],
            "family": r["family"],
            "api": r["family"] in api_families,
            "coverage": r["coverage"],
            "sentence_pairs": int(r["n_sentences"]),
            "group": leader,
            "input_usd_per_mtok": price["input_usd_per_mtok"] if price else None,
            "output_usd_per_mtok": price["output_usd_per_mtok"] if price else None,
        })

    # --- costs of the preset scenarios (also what the page checks its own formula against) ------
    cost_table: dict = {}
    for r in costs:
        if r["thai_thb"]:
            cost_table.setdefault(r["scenario"], {})[r["model_id"]] = {
                "thai_thb": float(r["thai_thb"]), "english_thb": float(r["english_thb"]),
            }

    head = display["headline"]
    chat = cost_table[head["scenario"]]
    pairs = []
    for pair in display["same_price_pair"]:
        a, b = prices["models"][pair["a"]], prices["models"][pair["b"]]
        same = all(a[k] == b[k] for k in ("input_usd_per_mtok", "output_usd_per_mtok"))
        if not same:
            raise Stop(f"{pair['a']} and {pair['b']} no longer have the same list price")
        pairs.append({
            "a": pair["a"], "b": pair["b"],
            "input_usd_per_mtok": a["input_usd_per_mtok"], "output_usd_per_mtok": a["output_usd_per_mtok"],
            "a_thai_thb": chat[pair["a"]]["thai_thb"], "b_thai_thb": chat[pair["b"]]["thai_thb"],
            "ratio": chat[pair["a"]]["thai_thb"] / chat[pair["b"]]["thai_thb"],
        })

    def per_1k(model_id: str) -> float:
        return float(full[leader_of(by_id[model_id])]["target_tokens_per_1k_chars"])

    headline = {
        "scenario": head["scenario"],
        "same_price_ratio": pairs[0]["ratio"],
        "claude_thai_tokens_per_1k_chars": per_1k(head["claude"]),
        "gpt_thai_tokens_per_1k_chars": per_1k(head["gpt"]),
        "gemini_thai_tokens_per_1k_chars": per_1k(head["gemini"]),
        "gemini_other_thai_tokens_per_1k_chars": per_1k(head["gemini_other"]),
        "claude_over_gpt_tokens": per_1k(head["claude"]) / per_1k(head["gpt"]),
        "claude_over_gemini_tokens": per_1k(head["claude"]) / per_1k(head["gemini"]),
        "short": head["short"],
    }

    # --- notes that are shown only while the numbers still support them --------------------
    more, fewer = display["counterexample"]["more_tokens"], display["counterexample"]["fewer_tokens"]
    counterexample = None
    if per_1k(more) > per_1k(fewer) and chat[more]["thai_thb"] < chat[fewer]["thai_thb"]:
        counterexample = {
            "more_tokens": more, "fewer_tokens": fewer,
            "more_tokens_thai_per_1k_chars": per_1k(more), "fewer_tokens_thai_per_1k_chars": per_1k(fewer),
            "more_tokens_thai_thb": chat[more]["thai_thb"], "fewer_tokens_thai_thb": chat[fewer]["thai_thb"],
        }
    old, new = (full[leader_of(by_id[display["generations"][k]])] for k in ("older", "newer"))
    thai_change = float(new["target_tokens_per_1k_chars"]) / float(old["target_tokens_per_1k_chars"])
    english_change = float(new["baseline_tokens_per_1k_chars"]) / float(old["baseline_tokens_per_1k_chars"])
    generations = None
    if abs(thai_change - 1) < 0.02 and english_change > 1.10:
        generations = {"older": old["model_id"], "newer": new["model_id"]}
    thai_models_group = leader_of(by_id[display["thai_models"]["group"]])

    # --- not measured: blocked in some run and never measured in any -------------------------
    blocked, measured = {}, set(by_id)
    for name in latest["counts_meta"].values():
        for entry in read_json(results / name)["blocked"]:
            if entry["model_id"] not in measured:
                blocked[entry["model_id"]] = {
                    "model_id": entry["model_id"], "family": entry["family"],
                    "kind": blocked_kind(entry), "http_status": entry["http_status"],
                }

    reference = next(iter(full.values()))
    plus_vs_200 = flores_plus["comparison_with_flores200"]
    rate = prices["exchange_rate"]
    return {
        "inputs": {
            name: sha256_file(results / name)
            for name in (latest[k] for k in ("summary_csv", "costs_csv", "prices", "billing_check"))
        },
        "dates": {
            "data": latest["run_date_utc"],
            "prices": min(s["fetched_utc"] for s in prices["sources"].values())[:10],
            "exchange_rate": datetime.strptime(rate["rate_date"], "%d %B %Y").date().isoformat(),
            "billing_check": billing["run_utc"][:10],
        },
        "dataset": {
            "sentence_pairs": int(reference["n_sentences"]),
            "thai_chars": int(reference["target_chars"]),
            "english_chars": int(reference["baseline_chars"]),
            "english_chars_per_thai_char": int(reference["baseline_chars"]) / int(reference["target_chars"]),
        },
        "exchange_rate": {"thb_per_usd": rate["thb_per_usd"], "page": rate["page"]},
        "price_sources": {p: s["url"] for p, s in prices["sources"].items()},
        "price_page_text": {
            m: {"input": p["page_text_input"], "output": p["page_text_output"]}
            for m, p in prices["models"].items()
            if "starting" in p["page_text_input"]  # the page announces a price change
        },
        "headline": headline,
        "names": display.get("names", {}),
        "notes": {"counterexample": counterexample, "generations": generations,
                  "thai_models_group": thai_models_group},
        "same_price_pairs": pairs,
        "groups": groups,
        "models": models,
        "scenarios": scenarios,
        "costs": cost_table,
        "billing_check": {
            "texts": sum(m["texts_compared"] for m in billing["models"].values()),
            "all_equal": all(
                m["billed_input_vs_count_tokens"] == "equal for every text"
                for m in billing["models"].values()
            ),
            "models": {
                m: {"texts": v["texts_compared"],
                    "billed_overhead_tokens": v["billed_input_minus_published_content"],
                    "overhead_subtracted": v["overhead_subtracted_in_results"]}
                for m, v in billing["models"].items()
            },
        },
        "flores_plus": {
            "version": flores_plus["version_in_changelog"].split(" ")[0],
            "sentence_pairs": plus_vs_200["pairs"],
            "thai_sentences_that_differ": plus_vs_200["tha_Thai_sentences_that_differ"],
            "english_sentences_that_differ": plus_vs_200["eng_Latn_sentences_that_differ"],
        },
        "blocked": list(blocked.values()),
        "licences": display["licences"],
    }


def og_block(data: dict, config: dict) -> str:
    """Open Graph / Twitter tags for link previews, as HTML lines.

    A preview needs the absolute address of its image, so there are no tags until
    site/config.json has a `site_url`. `og_lang` ("th" or "en") picks the wording and the card."""
    site_url = config.get("site_url")
    if not site_url:
        return ""
    base = site_url.rstrip("/") + "/"
    lang = config.get("og_lang") or "th"
    head = data["headline"]
    values = {
        "ratio_price": f"{head['same_price_ratio']:.2f}",
        "ratio_gpt": f"{head['claude_over_gpt_tokens']:.2f}",
        "ratio_gemini": f"{head['claude_over_gemini_tokens']:.2f}",
        "models": len(data["models"]), "pairs": f"{data['dataset']['sentence_pairs']:,}",
        "date_prices": data["dates"]["prices"],
    }
    text = {k: escape(v.format(**values), quote=True) for k, v in OG_TEXT[lang].items()}
    image = escape(f"{base}card.{lang}.png", quote=True)
    return "\n".join([
        f'<link rel="canonical" href="{escape(base, quote=True)}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:url" content="{escape(base, quote=True)}">',
        f'<meta property="og:locale" content="{text["locale"]}">',
        f'<meta property="og:title" content="{text["title"]}">',
        f'<meta property="og:description" content="{text["description"]}">',
        f'<meta property="og:image" content="{image}">',
        f'<meta property="og:image:width" content="{CARD_SIZE}">',
        f'<meta property="og:image:height" content="{CARD_SIZE}">',
        '<meta name="twitter:card" content="summary">',
        f'<meta name="twitter:title" content="{text["title"]}">',
        f'<meta name="twitter:description" content="{text["description"]}">',
        f'<meta name="twitter:image" content="{image}">',
    ])


def with_og(page: str, block: str) -> str:
    """The page with the text between the OG markers replaced by `block`."""
    if page.count(OG_START) != 1 or page.count(OG_END) != 1:
        raise Stop("site/index.html must contain the OG-START and OG-END markers exactly once")
    before, rest = page.split(OG_START)
    _, after = rest.split(OG_END)
    return before + OG_START + "\n" + (block + "\n" if block else "") + OG_END + after


def run(root: Path, results: Path) -> Path:
    out = root / "site" / "data.json"
    out.parent.mkdir(exist_ok=True)
    data = build(root, results)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    page_path = root / "site" / "index.html"
    page = page_path.read_text(encoding="utf-8")
    new_page = with_og(page, og_block(data, read_json(root / "site" / "config.json")))
    if new_page != page:
        page_path.write_text(new_page, encoding="utf-8", newline="\n")
        print(f"updated the link-preview tags in {page_path}")
    print(f"{len(data['groups'])} tokenizer groups, {len(data['models'])} models, "
          f"{len(data['scenarios'])} scenarios, {len(data['blocked'])} not measured -> {out}")
    return out
