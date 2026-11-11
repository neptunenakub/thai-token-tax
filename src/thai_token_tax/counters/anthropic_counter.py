"""Claude models through the official count_tokens endpoint, using the Anthropic SDK.

    client.messages.count_tokens(model=..., messages=[...]).input_tokens
    https://platform.claude.com/docs/en/build-with-claude/token-counting
"""
from __future__ import annotations

from pathlib import Path

import anthropic

from .base import ApiCounter, ApiError

ROLES = ("user", "assistant")


class AnthropicCounter(ApiCounter):
    env_key = "ANTHROPIC_API_KEY"
    endpoint = "POST /v1/messages/count_tokens"
    library = f"anthropic=={anthropic.__version__}"

    def __init__(self, model_id: str, cache_dir: Path, requests_per_minute=None, client=None):
        # `client` is replaceable so the tests never touch the network.
        self.client = client
        super().__init__(model_id, cache_dir, requests_per_minute)

    def call(self, turns: list[str]) -> int:
        if self.client is None:
            self.client = anthropic.Anthropic(api_key=self.api_key, max_retries=2)
        messages = [{"role": ROLES[i % 2], "content": text} for i, text in enumerate(turns)]
        try:
            return self.client.messages.count_tokens(model=self.model_id, messages=messages).input_tokens
        except anthropic.APIStatusError as e:
            raise ApiError(e.status_code, e.message) from e
        except anthropic.APIConnectionError as e:
            raise ApiError(None, f"{type(e).__name__}: {e}") from e
