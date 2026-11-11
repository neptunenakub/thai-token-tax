"""OpenAI models through the official input-token counting endpoint.

    POST https://api.openai.com/v1/responses/input_tokens
    https://developers.openai.com/api/docs/guides/token-counting

Needed for models whose encoding tiktoken does not know (the GPT-6 family), and used
on a GPT-5.x model as a cross-check: API count minus overhead must equal tiktoken.
"""
from __future__ import annotations

from .base import ApiCounter, post_json

URL = "https://api.openai.com/v1/responses/input_tokens"
ROLES = ("user", "assistant")


class OpenAIApiCounter(ApiCounter):
    env_key = "OPENAI_API_KEY"
    endpoint = "POST /v1/responses/input_tokens"
    library = "openai REST API"

    def call(self, turns: list[str]) -> int:
        messages = [{"role": ROLES[i % 2], "content": text} for i, text in enumerate(turns)]
        answer = post_json(
            URL,
            {"Authorization": f"Bearer {self.api_key}"},
            {"model": self.model_id, "input": messages},
        )
        return int(answer["input_tokens"])
