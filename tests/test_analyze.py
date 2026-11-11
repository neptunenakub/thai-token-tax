"""Premium math and the bootstrap. No network."""
import csv
import json

import numpy as np
import pytest

from thai_token_tax import Stop, analyze

DAY1_COUNTS = "results/open_counts_2026-11-10.csv"
DAY1_SUMMARY = "results/open_summary_2026-11-10.csv"
COLUMNS = ["run_date_utc", "dataset", "split", "sent_id", "lang", "family",
           "model_id", "tokenizer", "library", "n_chars", "n_tokens"]


def test_premium_is_a_ratio_of_sums_not_a_mean_of_ratios():
    target = np.array([10, 1])
    baseline = np.array([1, 10])
    assert analyze.premium(target, baseline) == 1.0  # the mean of the two ratios would be 5.05


def test_tokens_per_1k_chars():
    assert analyze.tokens_per_1k_chars(tokens=250, chars=1000) == 250.0
    assert analyze.tokens_per_1k_chars(tokens=1, chars=4) == 250.0


def test_resample_weights_keep_the_sample_size():
    weights = analyze.resample_weights(n_sentences=50, n_boot=200, seed=1)
    assert weights.shape == (200, 50)
    assert (weights.sum(axis=1) == 50).all()


def test_bootstrap_is_deterministic_for_a_seed():
    rng = np.random.default_rng(0)
    baseline = rng.integers(10, 40, size=300)
    target = baseline * 2 + rng.integers(0, 10, size=300)
    first = analyze.bootstrap_ci(target, baseline, analyze.resample_weights(300, 2000, seed=7))
    again = analyze.bootstrap_ci(target, baseline, analyze.resample_weights(300, 2000, seed=7))
    other = analyze.bootstrap_ci(target, baseline, analyze.resample_weights(300, 2000, seed=8))
    assert first == again
    assert first != other
    low, high = first
    assert low < analyze.premium(target, baseline) < high


def test_bootstrap_has_zero_width_when_every_sentence_has_the_same_ratio():
    baseline = np.array([5, 10, 20, 40])
    low, high = analyze.bootstrap_ci(baseline * 3, baseline, analyze.resample_weights(4, 500, seed=3))
    assert low == high == 3.0


def write_counts(path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(COLUMNS)
        for model, lang, sent_id, chars, tokens in rows:
            writer.writerow(
                ["2026-01-01", "toy", "devtest", sent_id, lang, "Fam", model, "tok", "lib", chars, tokens]
            )


def model_rows(model, sent_ids=(1, 2), thai=(25, 35)):
    english = {1: (40, 10), 2: (60, 10)}
    thai_rows = {1: (30, thai[0]), 2: (70, thai[1])}
    return [(model, "eng_Latn", s, *english[s]) for s in sent_ids] + [
        (model, "tha_Thai", s, *thai_rows[s]) for s in sent_ids
    ]


def summary(tmp_path, name="summary_2026-01-01.csv"):
    with (tmp_path / name).open(encoding="utf-8", newline="") as f:
        return {r["model_id"]: r for r in csv.DictReader(f)}


def test_run_writes_summary_and_latest(tmp_path):
    counts = tmp_path / "counts_2026-01-01_open.csv"
    write_counts(counts, model_rows("m1") + model_rows("m2"))  # m2 has identical counts
    analyze.run([counts], "eng_Latn", ["tha_Thai"], tmp_path)

    rows = summary(tmp_path)
    m1, m2 = rows["m1"], rows["m2"]
    assert (m1["baseline_tokens"], m1["target_tokens"]) == ("20", "60")
    assert m1["premium"] == "3.000000"
    assert m1["target_tokens_per_1k_chars"] == "600.000000"  # 60 tokens / 100 chars
    assert m1["baseline_tokens_per_1k_chars"] == "200.000000"  # 20 tokens / 100 chars
    assert m1["same_counts_as"] == "" and m2["same_counts_as"] == "m1"
    assert (tmp_path / "latest.json").exists()

    with pytest.raises(Stop):  # result files are never overwritten
        analyze.run([counts], "eng_Latn", ["tha_Thai"], tmp_path)
    analyze.run([counts], "eng_Latn", ["tha_Thai"], tmp_path, label="again")  # unless given a new name
    assert (tmp_path / "summary_2026-01-01_again.csv").exists()


def test_sources_are_merged_and_samples_point_at_a_full_model(tmp_path):
    open_csv = tmp_path / "counts_2026-01-01_open.csv"
    api_csv = tmp_path / "counts_2026-01-01_openai.csv"
    write_counts(open_csv, model_rows("local"))
    write_counts(
        api_csv,
        model_rows("api-full")  # same counts as the local tokenizer, measured through an API
        + model_rows("api-sample", sent_ids=(2,))  # agrees with it on the sampled sentence
        + model_rows("api-other", sent_ids=(2,), thai=(25, 99)),  # a different tokenizer
    )
    assert [p.name for p in analyze.find_counts(tmp_path, None)] == [open_csv.name, api_csv.name]
    analyze.run(analyze.find_counts(tmp_path, None), "eng_Latn", ["tha_Thai"], tmp_path)

    rows = summary(tmp_path)
    assert [(r["source"], r["coverage"]) for r in rows.values()] == [
        ("open", "full"), ("openai", "full"), ("openai", "sample"), ("openai", "sample"),
    ]
    assert rows["api-full"]["same_counts_as"] == "local"  # found across sources
    assert rows["api-sample"]["same_counts_as"] == "local"
    assert rows["api-sample"]["premium"] == ""  # a sample never gets numbers of its own
    assert rows["api-other"]["same_counts_as"] == ""  # no match: it needs a full run

    latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert latest["counts"] == {"open": open_csv.name, "openai": api_csv.name}


def test_sources_counted_on_different_sentence_files_are_not_merged(tmp_path):
    paths = []
    for source, sha in (("open", "aaa"), ("openai", "bbb")):
        path = tmp_path / f"counts_2026-01-01_{source}.csv"
        write_counts(path, model_rows(f"model-{source}"))
        path.with_suffix(".meta.json").write_text(json.dumps({"dataset": {"sha256": sha}}), encoding="utf-8")
        paths.append(path)
    with pytest.raises(Stop, match="different sentence files"):
        analyze.run(paths, "eng_Latn", ["tha_Thai"], tmp_path)


def test_a_missing_sentence_stops_the_analysis(tmp_path):
    counts = tmp_path / "counts_2026-01-01_open.csv"
    write_counts(counts, model_rows("m1")[:-1])  # the Thai row of sentence 2 is missing
    with pytest.raises(Stop):
        analyze.run([counts], "eng_Latn", ["tha_Thai"], tmp_path)


def test_day1_summary_is_reproduced_from_the_raw_counts(repo):
    """Golden test: the committed day-1 raw counts must still give the day-1 summary,
    digit for digit (premium and both CI bounds at 6 decimals, and the token totals)."""
    _, order, data = analyze.load_counts([repo / DAY1_COUNTS])
    rows = {r["model_id"]: r for r in analyze.summarize(order, data, "eng_Latn", ["tha_Thai"])}
    with (repo / DAY1_SUMMARY).open(encoding="utf-8", newline="") as f:
        expected = list(csv.DictReader(f))
    assert len(expected) == len(rows) == 23
    for old in expected:
        new = rows[old["model_id"]]
        assert f"{new['premium']:.6f}" == old["premium"]
        assert f"{new['ci95_low']:.6f}" == old["ci95_low"]
        assert f"{new['ci95_high']:.6f}" == old["ci95_high"]
        assert str(new["baseline_tokens"]) == old["en_tokens"]
        assert str(new["target_tokens"]) == old["th_tokens"]
        assert new["same_counts_as"] == old["same_counts_as"]


def test_add_on_sets_are_merged_in_source_order(tmp_path):
    names = ["open", "open-extra", "openai"]
    for name in names:
        write_counts(tmp_path / f"counts_2026-01-01_{name}.csv", model_rows(f"model-{name}"))
    found = analyze.find_counts(tmp_path, None)
    assert [p.name.split("_")[-1] for p in found] == [f"{n}.csv" for n in names]
    analyze.run(found, "eng_Latn", ["tha_Thai"], tmp_path)
    assert [r["source"] for r in summary(tmp_path).values()] == names
