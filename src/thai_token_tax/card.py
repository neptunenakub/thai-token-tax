"""`ttt card`: write the share cards site/card.th.svg and site/card.en.svg.

Reads  site/data.json (written by `ttt site`)
Writes site/card.th.svg, site/card.en.svg
       with --png also site/card.th.png, site/card.en.png and site/cards.json

The cards are square (1080 x 1080) pictures for posts: headline, the two figures behind it,
the four-bar chart, "cost, not answer quality", and the dates. Every number comes from
data.json; the wording is in TEXT below, with {placeholders}.

PNG export uses a Chrome or Edge that is already installed (headless screenshot). It is
not needed for anything else, so it is no dependency of the package. site/cards.json records
which SVG each PNG was made from; a test fails if a PNG is older than its SVG.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import date
from html import escape
from pathlib import Path

from . import Stop

SIZE = 1080
MARGIN = 72
LANGS = ("th", "en")
FONT = 'system-ui, -apple-system, "Segoe UI", "Leelawadee UI", "Noto Sans Thai", sans-serif'
# The site's light theme (site/index.html).
BG, PANEL, INK, INK2, LINE, ACCENT = "#fcfcfb", "#f4f3ee", "#0b0b0b", "#52514e", "#e1e0d9", "#2a78d6"

MONTHS = {
    "th": ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}
# Wording only. No measured number is written here.
TEXT = {
    "th": {
        "name": "ภาษีภาษา · Thai Token Tax",
        "headline": ["ราคาป้ายเท่ากัน", "แต่งานภาษาไทยบน Claude", "จ่ายแพงกว่า GPT {ratio_price} เท่า"],
        "figures_cap": ["ตัวอย่าง: {scenario}", "ราคาป้ายเท่ากันที่ {pin} / {pout} ต่อล้าน token (เข้า / ออก)"],
        "amount": "{n} บาท",
        "bars_cap": "สาเหตุ: จำนวน token ต่อข้อความไทย 1,000 ตัวอักษร",
        "caveat": "วัดต้นทุน ไม่ใช่คุณภาพคำตอบ",
        "foot": "ข้อมูลวัด {date_data} · ราคาป้าย ณ {date_prices} · FLORES-200 {pairs} คู่ประโยค",
    },
    "en": {
        "name": "Thai Token Tax · ภาษีภาษา",
        "headline": ["The same Thai text takes {ratio_gpt}×", "the tokens on Claude as on GPT,",
                     "and {ratio_gemini}× as on Gemini"],
        "figures_cap": ["Tokens {claude} spends on the same Thai text,", "compared with:"],
        "ratio": "{n}×",
        "bars_cap": "Tokens per 1,000 Thai characters",
        "caveat": "Cost, not answer quality",
        "foot": "Data {date_data} · list prices {date_prices} · FLORES-200, {pairs} sentence pairs",
    },
}
BROWSERS = (
    "chrome", "google-chrome", "chromium", "chromium-browser", "msedge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def short_date(iso: str, lang: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {MONTHS[lang][d.month - 1]} {d.year}"


def usd(value: float) -> str:
    return f"${value:.2f}" if value < 1 or value != int(value) else f"${value:.0f}"


def text(x: float, y: float, content: str, size: int, weight: int = 400, fill: str = INK,
         anchor: str = "start") -> str:
    return (f'<text x="{x:g}" y="{y:g}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}">{escape(content)}</text>')


def bar(x: float, y: float, width: float, height: float, radius: float = 6) -> str:
    """A bar anchored at the left, with a rounded data end on the right."""
    w = max(width, radius)
    r, flat = f"{radius:g}", w - radius
    return (f'<path d="M{x:g} {y:g}h{flat:g}a{r} {r} 0 0 1 {r} {r}v{height - 2 * radius:g}'
            f'a{r} {r} 0 0 1 -{r} {r}h{-flat:g}z" fill="{ACCENT}"/>')


def svg(data: dict, lang: str) -> str:
    t, head, pair = TEXT[lang], data["headline"], data["same_price_pairs"][0]
    scenario = next(s for s in data["scenarios"] if s["id"] == head["scenario"])
    values = {
        "ratio_price": f"{head['same_price_ratio']:.2f}",
        "ratio_gpt": f"{head['claude_over_gpt_tokens']:.2f}",
        "ratio_gemini": f"{head['claude_over_gemini_tokens']:.2f}",
        "scenario": scenario.get("name_th", scenario["name"]) if lang == "th" else scenario["name"],
        "pin": usd(pair["input_usd_per_mtok"]), "pout": usd(pair["output_usd_per_mtok"]),
        "claude": head["short"]["claude"],
        "date_data": short_date(data["dates"]["data"], lang),
        "date_prices": short_date(data["dates"]["prices"], lang),
        "pairs": f"{data['dataset']['sentence_pairs']:,}",
    }
    names = data["names"]
    if lang == "th":  # the two baht figures behind the Thai headline
        figures = [(names.get(pair[k], pair[k]), t["amount"].format(n=f"{pair[k + '_thai_thb']:,.0f}"))
                   for k in ("a", "b")]
    else:  # the two token ratios behind the English headline
        figures = [(head["short"]["gpt"], t["ratio"].format(n=values["ratio_gpt"])),
                   (head["short"]["gemini"], t["ratio"].format(n=values["ratio_gemini"]))]
    rows = [(head["short"][k], head[f"{k}_thai_tokens_per_1k_chars"])
            for k in ("claude", "gpt", "gemini", "gemini_other")]
    longest = max(v for _, v in rows)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}" '
        f'font-family=\'{FONT}\' role="img" aria-label="{escape(" ".join(t["headline"]).format(**values))}">',
        f'<rect width="{SIZE}" height="{SIZE}" fill="{BG}"/>',
        text(MARGIN, 104, t["name"], 34, 600, INK2),
    ]
    for i, line in enumerate(t["headline"]):
        out.append(text(MARGIN, 204 + i * 78, line.format(**values), 60, 700))

    # the two figures
    top = 418
    out.append(f'<rect x="0" y="{top}" width="{SIZE}" height="262" fill="{PANEL}"/>')
    for i, line in enumerate(t["figures_cap"]):
        out.append(text(MARGIN, top + 50 + i * 40, line.format(**values), 30, 400, INK2))
    column = (SIZE - 2 * MARGIN - 48) / 2
    for i, (label, amount) in enumerate(figures):
        x = MARGIN + i * (column + 48)
        out.append(f'<rect x="{x:g}" y="{top + 116}" width="{column:g}" height="3" fill="{INK}"/>')
        out.append(text(x, top + 160, label, 32, 400, INK2))
        out.append(text(x, top + 236, amount, 72, 700))

    # the four bars
    top = 742
    out.append(text(MARGIN, top, t["bars_cap"], 30, 400, INK2))
    label_width, track = 240, 520
    for i, (label, value) in enumerate(rows):
        y = top + 28 + i * 50
        out.append(text(MARGIN, y + 29, label, 32))
        width = track * value / longest
        out.append(bar(MARGIN + label_width, y + 4, width, 30))
        out.append(text(MARGIN + label_width + width + 16, y + 30, f"{value:,.1f}", 34, 700))

    out.append(f'<rect x="{MARGIN}" y="972" width="{SIZE - 2 * MARGIN}" height="2" fill="{LINE}"/>')
    out.append(text(MARGIN, 1016, t["caveat"], 34, 700))
    out.append(text(MARGIN, 1054, t["foot"].format(**values), 26, 400, INK2))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def build(data: dict) -> dict[str, str]:
    """-> {file name in site/: SVG text}"""
    return {f"card.{lang}.svg": svg(data, lang) for lang in LANGS}


def find_browser() -> str | None:
    for candidate in BROWSERS:
        found = shutil.which(candidate) or (candidate if os.path.isfile(candidate) else None)
        if found:
            return found
    return None


def export_png(site: Path, names: list[str]) -> None:
    browser = find_browser()
    if not browser:
        raise Stop("no Chrome or Edge found for --png. Open each site/card.*.svg in a browser at "
                   f"{SIZE} x {SIZE} and save a screenshot as site/card.<lang>.png instead.")
    made = {}
    for name in names:
        source, target = site / name, site / name.replace(".svg", ".png")
        target.unlink(missing_ok=True)
        subprocess.run(
            [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
             f"--window-size={SIZE},{SIZE}", f"--screenshot={target.resolve()}", source.resolve().as_uri()],
            check=True, capture_output=True, timeout=120,
        )
        if not target.exists():
            raise Stop(f"{browser} did not write {target}")
        made[target.name] = {"from": name, "from_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
        print(f"wrote {target}")
    (site / "cards.json").write_text(json.dumps(made, indent=1) + "\n", encoding="utf-8", newline="\n")


def run(root: Path, png: bool = False) -> None:
    site = root / "site"
    data_path = site / "data.json"
    if not data_path.exists():
        raise Stop(f"{data_path} is missing. Run `ttt site` first.")
    cards = build(json.loads(data_path.read_text(encoding="utf-8")))
    for name, content in cards.items():
        (site / name).write_text(content, encoding="utf-8", newline="\n")
        print(f"wrote {site / name}")
    if png:
        export_png(site, list(cards))
