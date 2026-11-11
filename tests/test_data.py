"""Normalization and alignment. No network."""
import pytest

from thai_token_tax import Stop
from thai_token_tax.data import check_alignment, load_languages, normalize, normalize_all, split_lines


def test_nfc_composes_decomposed_characters():
    out, stats = normalize("café")  # e + combining acute accent
    assert out == "café"
    assert stats["nfc_changed"] and stats["changed"]


def test_zero_width_and_format_characters_are_deleted():
    out, stats = normalize("ภาษา​ไทย﻿")  # zero-width space, BOM
    assert out == "ภาษาไทย"
    assert stats["strip_changed"]
    assert sum(stats["removed"].values()) == 2


def test_whitespace_controls_become_a_space_and_other_controls_are_deleted():
    assert normalize("a\tb")[0] == "a b"  # TAB must not glue two words together
    assert normalize("a\x00b")[0] == "ab"


def test_edges_are_trimmed_but_inner_text_is_untouched():
    out, stats = normalize("  two  spaces nbsp ")
    assert out == "two  spaces nbsp"
    assert stats["trim_changed"] and not stats["nfc_changed"] and not stats["strip_changed"]


def test_clean_text_is_not_changed():
    text = "พิมพ์ไทย จ่ายแพงกว่ากี่เท่า?"
    out, stats = normalize(text)
    assert out == text
    assert not stats["changed"]


def test_normalize_all_logs_which_sentences_changed():
    out, log = normalize_all(["clean", "zero​width", "trailing "])
    assert out == ["clean", "zerowidth", "trailing"]
    assert log["changed_total"] == 2
    assert log["sent_ids_changed_by_control_or_format_strip"] == [2]
    assert log["sent_ids_changed_by_trim"] == [3]
    assert log["removed_or_replaced_characters"] == {"U+200B ZERO WIDTH SPACE": 1}


def test_split_lines_only_splits_on_line_feed():
    # U+2028 and form feed are line breaks for str.splitlines(); splitting there would
    # shift every later sentence against its translation.
    blob = "one still one\ntwo\x0cstill two\n".encode()
    assert split_lines(blob) == ["one still one", "two\x0cstill two"]


def test_split_lines_stops_on_invalid_utf8():
    with pytest.raises(UnicodeDecodeError):
        split_lines(b"ok\n\xff\n")


def test_alignment_accepts_equal_lengths():
    check_alignment({"eng_Latn": ["a", "b"], "tha_Thai": ["ก", "ข"]}, expected_rows=2)


@pytest.mark.parametrize(
    "sentences",
    [
        {"eng_Latn": ["a", "b"], "tha_Thai": ["ก"]},  # a language is missing a sentence
        {"eng_Latn": ["a", ""], "tha_Thai": ["ก", "ข"]},  # empty sentence
        {"eng_Latn": ["a", "b\tc"], "tha_Thai": ["ก", "ข"]},  # TAB would corrupt the TSV
    ],
)
def test_alignment_stops_on_bad_data(sentences):
    with pytest.raises(Stop):
        check_alignment(sentences, expected_rows=2)


def test_languages_registry(repo):
    baseline, targets = load_languages(repo / "registry" / "languages.toml")
    assert baseline == "eng_Latn"
    assert "tha_Thai" in targets
    assert baseline not in targets


def test_languages_registry_rejects_baseline_as_target(tmp_path):
    path = tmp_path / "languages.toml"
    path.write_text('[baseline]\ncode = "eng_Latn"\n[[target]]\ncode = "eng_Latn"\n', encoding="utf-8")
    with pytest.raises(Stop):
        load_languages(path)
