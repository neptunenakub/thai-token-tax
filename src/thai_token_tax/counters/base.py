"""The interface every way of counting tokens implements, and the shared part of API counters."""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from .. import Stop, utc_now

SECRET = re.compile(r"(sk-|AIza|hf_)[\w*.\-]+")  # never let a key (even a masked one) reach a log


class Blocked(Exception):
    """This tokenizer cannot be measured right now (gated repo, missing key, no credit, ...).

    The run records the real reason and moves on. A blocked tokenizer is never
    replaced by a guess, an estimate or an unofficial copy.
    """

    def __init__(self, reason: str, cause: Exception | None = None):
        super().__init__(reason)
        self.reason = reason
        self.cause = cause

    def record(self) -> dict:
        response = getattr(self.cause, "response", None)
        status = getattr(self.cause, "status", None) or getattr(response, "status_code", None)
        text = SECRET.sub("[redacted]", str(self.cause).strip()) if self.cause else ""
        return {
            "reason": self.reason,
            "error_type": type(self.cause).__name__ if self.cause else None,
            "http_status": status,
            "error_first_line": text.splitlines()[0][:300] if text else "",
        }


class Counter(Protocol):
    """Counts CONTENT tokens only: no BOS/EOS, no chat template, no API overhead."""

    def count(self, texts: list[str]) -> list[int]:
        """Number of content tokens of each text, in the same order."""
        ...

    def describe(self) -> dict:
        """What was measured: model id, tokenizer/encoding, library version, file hashes."""
        ...


class ApiError(Exception):
    """One failed call to a token-counting endpoint."""

    def __init__(self, status: int | None, message: str, retry_after: float | None = None):
        super().__init__(SECRET.sub("[redacted]", message))
        self.status = status
        self.retry_after = retry_after


class ApiCounter:
    """A counter that asks the provider's official token-counting endpoint.

    The endpoint counts a whole request, so every answer includes a fixed number of
    framing tokens (role markers and the like). This class:
      - measures that overhead on a one-token message and subtracts it,
      - saves every answer to a checkpoint file, so an interrupted run resumes
        without repeating calls,
      - retries rate limits and server errors with backoff, a few calls at a time,
        and can be held under a requests-per-minute limit (registry: [rate_limits]).
    A subclass only implements call(): one request for one conversation.
    `ttt verify` checks that the overhead really is constant.
    """

    env_key = ""  # name of the environment variable holding the API key
    endpoint = ""  # shown in results as the tokenizer
    library = ""
    OVERHEAD_PROBE = "a"  # one token in every tokenizer; verify re-checks this
    WORKERS = 4
    TRIES = 6
    RETRY_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}

    def __init__(self, model_id: str, cache_dir: Path, requests_per_minute: float | None = None):
        self.model_id = model_id
        self.requests_per_minute = requests_per_minute
        self.next_call = 0.0
        self.api_key = os.environ.get(self.env_key)
        if not self.api_key:
            raise Blocked(f"{self.env_key} is not set")
        date = datetime.now(UTC).strftime("%Y-%m-%d")
        self.checkpoint = cache_dir / "checkpoints" / date / f"{model_id.replace('/', '_')}.jsonl"
        self.checkpoint.parent.mkdir(parents=True, exist_ok=True)
        self.raw: dict[str, int] = {}
        if self.checkpoint.exists():
            for line in self.checkpoint.read_text(encoding="utf-8").splitlines():
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue  # a line cut off when a run was interrupted: count that text again
                self.raw[entry["key"]] = entry["raw"]
        self.resumed, self.calls = len(self.raw), 0
        self.lock = threading.Lock()
        self.overhead = self.raw_count([self.OVERHEAD_PROBE]) - 1

    def call(self, turns: list[str]) -> int:
        """One request: the raw count of a conversation (user, assistant, user, ...).
        Raises ApiError."""
        raise NotImplementedError

    def raw_count(self, turns: list[str]) -> int:
        """Raw endpoint answer for a conversation, from the checkpoint when already known."""
        key = hashlib.sha256("\x1e".join(turns).encode()).hexdigest()
        if key in self.raw:
            return self.raw[key]
        for attempt in range(self.TRIES):
            self.wait_for_turn()
            try:
                raw = self.call(turns)
                break
            except ApiError as e:
                if e.status not in self.RETRY_STATUS and e.status is not None:
                    raise Blocked(f"{self.endpoint} refused the request (HTTP {e.status})", e) from e
                if attempt == self.TRIES - 1:
                    raise Blocked(f"{self.endpoint} kept failing after {self.TRIES} tries", e) from e
                time.sleep(e.retry_after or min(2.0**attempt, 30.0))
        with self.lock:
            self.raw[key] = raw
            self.calls += 1
            with self.checkpoint.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"key": key, "raw": raw}) + "\n")
        return raw

    def wait_for_turn(self) -> None:
        """Space out calls so the run stays under the requests-per-minute limit."""
        if not self.requests_per_minute:
            return
        with self.lock:
            now = time.monotonic()
            start = max(now, self.next_call)
            self.next_call = start + 60.0 / self.requests_per_minute
        time.sleep(start - now)

    def count(self, texts: list[str]) -> list[int]:
        with ThreadPoolExecutor(max_workers=self.WORKERS) as pool:
            raw = list(pool.map(lambda text: self.raw_count([text]), texts))
        counts = [r - self.overhead for r in raw]
        if min(counts) <= 0:
            raise Stop(f"{self.model_id}: a text has no tokens left after subtracting the overhead")
        return counts

    def describe(self) -> dict:
        return {
            "model_id": self.model_id,
            "tokenizer": self.endpoint,
            "library": self.library,
            "overhead_tokens_subtracted": self.overhead,
            "overhead_probe": f"raw count of the message {self.OVERHEAD_PROBE!r} minus 1",
            "requests_per_minute_limit_used": self.requests_per_minute,
            "api_calls_this_run": self.calls,
            "answers_resumed_from_checkpoint": self.resumed,
            "described_utc": utc_now(),
        }


def post_json(url: str, headers: dict[str, str], body: dict, timeout: float = 60.0) -> dict:
    """POST JSON with the standard library. Any failure becomes an ApiError."""
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(text)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = text[:300]
        retry_after = e.headers.get("Retry-After", "")
        delay = float(retry_after) if retry_after.replace(".", "", 1).isdigit() else None
        raise ApiError(e.code, message, delay) from e
    except OSError as e:  # DNS, connection reset, timeout
        raise ApiError(None, f"{type(e).__name__}: {e}") from e
