"""FLORES+ reading, the FLORES-200 vs FLORES+ comparison, and the latest.json fix. No network."""
import csv
import json

import pytest

from thai_token_tax import Stop, analyze, compare, counters, data, sha256_file

COLUMNS = ["run_date_utc", "dataset", "split", "sent_id", "lang", "family",
           "model_id", "tokenizer", "library", "n_chars", "n_tokens"]


def write_counts(path, model, thai_tokens, dataset="flores200", english=(10, 10, 12, 8)):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(COLUMNS)
        for lang, tokens in (("eng_Latn", english), ("tha_Thai", thai_tokens)):
            for sent_id, n in enumerate(tokens, start=1):
                writer.writerow(["2026-01-01", dataset, "devtest", sent_id, lang, "Fam", model, "tok", "lib",
                                 40, n])


def loaded(path):
    return analyze.load_counts([path])


def test_read_jsonl_pairs_text_with_integer_ids():
    blob = b'{"id": 1, "text": "two"}\n{"id": 0, "text": "one"}\n'
    assert data.read_jsonl(blob) == {1: "two", 0: "one"}
    with pytest.raises(Stop):
        data.read_jsonl(b'{"id": 0, "text": "a"}\n{"id": 0, "text": "b"}\n')


def test_identical_counts_are_reported_as_identical_and_inside_the_ci(tmp_path):
    thai = (25, 24, 30, 20)
    write_counts(tmp_path / "counts_2026-01-01_open.csv", "m", thai)
    plus = tmp_path / "plus"
    plus.mkdir()
    write_counts(plus / "counts_2026-01-01_open.csv", "m", thai, dataset="floresplus")
    (row,) = compare.compare(loaded(tmp_path / "counts_2026-01-01_open.csv"),
                             loaded(plus / "counts_2026-01-01_open.csv"), "eng_Latn", "tha_Thai")
    assert row["identical_counts"]
    assert row["premium_flores200"] == row["premium_floresplus"] == pytest.approx(99 / 40)
    assert row["tokens_per_1k_thai_chars_flores200"] == pytest.approx(1000 * 99 / 160)
    assert row["premium_floresplus_inside_flores200_ci"]
    assert row["tokens_per_1k_thai_chars_floresplus_inside_flores200_ci"]


def test_a_different_count_is_flagged_and_can_fall_outside_the_ci(tmp_path):
    write_counts(tmp_path / "counts_2026-01-01_open.csv", "m", (25, 24, 30, 20))
    plus = tmp_path / "plus"
    plus.mkdir()
    write_counts(plus / "counts_2026-01-01_open.csv", "m", (50, 48, 60, 40), dataset="floresplus")
    (row,) = compare.compare(loaded(tmp_path / "counts_2026-01-01_open.csv"),
                             loaded(plus / "counts_2026-01-01_open.csv"), "eng_Latn", "tha_Thai")
    assert not row["identical_counts"]
    assert not row["premium_floresplus_inside_flores200_ci"]


def test_models_missing_on_one_side_are_not_compared(tmp_path):
    write_counts(tmp_path / "counts_2026-01-01_open.csv", "only-core", (25, 24, 30, 20))
    plus = tmp_path / "plus"
    plus.mkdir()
    write_counts(plus / "counts_2026-01-01_open.csv", "only-plus", (25, 24, 30, 20), dataset="floresplus")
    assert compare.compare(loaded(tmp_path / "counts_2026-01-01_open.csv"),
                           loaded(plus / "counts_2026-01-01_open.csv"), "eng_Latn", "tha_Thai") == []


def test_analyze_keeps_the_price_and_cost_entries_of_latest_json(tmp_path):
    counts = tmp_path / "counts_2026-01-01_open.csv"
    write_counts(counts, "m", (25, 24, 30, 20))
    (tmp_path / "latest.json").write_text(
        json.dumps({"prices": "prices.json", "costs_csv": "costs.csv", "billing_check": "bill.json",
                    "summary_csv": "old.csv"}),
        encoding="utf-8",
    )
    analyze.run([counts], "eng_Latn", ["tha_Thai"], tmp_path)
    latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert latest["prices"] == "prices.json" and latest["costs_csv"] == "costs.csv"
    assert latest["billing_check"] == "bill.json"
    assert latest["summary_csv"] == "summary_2026-01-01.csv"  # the summary pointer itself is renewed


class WordCounter:
    def __init__(self, model_id):
        self.model_id = model_id

    def count(self, texts):
        return [len(t.split()) for t in texts]

    def describe(self):
        return {"model_id": self.model_id, "tokenizer": "words", "library": "fake==0"}


def test_count_stage_can_read_the_second_dataset(tmp_path):
    (tmp_path / "registry").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "registry" / "models.toml").write_text(
        '[[model]]\nid = "open/model"\nfamily = "Open"\ncounter = "hf"\n', encoding="utf-8")
    tsv = tmp_path / "data" / data.TSV_FILE["floresplus"]
    tsv.write_text("sent_id\teng_Latn\ttha_Thai\n1\tone two\tหนึ่ง สอง\n", encoding="utf-8", newline="\n")
    (tmp_path / "data" / data.SOURCE_FILE["floresplus"]).write_text(
        json.dumps({"normalized_tsv": {"sha256": sha256_file(tsv)}}), encoding="utf-8")
    (path,) = counters.run(tmp_path, tmp_path / "out", dataset="floresplus",
                           build=lambda entry, cache: WordCounter(entry["id"]))
    with path.open(encoding="utf-8", newline="") as f:
        assert {r["dataset"] for r in csv.DictReader(f)} == {"floresplus"}
    meta = json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8"))
    assert meta["dataset"]["name"] == "floresplus"
    with pytest.raises(Stop):  # the FLORES-200 files do not exist in this toy repo
        counters.run(tmp_path, tmp_path / "out2", build=lambda entry, cache: WordCounter(entry["id"]))
