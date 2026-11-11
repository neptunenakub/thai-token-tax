"""The share cards show only what site/data.json says. No network, no browser."""
import copy
import hashlib
import json
import struct
import xml.etree.ElementTree as ET

import pytest

from thai_token_tax import card


@pytest.fixture(scope="module")
def data(repo):
    return json.loads((repo / "site" / "data.json").read_text(encoding="utf-8"))


def test_committed_cards_are_what_the_data_produces(repo, data):
    built = card.build(data)
    assert set(built) == {"card.th.svg", "card.en.svg"}
    for name, svg in built.items():
        assert (repo / "site" / name).read_text(encoding="utf-8") == svg, f"{name} is stale: run `ttt card`"
        root = ET.fromstring(svg)  # well-formed
        assert root.get("width") == root.get("height") == str(card.SIZE)


def test_card_numbers_come_from_the_data(data):
    head, pair = data["headline"], data["same_price_pairs"][0]
    th, en = card.svg(data, "th"), card.svg(data, "en")
    assert f"GPT {head['same_price_ratio']:.2f} เท่า" in th
    assert f"{pair['a_thai_thb']:,.0f} บาท" in th and f"{pair['b_thai_thb']:,.0f} บาท" in th
    assert f"{head['claude_over_gpt_tokens']:.2f}×" in en
    assert f"{head['claude_over_gemini_tokens']:.2f}×" in en
    for svg in (th, en):
        for key in ("claude", "gpt", "gemini", "gemini_other"):
            assert f">{head[key + '_thai_tokens_per_1k_chars']:,.1f}<" in svg
    assert "ไม่ใช่คุณภาพคำตอบ" in th and "not answer quality" in en

    changed = copy.deepcopy(data)  # different data must give different cards: nothing is typed in card.py
    changed["headline"]["same_price_ratio"] = 9.87
    changed["headline"]["claude_over_gpt_tokens"] = 8.76
    changed["headline"]["claude_thai_tokens_per_1k_chars"] = 123.4
    changed["same_price_pairs"][0]["a_thai_thb"] = 55555.0
    changed["dataset"]["sentence_pairs"] = 7777
    th2, en2 = card.svg(changed, "th"), card.svg(changed, "en")
    assert "GPT 9.87 เท่า" in th2 and "55,555 บาท" in th2 and ">123.4<" in th2 and "7,777" in th2
    assert "8.76×" in en2 and f"{head['claude_over_gpt_tokens']:.2f}×" not in en2


def test_png_cards_were_rendered_from_the_current_svg(repo):
    """A PNG is a screenshot, so it can go stale. cards.json records the SVG it was made from."""
    site = repo / "site"
    made = json.loads((site / "cards.json").read_text(encoding="utf-8"))
    assert set(made) == {"card.th.png", "card.en.png"}
    for name, info in made.items():
        svg = (site / info["from"]).read_bytes()
        stale = f"{name} is stale: run `ttt card --png`"
        assert hashlib.sha256(svg).hexdigest() == info["from_sha256"], stale
        header = (site / name).read_bytes()[:24]
        assert header[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", header[16:24]) == (card.SIZE, card.SIZE)
