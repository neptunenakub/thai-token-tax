"""`ttt docs`: write the README files, the methodology, and the articles and post drafts
from their templates.

Reads  templates/*.md, the same result files as `ttt site` (through site.build), the count
       metadata and verification files, data/*.json, site/config.json
Writes the three documents

A template is plain Markdown with {{placeholders}}. Every measured number, date, file name
and table in the documents is a placeholder, filled here from the result files; no number is
typed into a template (a test checks both that and that the committed documents are current).
To change the wording, edit the template and run `ttt docs`.
"""

from __future__ import annotations

import re
import tomllib
from datetime import date
from pathlib import Path

from . import Stop, __version__, site
from .site import read_json

# template -> (document, language)
TARGETS = {
    "templates/readme.en.md": ("README.md", "en"),
    "templates/readme.th.md": ("README.th.md", "th"),
    "templates/methodology.en.md": ("docs/methodology.md", "en"),
    "templates/blog.th.md": ("blog/thai-token-tax.th.md", "th"),
    "templates/blog.en.md": ("blog/thai-token-tax.en.md", "en"),
    "templates/posts.md": ("blog/posts.md", "en"),  # Thai values are used as {{th_...}}
}
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
BAR_WIDTH = 24
REPO_URL_PLACEHOLDER = "REPO_URL"  # shown until site/config.json has a repo_url
SITE_URL_PLACEHOLDER = "SITE_URL"  # shown until site/config.json has a site_url

MONTHS = {
    "en": [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
    "th": [
        "มกราคม",
        "กุมภาพันธ์",
        "มีนาคม",
        "เมษายน",
        "พฤษภาคม",
        "มิถุนายน",
        "กรกฎาคม",
        "สิงหาคม",
        "กันยายน",
        "ตุลาคม",
        "พฤศจิกายน",
        "ธันวาคม",
    ],
}
# Words used inside generated tables. Sentences live in the templates, not here.
WORDS = {
    "en": {
        "baht": "{n} baht",
        "times": "{n}×",
        "api": "API",
        "open": "open models only",
        "full": "full run",
        "sample": "sample, {n} pairs",
        "yes": "yes",
        "no": "no",
        "constant": "constant",
        "varies": "VARIES",
        "not_known": "not known to tiktoken",
        "differ": "{n} differ",
        "input": "input",
        "output": "output",
        "none": "none",
        "gated": "gated repository, access not granted (HTTP {code})",
        "custom_code": "no tokenizer.json; would need code from the repository to be executed (HTTP {code})",
        "withdrawn": "the API says the model is no longer available to new users (HTTP {code})",
        "other": "could not be downloaded or called (HTTP {code})",
        "h_tokenizer": "Tokenizer (models that share it)",
        "h_thai_1k": "Tokens per 1,000 Thai characters",
        "h_english_1k": "per 1,000 English characters",
        "h_premium": "Thai ÷ English (95% CI)",
        "h_kind": "Type",
        "h_models": "Models",
        "h_price": "List price, $ per 1M tokens (in / out)",
        "h_model": "Model",
        "h_thai_thb": "Thai",
        "h_english_thb": "Same content in English",
        "h_ratio": "Ratio",
        "h_scenario": "Scenario",
        "h_units": "Volume",
        "h_turns": "Turns",
        "h_system": "System prompt, chars",
        "h_input": "Input per turn, chars",
        "h_output": "Output per turn, chars",
        "h_history": "History resent",
        "h_reason": "Why not measured",
        "h_measured": "Measured on",
        "h_matches": "Identical counts to",
        "h_endpoint": "Counted with",
        "h_overhead": "Overhead subtracted",
        "h_length": "Length check ({a}–{b} words)",
        "h_content": "Content check ({n} conversations)",
        "h_repeat": "Repeat ({n} sentences)",
        "h_local": "Against tiktoken, per sentence",
        "h_texts": "Requests",
        "h_billed": "Billed input vs `count_tokens`",
        "h_billed_minus": "Billed input − published content tokens",
        "h_cost": "Cost, USD",
        "h_language": "Language",
        "h_sentences": "Sentences",
        "h_nfc": "Changed by NFC",
        "h_strip": "Changed by removing control/format characters",
        "h_trim": "Changed by trimming",
        "h_total": "Changed in total",
        "h_removed": "Characters removed",
        "h_provider": "Provider",
        "h_page": "Official page",
        "h_fetched": "Fetched (UTC)",
        "h_sp_sentences": "sentences counted differently",
        "h_sp_json": "Thai tokens, `tokenizer.json` (published)",
        "h_sp_file": "Thai tokens, SentencePiece file",
        "eng_Latn": "English",
        "tha_Thai": "Thai",
        "equal": "equal for every request",
        "not_equal": "NOT equal for every request",
    },
    "th": {
        "baht": "{n} บาท",
        "times": "{n} เท่า",
        "api": "API",
        "open": "โมเดลเปิดเท่านั้น",
        "full": "เต็มชุด",
        "sample": "สุ่ม {n} คู่",
        "yes": "ใช่",
        "no": "ไม่",
        "none": "ไม่มี",
        "gated": "repo จำกัดการเข้าถึง ยังไม่ได้รับสิทธิ์ (HTTP {code})",
        "custom_code": "ไม่มีไฟล์ tokenizer.json ต้องรันโค้ดจาก repo ซึ่งโปรเจคนี้ไม่ทำ (HTTP {code})",
        "withdrawn": "API แจ้งว่าโมเดลนี้ไม่เปิดให้ผู้ใช้ใหม่แล้ว (HTTP {code})",
        "other": "ดาวน์โหลดหรือเรียกใช้ไม่สำเร็จ (HTTP {code})",
        "h_tokenizer": "Tokenizer (โมเดลที่ใช้ร่วมกัน)",
        "h_thai_1k": "token ต่อ 1,000 ตัวอักษรไทย",
        "h_english_1k": "ต่อ 1,000 ตัวอักษรอังกฤษ",
        "h_premium": "ไทย ÷ อังกฤษ (95% CI)",
        "h_kind": "ประเภท",
        "h_models": "จำนวนโมเดล",
        "h_price": "ราคาป้าย $ ต่อล้าน token (เข้า / ออก)",
        "h_model": "โมเดล",
        "h_thai_thb": "ภาษาไทย",
        "h_english_thb": "เนื้อหาเดียวกันเป็นภาษาอังกฤษ",
        "h_ratio": "อัตราส่วน",
        "h_scenario": "งานตัวอย่าง",
        "h_units": "จำนวนงาน",
        "h_turns": "รอบต่องาน",
        "h_system": "system prompt (ตัวอักษร)",
        "h_input": "ข้อความเข้าต่อรอบ (ตัวอักษร)",
        "h_output": "ข้อความออกต่อรอบ (ตัวอักษร)",
        "h_history": "ส่งประวัติซ้ำ",
        "h_reason": "เหตุที่ยังไม่ได้วัด",
        "input": "ขาเข้า",
        "output": "ขาออก",
    },
}


def num(value: float, digits: int = 0) -> str:
    return f"{value:,.{digits}f}"


def usd_price(value: float) -> str:
    return f"${value:.2f}" if value < 1 or value != int(value) else f"${value:.0f}"


def long_date(iso: str, lang: str) -> str:
    d = date.fromisoformat(iso[:10])
    return f"{d.day} {MONTHS[lang][d.month - 1]} {d.year}"


def bar(value: float, longest: float) -> str:
    return "█" * max(1, round(BAR_WIDTH * value / longest))


def table(header: list[str], rows: list[list[str]], right: tuple[int, ...] = ()) -> str:
    """A Markdown table. `right` lists the columns to align right (numbers)."""
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---:" if i in right else "---" for i in range(len(header))) + "|",
    ]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def values(root: Path, results: Path, lang: str) -> dict[str, str]:
    """Everything a template may use, as text in the given language."""
    w = WORDS[lang]
    d = site.build(root, results)  # the same checked data the site shows
    latest = read_json(results / "latest.json")
    summary = read_json(results / latest["summary_json"])
    costs = read_json(results / latest["costs_json"])
    prices = read_json(results / latest["prices"])
    billing = read_json(results / latest["billing_check"])
    metas = {name: read_json(results / f) for name, f in latest["counts_meta"].items()}
    checks = [c for f in latest["verification"].values() for c in read_json(results / f)["checks"]]
    source = read_json(root / "data" / "source.json")
    norm = read_json(root / "data" / "normalization_log.json")
    plus = read_json(root / "data" / "source_floresplus.json")
    comparisons = sorted(results.glob("comparison_flores200_vs_floresplus_*.json"))
    if not comparisons:
        raise Stop("no FLORES-200 vs FLORES+ comparison in results/. Run `ttt compare`.")
    comparison = read_json(comparisons[-1])
    display = tomllib.loads((root / "registry" / "display.toml").read_text(encoding="utf-8"))
    config = read_json(root / "site" / "config.json")
    repo_url, site_url = config.get("repo_url"), config.get("site_url")

    groups = {g["leader"]: g for g in d["groups"]}
    models = {m["model_id"]: m for m in d["models"]}
    head = d["headline"]

    def name(model_id: str) -> str:
        return d["names"].get(model_id, f"`{model_id}`")

    def baht(v: float) -> str:
        return w["baht"].format(n=num(v, 2 if v < 100 else 0))

    def times(v: float, digits: int = 2) -> str:
        return w["times"].format(n=num(v, digits))

    def group_of(model_id: str) -> dict:
        return groups[models[model_id]["group"]]

    def premium(g: dict) -> str:
        return f"{g['premium']:.3f} ({g['premium_ci_low']:.3f}–{g['premium_ci_high']:.3f})"

    def kind(g: dict) -> str:
        return w["api"] if g["api"] else w["open"]

    def price(m: dict) -> str:
        return f"{usd_price(m['input_usd_per_mtok'])} / {usd_price(m['output_usd_per_mtok'])}"

    scenarios = {s["id"]: s for s in d["scenarios"]}

    def scenario_name(s: dict) -> str:
        return s.get("name_th", s["name"]) if lang == "th" else s["name"]

    longest = max(g["thai_tokens_per_1k_chars"] for g in d["groups"])
    headline_groups = [group_of(display["headline"][k]) for k in ("claude", "gpt", "gemini", "gemini_other")]
    chat = d["costs"][head["scenario"]]
    priced = sorted(
        (m for m in d["models"] if m["model_id"] in chat), key=lambda m: chat[m["model_id"]]["thai_thb"]
    )
    pair1, pair2 = d["same_price_pairs"][0], d["same_price_pairs"][1]
    sample_sizes = sorted({m["sentence_pairs"] for m in d["models"] if m["coverage"] == "sample"})
    overheads = sorted(
        {o for m in d["billing_check"]["models"].values() for o in m["billed_overhead_tokens"]}, reverse=True
    )
    counter = d["notes"]["counterexample"]
    generations = d["notes"]["generations"]
    thai_group = groups[d["notes"]["thai_models_group"]]
    open_checks = [c for c in checks if "overhead_subtracted" not in c]
    api_checks = [c for c in checks if "overhead_subtracted" in c]
    languages = [k for k in norm if isinstance(norm[k], dict) and "sentences" in norm[k]]
    libraries = sorted(
        {m["library"] for meta in metas.values() for m in meta["measured"] if "==" in m["library"]}
    )
    measured_info = {m["model_id"]: m for meta in metas.values() for m in meta["measured"]}

    # Sentences in the templates that are true only while the results say so. If one stops being
    # true the documents are not written; the wording has to be changed by a person.
    claims = {
        "a model with more tokens is cheaper than one with fewer (the counterexample)": counter is not None,
        "two Claude generations differ in English but not in Thai": generations is not None,
        "FLORES+ and FLORES-200 are identical after normalization and give identical counts": (
            d["flores_plus"]["thai_sentences_that_differ"] + d["flores_plus"]["english_sentences_that_differ"]
            == 0
            and all(r["identical_counts"] for r in comparison["rows"])
        ),
        "billed input tokens equal count_tokens on every request": d["billing_check"]["all_equal"],
        "billed input minus content tokens equals the subtracted overhead": all(
            b["billed_input_minus_published_content"] == [b["overhead_subtracted_in_results"]]
            for b in billing["models"].values()
        ),
        "every API overhead check found a constant overhead": all(
            c["length_check_constant"] and c["content_check_constant"] and c["repeat_check_mismatch"] == 0
            for c in api_checks
        ),
        "the second count of every local tokenizer agrees with the first": all(
            c[code]["recount_mismatch"] == 0 and c[code].get("transformers_mismatch", 0) == 0
            for c in open_checks
            for code in languages
        ),
    }
    for claim, holds in claims.items():
        if not holds:
            raise Stop(f"the templates say that {claim}, but the results no longer do. Edit templates/.")

    v: dict[str, str] = {
        "version": __version__,
        "clone_url": repo_url or REPO_URL_PLACEHOLDER,
        "site_url": site_url or SITE_URL_PLACEHOLDER,
        "urls_note": ""
        if repo_url and site_url
        else f"`{SITE_URL_PLACEHOLDER}` and `{REPO_URL_PLACEHOLDER}` stand for the page and the repository: "
        "set `site_url` and `repo_url` in `site/config.json`, then run `ttt docs` again.",
        "site_ref": f"<{site_url}>" if site_url else "[`site/`](site/)",
        "repo_url_note": ""
        if repo_url
        else {
            "en": f"`{REPO_URL_PLACEHOLDER}` is a placeholder: the repository address is filled in from "
            "`site/config.json` when the repository is published.",
            "th": f"`{REPO_URL_PLACEHOLDER}` เป็นช่องว่างรอที่อยู่ repo ซึ่งจะเติมจาก `site/config.json` เมื่อเผยแพร่",
        }[lang],
        # the finding
        "ratio_price": num(head["same_price_ratio"], 2),
        "ratio_gpt": num(head["claude_over_gpt_tokens"], 2),
        "ratio_gemini": num(head["claude_over_gemini_tokens"], 2),
        "claude_1k": num(head["claude_thai_tokens_per_1k_chars"], 1),
        "gpt_1k": num(head["gpt_thai_tokens_per_1k_chars"], 1),
        "gemini_1k": num(head["gemini_thai_tokens_per_1k_chars"], 1),
        "gemini_other_1k": num(head["gemini_other_thai_tokens_per_1k_chars"], 1),
        "claude_premium": premium(group_of(display["headline"]["claude"])),
        "gpt_premium": premium(group_of(display["headline"]["gpt"])),
        "scenario": scenario_name(scenarios[head["scenario"]]),
        "pair1_a": name(pair1["a"]),
        "pair1_b": name(pair1["b"]),
        "pair1_a_thb": baht(pair1["a_thai_thb"]),
        "pair1_b_thb": baht(pair1["b_thai_thb"]),
        "pair1_in": usd_price(pair1["input_usd_per_mtok"]),
        "pair1_out": usd_price(pair1["output_usd_per_mtok"]),
        "pair2_a": name(pair2["a"]),
        "pair2_b": name(pair2["b"]),
        "pair2_a_thb": baht(pair2["a_thai_thb"]),
        "pair2_b_thb": baht(pair2["b_thai_thb"]),
        "pair1_diff_thb": baht(pair1["a_thai_thb"] - pair1["b_thai_thb"]),
        "claude_p2": num(group_of(display["headline"]["claude"])["premium"], 2),
        "gpt_p2": num(group_of(display["headline"]["gpt"])["premium"], 2),
        "gemini_p2": num(group_of(display["headline"]["gemini"])["premium"], 2),
        "claude_english_1k": num(group_of(display["headline"]["claude"])["english_tokens_per_1k_chars"], 1),
        "gpt_english_1k": num(group_of(display["headline"]["gpt"])["english_tokens_per_1k_chars"], 1),
        "short_claude": head["short"]["claude"],
        "short_gpt": head["short"]["gpt"],
        "short_gemini": head["short"]["gemini"],
        "short_gemini_other": head["short"]["gemini_other"],
        "n_open_measured": num(len(metas["open"]["measured"])),
        "pair2_in": usd_price(pair2["input_usd_per_mtok"]),
        "pair2_out": usd_price(pair2["output_usd_per_mtok"]),
        # scale and dates
        "n_models": num(len(d["models"])),
        "n_groups": num(len(d["groups"])),
        "n_priced": num(len(priced)),
        "n_blocked": num(len(d["blocked"])),
        "pairs": num(d["dataset"]["sentence_pairs"]),
        "thai_chars": num(d["dataset"]["thai_chars"]),
        "english_chars": num(d["dataset"]["english_chars"]),
        "en_per_th": num(d["dataset"]["english_chars_per_thai_char"], 3),
        "date_data": long_date(d["dates"]["data"], lang),
        "date_prices": long_date(d["dates"]["prices"], lang),
        "date_rate": long_date(d["dates"]["exchange_rate"], lang),
        "date_billing": long_date(d["dates"]["billing_check"], lang),
        "rate": num(d["exchange_rate"]["thb_per_usd"], 3),
        "rate_what": prices["exchange_rate"]["what"],
        "rate_page": d["exchange_rate"]["page"],
        # files
        "summary_md": latest["summary_md"],
        "summary_csv": latest["summary_csv"],
        "costs_md": latest["costs_md"],
        "costs_csv": latest["costs_csv"],
        "prices_json": latest["prices"],
        "billing_json": latest["billing_check"],
        "billing_md": latest["billing_check"].replace(".json", ".md"),
        "comparison_md": comparisons[-1].with_suffix(".md").name,
        "counts_files": ", ".join(f"`{f}`" for f in latest["counts"].values()),
        "counts_open": latest["counts"]["open"],
        # method parameters (read from the result files, so they cannot drift from the code)
        "ci_level": num(summary["ci"]["level"] * 100),
        "ci_resamples": num(summary["ci"]["resamples"]),
        "ci_seed": str(summary["ci"]["seed"]),
        "ci_method": summary["ci"]["method"],
        "sample_size": " / ".join(num(n) for n in sample_sizes),
        "sample_seed": str(metas["anthropic"]["sample"]["seed"]),
        "n_sampled": num(sum(m["coverage"] == "sample" for m in d["models"])),
        "n_full": num(sum(m["coverage"] == "full" for m in d["models"])),
        "python": metas["open"]["python"],
        "libraries": ", ".join(f"`{x}`" for x in libraries),
        "rate_limit_anthropic": num(
            measured_info[display["headline"]["claude"]]["requests_per_minute_limit_used"]
        ),
        # data provenance
        "flores_url": source["official_release"]["url"],
        "flores_tarball_sha256": source["official_release"]["sha256"],
        "flores_mb": num(source["official_release"]["bytes"] / 1e6),
        "tsv_sha256": source["normalized_tsv"]["sha256"],
        "unicode_version": norm["unicode_data_version"],
        "fp_version": d["flores_plus"]["version"],
        "fp_revision": plus["revision"],
        "fp_diff": num(
            d["flores_plus"]["thai_sentences_that_differ"] + d["flores_plus"]["english_sentences_that_differ"]
        ),
        "fp_tokenizers": num(len(comparison["rows"])),
        "fp_identical": num(sum(r["identical_counts"] for r in comparison["rows"])),
        # verification of the local tokenizers
        "open_checked": num(len(open_checks)),
        "open_recount_mismatch": num(
            sum(c[lang_]["recount_mismatch"] for c in open_checks for lang_ in languages)
        ),
        "open_roundtrip_min": num(
            min(c[lang_]["roundtrip_exact"] for c in open_checks for lang_ in languages)
        ),
        "open_unk": num(sum(c[lang_].get("unk_tokens", 0) for c in open_checks for lang_ in languages)),
        "open_transformers_checked": num(sum("transformers_class" in c for c in open_checks)),
        "open_transformers_mismatch": num(
            sum(c[lang_].get("transformers_mismatch", 0) for c in open_checks for lang_ in languages)
        ),
        # billing check
        "bill_texts": num(d["billing_check"]["texts"]),
        "bill_cost": f"${billing['cost']['actual_usd']:.6f}",
        "bill_cap": f"${billing['cost']['cap_usd']:.2f}",
        "bill_what": billing["what"],
        "overheads": " / ".join(num(o) for o in overheads),
        "thai_group_label": thai_group["label"][lang],
        "thai_group_1k": num(thai_group["thai_tokens_per_1k_chars"], 1),
        "thai_group_models": num(len(thai_group["members"])),
        "lic_code": d["licences"]["code"],
        "lic_results": d["licences"]["results"],
        "lic_dataset": d["licences"]["dataset"],
        "holder": d["licences"]["holder"],
    }
    if counter:
        v |= {
            "counter_more": name(counter["more_tokens"]),
            "counter_fewer": name(counter["fewer_tokens"]),
            "counter_more_thb": baht(counter["more_tokens_thai_thb"]),
            "counter_fewer_thb": baht(counter["fewer_tokens_thai_thb"]),
            "counter_more_1k": num(counter["more_tokens_thai_per_1k_chars"], 1),
            "counter_fewer_1k": num(counter["fewer_tokens_thai_per_1k_chars"], 1),
        }
    if generations:
        old, new = group_of(generations["older"]), group_of(generations["newer"])
        v |= {
            "gen_old": name(generations["older"]),
            "gen_new": name(generations["newer"]),
            "gen_old_premium": num(old["premium"], 3),
            "gen_new_premium": num(new["premium"], 3),
            "gen_old_thai": num(old["thai_tokens_per_1k_chars"], 1),
            "gen_new_thai": num(new["thai_tokens_per_1k_chars"], 1),
            "gen_old_english": num(old["english_tokens_per_1k_chars"], 1),
            "gen_new_english": num(new["english_tokens_per_1k_chars"], 1),
        }

    # --- tables ------------------------------------------------------------------------------
    v["table_headline"] = table(
        [w["h_tokenizer"], w["h_thai_1k"], ""],
        [
            [
                g["label"][lang],
                num(g["thai_tokens_per_1k_chars"], 1),
                bar(g["thai_tokens_per_1k_chars"], longest),
            ]
            for g in headline_groups
        ],
        right=(1,),
    )
    v["table_groups"] = table(
        [w["h_tokenizer"], w["h_kind"], w["h_thai_1k"], "", w["h_english_1k"], w["h_premium"], w["h_models"]],
        [
            [
                g["label"][lang],
                kind(g),
                num(g["thai_tokens_per_1k_chars"], 1),
                bar(g["thai_tokens_per_1k_chars"], longest),
                num(g["english_tokens_per_1k_chars"], 1),
                premium(g),
                num(len(g["members"])),
            ]
            for g in d["groups"]
        ],
        right=(2, 4, 6),
    )
    v["table_pairs"] = table(
        [w["h_price"], w["h_model"], w["h_thai_thb"], w["h_model"], w["h_thai_thb"], w["h_ratio"]],
        [
            [
                price(models[p["a"]]),
                name(p["a"]),
                baht(p["a_thai_thb"]),
                name(p["b"]),
                baht(p["b_thai_thb"]),
                times(p["ratio"]),
            ]
            for p in d["same_price_pairs"]
        ],
        right=(2, 4, 5),
    )
    v["table_costs"] = table(
        [w["h_model"], w["h_price"], w["h_thai_thb"], w["h_english_thb"], w["h_ratio"]],
        [
            [
                name(m["model_id"]),
                price(m),
                baht(chat[m["model_id"]]["thai_thb"]),
                baht(chat[m["model_id"]]["english_thb"]),
                times(chat[m["model_id"]]["thai_thb"] / chat[m["model_id"]]["english_thb"]),
            ]
            for m in priced
        ],
        right=(2, 3, 4),
    )
    v["table_scenarios"] = table(
        [
            w["h_scenario"],
            w["h_units"],
            w["h_turns"],
            w["h_system"],
            w["h_input"],
            w["h_output"],
            w["h_history"],
        ],
        [
            [
                scenario_name(s),
                num(s["units"]),
                num(s["turns"]),
                num(s["system_chars"]),
                num(s["input_chars"]),
                num(s["output_chars"]),
                w["yes"] if s["resend_history"] else w["no"],
            ]
            for s in d["scenarios"]
        ],
        right=(1, 2, 3, 4, 5),
    )
    v["table_blocked"] = table(
        [w["h_model"], w["h_reason"]],
        [[f"`{b['model_id']}`", w[b["kind"]].format(code=b["http_status"])] for b in d["blocked"]],
    )
    v["list_price_end_dates"] = "\n".join(
        f'- {name(m)}: {w["input"]} "{text["input"]}" {w["output"]} "{text["output"]}"'
        for m, text in d["price_page_text"].items()
    )
    if lang != "en":
        return v

    # --- English only: the methodology tables ------------------------------------------------
    v["list_limits_costs"] = "\n".join(f"- {line}" for line in costs["limits"])
    v["list_normalization_rules"] = "\n".join(f"    {line}" for line in norm["rules"])
    v["table_normalization"] = table(
        [
            w["h_language"],
            w["h_sentences"],
            w["h_nfc"],
            w["h_strip"],
            w["h_trim"],
            w["h_total"],
            w["h_removed"],
        ],
        [
            [
                w[code],
                num(norm[code]["sentences"]),
                num(norm[code]["changed_by_nfc"]),
                num(norm[code]["changed_by_control_or_format_strip"]),
                num(norm[code]["changed_by_trim"]),
                num(norm[code]["changed_total"]),
                ", ".join(f"{k} × {n}" for k, n in norm[code]["removed_or_replaced_characters"].items())
                or w["none"],
            ]
            for code in languages
        ],
        right=(1, 2, 3, 4, 5),
    )

    def local_check(c: dict) -> str:
        t = c["tiktoken_check"]
        if isinstance(t, str):
            return w["not_known"]
        return f"`{t['encoding']}`: " + w["differ"].format(n=num(sum(t[code] for code in languages)))

    steps = [int(k) for c in api_checks for k in c["length_check_raw_minus_words"]]
    v["table_overheads"] = table(
        [
            w["h_model"],
            w["h_endpoint"],
            w["h_overhead"],
            w["h_length"].format(a=min(steps), b=max(steps)),
            w["h_content"].format(n=api_checks[0]["content_check_triples"]),
            w["h_repeat"].format(n=api_checks[0]["repeat_check_sentences"]),
            w["h_local"],
        ],
        [
            [
                f"`{c['model_id']}`",
                f"`{measured_info[c['model_id']]['tokenizer']}`",
                num(c["overhead_subtracted"]),
                w["constant"] if c["length_check_constant"] else w["varies"],
                w["constant"] if c["content_check_constant"] else w["varies"],
                w["differ"].format(n=num(c["repeat_check_mismatch"])),
                local_check(c),
            ]
            for c in api_checks
        ],
        right=(2,),
    )
    v["table_samples"] = table(
        [w["h_model"], w["h_measured"], w["h_matches"]],
        [
            [
                f"`{m['model_id']}`",
                w["sample"].format(n=num(m["sentence_pairs"])),
                f"`{m['group']}`" if m["group"] else w["none"],
            ]
            for m in d["models"]
            if m["coverage"] == "sample"
        ],
    )
    v["table_billing"] = table(
        [w["h_model"], w["h_texts"], w["h_billed"], w["h_billed_minus"], w["h_overhead"], w["h_cost"]],
        [
            [
                f"`{m}`",
                num(b["texts_compared"]),
                w["equal"] if b["billed_input_vs_count_tokens"] == "equal for every text" else w["not_equal"],
                " / ".join(num(x) for x in b["billed_input_minus_published_content"]),
                num(b["overhead_subtracted_in_results"]),
                f"{b['actual_cost_usd']:.6f}",
            ]
            for m, b in billing["models"].items()
        ],
        right=(1, 3, 4, 5),
    )
    v["table_price_sources"] = table(
        [w["h_provider"], w["h_page"], w["h_fetched"]],
        [[p, f"<{s['url']}>", s["fetched_utc"]] for p, s in prices["sources"].items()],
    )
    # Repositories that ship a SentencePiece file next to tokenizer.json: the two may count differently.
    with_sp = [c for c in open_checks if c.get("has_sentencepiece_model")]
    sp_differ = [c for c in with_sp if any(c[code]["sentencepiece_mismatch"] for code in languages)]
    published = {r["model_id"]: r for r in summary["rows"]}
    v["sp_checked"] = num(len(with_sp))
    v["sp_differ"] = num(len(sp_differ))
    v["table_sentencepiece"] = table(
        [
            w["h_model"],
            *(f"{w[code]}: {w['h_sp_sentences']}" for code in languages),
            w["h_sp_json"],
            w["h_sp_file"],
        ],
        [
            [
                f"`{c['model_id']}`",
                *(num(c[code]["sentencepiece_mismatch"]) for code in languages),
                num(published[c["model_id"]]["target_tokens"]),
                num(c[published[c["model_id"]]["target_lang"]]["sentencepiece_total"]),
            ]
            for c in sp_differ
        ],
        right=(1, 2, 3, 4),
    )
    return v


def render(template: str, vals: dict[str, str], template_name: str) -> str:
    def fill(match: re.Match) -> str:
        if match[1] not in vals:
            raise Stop(f"{template_name}: unknown placeholder {{{{{match[1]}}}}}")
        return vals[match[1]]

    note = f"<!-- Generated by `ttt docs` from {template_name}. Edit the template, not this file. -->\n"
    return note + PLACEHOLDER.sub(fill, template)


def build(root: Path, results: Path) -> dict[str, str]:
    """-> {document path: text} for every template."""
    cache: dict[str, dict[str, str]] = {}
    out = {}
    for template_name, (target, lang) in TARGETS.items():
        other = "th" if lang == "en" else "en"
        for code in (lang, other):
            if code not in cache:
                cache[code] = values(root, results, code)
        # A document may also use the other language's values, as {{th_name}} or {{en_name}}.
        vals = cache[lang] | {f"{other}_{k}": v for k, v in cache[other].items()}
        out[target] = render((root / template_name).read_text(encoding="utf-8"), vals, template_name)
    return out


def run(root: Path, results: Path) -> None:
    for target, text in build(root, results).items():
        path = root / target
        path.parent.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path}")
