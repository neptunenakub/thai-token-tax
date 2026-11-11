"""Registry loading and the count stage, with a fake counter. No network."""
import csv
import json

import pytest

from thai_token_tax import Stop, counters, sha256_file
from thai_token_tax.counters.base import Blocked


def test_models_registry_is_valid(repo):
    models, openai_lookup = counters.load_models(repo / "registry" / "models.toml")
    ids = [m["id"] for m in models]
    assert len(ids) == len(set(ids))
    assert "tiktoken/o200k_base" in ids
    by_id = {m["id"]: m for m in models}
    for m in models:
        assert m["counter"] in counters.SOURCE_OF
        assert m["family"]
        if m["counter"] == "tiktoken":
            assert m["encoding"]
        if "revision" in m:
            assert len(m["revision"]) == 40  # a full commit hash, not a branch name
        if "sample_of" in m:  # a sample is compared with a FULLY measured model of the same source
            reference = by_id[m["sample_of"]]
            assert "sample_of" not in reference
            assert reference["counter"] == m["counter"]
    assert openai_lookup["model_ids"]


def test_registry_rejects_duplicates_unknown_counters_and_dangling_samples(tmp_path):
    path = tmp_path / "models.toml"
    block = '[[model]]\nid = "a"\nfamily = "F"\ncounter = "hf"\n'
    for bad in (block + block, block.replace('"hf"', '"guess"'), block + 'sample_of = "missing"\n'):
        path.write_text(bad, encoding="utf-8")
        with pytest.raises(Stop):
            counters.load_models(path)


class WordCounter:
    """A stand-in tokenizer: one token per whitespace-separated word."""

    def __init__(self, model_id):
        self.model_id = model_id

    def count(self, texts):
        return [len(t.split()) for t in texts]

    def describe(self):
        return {"model_id": self.model_id, "tokenizer": "words", "library": "fake==0"}


def fake_build(entry, cache_dir):
    if entry["id"].startswith("gated/"):
        raise Blocked("gated repo: needs HF_TOKEN from an account that accepted the model terms")
    return WordCounter(entry["id"])


MODELS = (
    '[[model]]\nid = "open/model"\nfamily = "Open"\ncounter = "hf"\n'
    '[[model]]\nid = "gated/model"\nfamily = "Gated"\ncounter = "hf"\n'
    '[[model]]\nid = "api-full"\nfamily = "Api"\ncounter = "gemini"\n'
    '[[model]]\nid = "api-sample"\nfamily = "Api"\ncounter = "gemini"\nsample_of = "api-full"\n'
    '[[model]]\nid = "gated/api"\nfamily = "Api"\ncounter = "anthropic"\n'
)


@pytest.fixture
def toy_repo(tmp_path, monkeypatch):
    (tmp_path / "registry").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "registry" / "models.toml").write_text(MODELS, encoding="utf-8")
    tsv = tmp_path / "data" / "flores200_devtest.tsv"
    tsv.write_text(
        "sent_id\teng_Latn\ttha_Thai\n1\tone two\tหนึ่ง สอง สาม\n2\tthree\tสี่\n3\tfour five six\tห้า หก\n",
        encoding="utf-8", newline="\n",
    )
    (tmp_path / "data" / "source.json").write_text(
        json.dumps({"normalized_tsv": {"sha256": sha256_file(tsv)}}), encoding="utf-8"
    )
    monkeypatch.setattr(counters, "SAMPLE_SIZE", 2)
    return tmp_path


def read(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_count_stage_writes_one_result_set_per_source(toy_repo):
    out = toy_repo / "out"
    written = counters.run(toy_repo, out, build=fake_build)
    assert [p.name.split("_")[-1] for p in written] == ["open.csv", "gemini.csv"]

    rows = read(written[0])
    assert list(rows[0]) == counters.COLUMNS
    assert [(r["lang"], r["sent_id"], r["n_chars"], r["n_tokens"]) for r in rows] == [
        ("eng_Latn", "1", "7", "2"), ("eng_Latn", "2", "5", "1"), ("eng_Latn", "3", "13", "3"),
        ("tha_Thai", "1", "13", "3"), ("tha_Thai", "2", "3", "1"), ("tha_Thai", "3", "6", "2"),
    ]
    assert {r["model_id"] for r in rows} == {"open/model"}  # the gated model has no rows at all

    meta = json.loads(written[0].with_suffix(".meta.json").read_text(encoding="utf-8"))
    assert [m["model_id"] for m in meta["measured"]] == ["open/model"]
    assert [(b["model_id"], b["reason"][:10]) for b in meta["blocked"]] == [("gated/model", "gated repo")]

    with pytest.raises(Stop):  # a second run on the same day must not overwrite the first
        counters.run(toy_repo, out, build=fake_build)


def test_sampled_model_is_counted_on_the_sample_only(toy_repo):
    (gemini,) = counters.run(toy_repo, toy_repo / "out", sources=["gemini"], build=fake_build)
    rows = read(gemini)
    full = {r["sent_id"] for r in rows if r["model_id"] == "api-full"}
    sample = {r["sent_id"] for r in rows if r["model_id"] == "api-sample"}
    assert full == {"1", "2", "3"}
    assert len(sample) == 2 and sample < full

    meta = json.loads(gemini.with_suffix(".meta.json").read_text(encoding="utf-8"))
    coverage = {m["model_id"]: (m["coverage"], m["sentences_counted"]) for m in meta["measured"]}
    assert coverage == {"api-full": ("full", 3), "api-sample": ("sample", 2)}
    assert sorted(int(s) for s in sample) == meta["sample"]["sent_ids"]


def test_a_fully_blocked_source_leaves_a_record_but_no_result_set(toy_repo):
    out = toy_repo / "out"
    assert counters.run(toy_repo, out, sources=["anthropic"], build=fake_build) == []
    assert not list(out.glob("*.csv")) and not list(out.glob("*.meta.json"))
    (record,) = out.glob("counts_*_anthropic.blocked.json")
    blocked = json.loads(record.read_text(encoding="utf-8"))["blocked"]
    assert [b["model_id"] for b in blocked] == ["gated/api"]
    # Once the source works, it can still be measured on the same day and the record goes away.
    counters.run(toy_repo, out, sources=["anthropic"], build=lambda entry, cache: WordCounter(entry["id"]))
    assert not record.exists() and len(list(out.glob("counts_*_anthropic.csv"))) == 1


def test_count_stage_refuses_sentences_that_changed_after_prepare(toy_repo):
    tsv = toy_repo / "data" / "flores200_devtest.tsv"
    tsv.write_text(tsv.read_text(encoding="utf-8") + "4\tedited\tแก้\n", encoding="utf-8", newline="\n")
    with pytest.raises(Stop):
        counters.run(toy_repo, toy_repo / "out", build=fake_build)


def test_an_add_on_set_for_chosen_models_never_overwrites_the_main_set(toy_repo):
    out = toy_repo / "out"
    counters.run(toy_repo, out, sources=["open"], build=fake_build)
    with pytest.raises(Stop, match="--label"):  # a partial run must be named
        counters.run(toy_repo, out, sources=["open"], build=fake_build, only=["open/model"])
    (extra,) = counters.run(
        toy_repo, out, sources=["open"], build=fake_build, only=["open/model"], label="extra"
    )
    assert extra.name.endswith("_open-extra.csv")
    assert {r["model_id"] for r in read(extra)} == {"open/model"}
    assert len(list(out.glob("counts_*_open*.csv"))) == 2
