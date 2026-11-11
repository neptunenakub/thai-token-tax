"""Billing check: comparison logic, the cost cap and exactly-once sending. No network."""
import csv
import json

import pytest

from thai_token_tax import Stop, billing, sha256_file

PRICE = {"input_usd_per_mtok": 2.0, "output_usd_per_mtok": 10.0}


def test_classify_the_three_possible_outcomes():
    assert billing.classify([0, 0, 0]) == "equal for every text"
    assert billing.classify([3, 3, 3]) == "differ by a constant (+3 tokens on every text)"
    assert billing.classify([0, 2, -1]) == "differ irregularly (differences from -1 to +2)"


def test_billed_input_includes_cache_fields():
    assert billing.billed_input({"input_tokens": 40}) == 40
    assert billing.billed_input({"input_tokens": 40, "cache_creation_input_tokens": None}) == 40
    usage = {"input_tokens": 10, "cache_creation_input_tokens": 25, "cache_read_input_tokens": 5}
    assert billing.billed_input(usage) == 40


def test_cost_and_estimate():
    assert billing.cost_usd(1_000_000, 100_000, PRICE) == pytest.approx(2.0 + 1.0)
    plan = [{"model_id": "m", "expected_input_tokens": 500_000}] * 2
    expected = 2 * (500_000 * 2.0 + billing.MAX_TOKENS * 10.0) / 1_000_000
    assert billing.estimate(plan, {"models": {"m": PRICE}}) == pytest.approx(expected)


def test_sample_is_fixed_and_nested():
    ids = list(range(1, 101))
    assert billing.sample_pairs(ids, 20) == billing.sample_pairs(ids, 20)
    assert billing.sample_pairs(ids, 5) == billing.sample_pairs(ids, 20)[:5]


def row(model, sent_id, counted, billed, content, overhead=8, lang="tha_Thai"):
    return {"model_id": model, "lang": lang, "sent_id": sent_id, "count_tokens": counted,
            "content_tokens_published": content, "overhead_published": overhead,
            "usage": {"input_tokens": billed, "output_tokens": 1}}


def test_summarize_reports_what_billing_shows():
    prices = {"models": {"same": PRICE, "plus-two": PRICE}}
    rows = [row("same", 1, 48, 48, 40), row("same", 2, 28, 28, 20),
            row("plus-two", 1, 48, 50, 40), row("plus-two", 2, 28, 30, 20),
            {"model_id": "same", "lang": "tha_Thai", "sent_id": 3, "count_tokens": 9, "usage": None}]
    result = billing.summarize(rows, prices)
    same, plus = result["same"], result["plus-two"]
    assert same["billed_input_vs_count_tokens"] == "equal for every text"
    assert same["billed_input_minus_published_content"] == [8]  # the overhead we subtract
    assert same["texts_compared"] == 2 and same["texts_failed"] == 1
    assert same["actual_cost_usd"] == pytest.approx((76 * 2.0 + 2 * 10.0) / 1_000_000)
    assert plus["billed_input_vs_count_tokens"] == "differ by a constant (+2 tokens on every text)"
    assert plus["billed_input_minus_published_content"] == [10]  # billing shows a different overhead
    differently = billing.same_billing(rows, "same", "plus-two")
    assert differently == {"texts_in_common": 2, "texts_billed_differently": 2}


class FakeClient:
    """Counts like the real endpoints would; remembers how many billable requests it got."""

    def __init__(self):
        self.billable = 0
        self.messages = self

    def count_tokens(self, *, model, messages):
        return type("Count", (), {"input_tokens": len(messages[0]["content"].split()) + 8})()

    def create(self, *, model, max_tokens, messages):
        self.billable += 1
        usage = {"input_tokens": len(messages[0]["content"].split()) + 8, "output_tokens": max_tokens}
        return type("Answer", (), {"usage": type("U", (), {"to_dict": lambda self: usage})(),
                                   "stop_reason": "max_tokens"})()


@pytest.fixture
def toy(tmp_path, monkeypatch):
    monkeypatch.setattr(billing, "PLAN", [("model-a", 2, "model-a"), ("model-b", 1, "model-a")])
    monkeypatch.setattr(billing, "SECONDS_BETWEEN_REQUESTS", 0)
    results = tmp_path / "results"
    (tmp_path / "data").mkdir()
    results.mkdir()
    tsv = tmp_path / "data" / "flores200_devtest.tsv"
    sentences = [(1, "one two", "หนึ่ง สอง สาม"), (2, "three", "สี่"), (3, "four five six", "ห้า หก")]
    tsv.write_text("sent_id\teng_Latn\ttha_Thai\n" + "".join(f"{i}\t{e}\t{t}\n" for i, e, t in sentences),
                   encoding="utf-8", newline="\n")
    (tmp_path / "data" / "source.json").write_text(
        json.dumps({"normalized_tsv": {"sha256": sha256_file(tsv)}}), encoding="utf-8")
    with (results / "counts.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["model_id", "lang", "sent_id", "n_tokens"])
        for i, english, thai in sentences:
            writer.writerow(["model-a", "eng_Latn", i, len(english.split())])
            writer.writerow(["model-a", "tha_Thai", i, len(thai.split())])
    (results / "counts.meta.json").write_text(json.dumps({"measured": [
        {"model_id": "model-a", "overhead_tokens_subtracted": 8},
        {"model_id": "model-b", "overhead_tokens_subtracted": 8}]}), encoding="utf-8")
    (results / "prices.json").write_text(json.dumps({"models": {"model-a": PRICE, "model-b": PRICE}}),
                                         encoding="utf-8")
    (results / "latest.json").write_text(
        json.dumps({"counts": {"anthropic": "counts.csv"}, "prices": "prices.json"}), encoding="utf-8")
    return tmp_path, results


def test_dry_run_sends_nothing_billable(toy):
    root, results = toy
    client = FakeClient()
    assert billing.run(root, results, dry_run=True, client=client) is None
    assert client.billable == 0 and not list(results.glob("billing_check_*"))


def test_run_aborts_above_the_cap_before_sending(toy):
    root, results = toy
    client = FakeClient()
    with pytest.raises(Stop, match="above the cap"):
        billing.run(root, results, cap_usd=0.0000001, client=client)
    assert client.billable == 0


def test_each_billable_request_is_sent_exactly_once(toy):
    root, results = toy
    client = FakeClient()
    out = billing.run(root, results, client=client)
    assert client.billable == 6  # (2 pairs + 1 pair) x 2 languages
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["models"]["model-a"]["billed_input_vs_count_tokens"] == "equal for every text"
    assert report["models"]["model-a"]["billed_input_minus_published_content"] == [8]
    assert report["claude-opus-5-5_vs_claude-haiku-5-5"]["texts_in_common"] == 0  # other models in this toy
    assert report["cost"]["actual_usd"] == pytest.approx(report["cost"]["expected_usd"])
    assert "text" not in report["rows"][0]  # no sentence text in the result file
    assert json.loads((results / "latest.json").read_text(encoding="utf-8"))["billing_check"] == out.name

    out.unlink()  # a rerun (e.g. after a crash) must reuse the saved answers, not bill again
    (results / out.name.replace(".json", ".md")).unlink()
    billing.run(root, results, client=client)
    assert client.billable == 6
