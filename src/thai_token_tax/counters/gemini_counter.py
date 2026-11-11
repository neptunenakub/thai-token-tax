"""Gemini models through the official countTokens endpoint.

    POST https://generativelanguage.googleapis.com/v1beta/models/{model}:countTokens
    https://ai.google.dev/gemini-api/docs/tokens
"""
from __future__ import annotations

from .base import ApiCounter, post_json

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:countTokens"
ROLES = ("user", "model")


class GeminiCounter(ApiCounter):
    env_key = "GEMINI_API_KEY"
    endpoint = "POST v1beta/models/{model}:countTokens"
    library = "gemini REST API"

    def call(self, turns: list[str]) -> int:
        contents = [
            {"role": ROLES[i % 2], "parts": [{"text": text}]} for i, text in enumerate(turns)
        ]
        answer = post_json(
            URL.format(model=self.model_id),
            {"x-goog-api-key": self.api_key},  # in a header, never in the URL
            {"contents": contents},
        )
        return int(answer["totalTokens"])
