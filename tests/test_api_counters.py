"""API counters: overhead subtraction, checkpoint/resume, retries, blocking. No network."""
import pytest

from thai_token_tax import Stop, verify
from thai_token_tax.counters.anthropic_counter import AnthropicCounter
from thai_token_tax.counters.base import ApiCounter, ApiError, Blocked

OVERHEAD = 7  # framing tokens the fake endpoint adds to a one-message request
PER_TURN = 3  # framing tokens it adds for every further turn
IDS = [1, 2, 3]


class FakeEndpoint(ApiCounter):
    """One token per word, plus fixed framing, like a real counting endpoint."""

    env_key = "FAKE_API_KEY"
    endpoint = "fake endpoint"
    library = "fake"

    def __init__(self, model_id, cache_dir, failures=()):
        self.requests = []
        self.failures = list(failures)  # errors to raise before answering
        super().__init__(model_id, cache_dir)

    def call(self, turns):
        if self.failures:
            raise self.failures.pop(0)
        self.requests.append(turns)
        return sum(len(t.split()) for t in turns) + OVERHEAD + PER_TURN * (len(turns) - 1)


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("FAKE_API_KEY", "not-a-real-key")
    monkeypatch.setattr("time.sleep", lambda seconds: None)  # no real waiting between retries


def test_overhead_is_measured_and_subtracted(tmp_path):
    counter = FakeEndpoint("m", tmp_path)
    assert counter.overhead == OVERHEAD
    assert counter.count(["one two three", "พิมพ์ ไทย"]) == [3, 2]  # content tokens only
    described = counter.describe()
    assert described["overhead_tokens_subtracted"] == OVERHEAD
    assert described["api_calls_this_run"] == 3  # the probe + two texts


def test_a_run_resumes_from_the_checkpoint_without_new_calls(tmp_path):
    first = FakeEndpoint("m", tmp_path)
    first.count(["one two", "three"])
    resumed = FakeEndpoint("m", tmp_path)
    assert resumed.count(["one two", "three", "four five six"]) == [2, 1, 3]
    assert resumed.requests == [["four five six"]]  # only the text that was not counted yet
    assert resumed.describe()["answers_resumed_from_checkpoint"] == 3


def test_a_checkpoint_line_cut_off_by_an_interrupted_run_is_ignored(tmp_path):
    first = FakeEndpoint("m", tmp_path)
    first.count(["one two"])
    with first.checkpoint.open("a", encoding="utf-8") as f:
        f.write('{"key": "abc", "ra')  # the process died in the middle of a write
    assert FakeEndpoint("m", tmp_path).count(["one two"]) == [2]


def test_calls_are_spaced_to_stay_under_a_requests_per_minute_limit(tmp_path, monkeypatch):
    waits = []
    monkeypatch.setattr("time.sleep", waits.append)
    monkeypatch.setattr("time.monotonic", lambda: 100.0)  # a frozen clock
    counter = FakeEndpoint("m", tmp_path)
    counter.requests_per_minute = 60
    for text in ("one", "two", "three"):
        counter.raw_count([text])
    assert waits[-3:] == [0.0, 1.0, 2.0]  # each call is booked one second after the previous one


def test_rate_limits_and_server_errors_are_retried(tmp_path):
    counter = FakeEndpoint("m", tmp_path, failures=[ApiError(429, "slow down", 0.0), ApiError(503, "busy")])
    assert counter.overhead == OVERHEAD


def test_missing_key_blocks_the_model(tmp_path, monkeypatch):
    monkeypatch.delenv("FAKE_API_KEY")
    with pytest.raises(Blocked, match="FAKE_API_KEY is not set"):
        FakeEndpoint("m", tmp_path)


def test_a_refused_request_blocks_with_the_real_error_and_never_shows_a_key(tmp_path):
    error = ApiError(400, "Your credit balance is too low. key sk-ant-api03-abcDEF123")
    with pytest.raises(Blocked) as blocked:
        FakeEndpoint("m", tmp_path, failures=[error])
    record = blocked.value.record()
    assert record["http_status"] == 400
    assert record["error_first_line"] == "Your credit balance is too low. key [redacted]"


def test_endpoint_that_keeps_failing_blocks_instead_of_guessing(tmp_path):
    with pytest.raises(Blocked, match="kept failing"):
        FakeEndpoint("m", tmp_path, failures=[ApiError(500, "down")] * ApiCounter.TRIES)


def test_a_text_with_no_tokens_after_subtraction_stops_the_run(tmp_path):
    counter = FakeEndpoint("m", tmp_path)
    with pytest.raises(Stop):
        counter.count([""])


class FakeAnthropicClient:
    """Stands in for anthropic.Anthropic(): records the request, answers like the SDK."""

    def __init__(self):
        self.calls = []
        self.messages = self

    def count_tokens(self, *, model, messages):
        self.calls.append((model, messages))
        return type("Answer", (), {"input_tokens": sum(len(m["content"].split()) for m in messages) + 8})()


def test_anthropic_counter_sends_alternating_roles_and_subtracts_overhead(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    client = FakeAnthropicClient()
    counter = AnthropicCounter("claude-test", tmp_path, client=client)
    assert counter.overhead == 8
    assert counter.count(["hello there"]) == [2]
    counter.raw_count(["x", "y", "z"])
    model, messages = client.calls[-1]
    assert model == "claude-test"
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]


def test_verify_accepts_a_constant_overhead(tmp_path):
    counter = FakeEndpoint("m", tmp_path)
    texts = {"eng_Latn": ["one two", "three", "four five six"], "tha_Thai": ["หนึ่ง สอง", "สาม", "สี่ ห้า"]}
    expected = {lang: dict(zip(IDS, counter.count(lines), strict=True)) for lang, lines in texts.items()}
    result = verify.check_api(counter, IDS, texts, expected)
    assert result["length_check_constant"] and result["content_check_constant"]
    assert result["repeat_check_mismatch"] == 0
    assert result["content_check_distinct_differences"] == [2 * PER_TURN - 2 * OVERHEAD]
    assert result["tiktoken_check"] == "tiktoken does not know this model"


def test_verify_catches_an_overhead_that_grows_with_length(tmp_path):
    class Drifting(FakeEndpoint):
        def call(self, turns):
            return super().call(turns) + sum(len(t.split()) for t in turns) // 50

    counter = Drifting("m", tmp_path)
    texts = {"eng_Latn": ["one two", "three", "four"], "tha_Thai": ["หนึ่ง", "สอง", "สาม"]}
    expected = {lang: dict(zip(IDS, counter.count(lines), strict=True)) for lang, lines in texts.items()}
    assert not verify.check_api(counter, IDS, texts, expected)["length_check_constant"]
