"""OpenAI encodings, counted locally with tiktoken.

Which OpenAI model uses which encoding is taken from tiktoken's own table
(tiktoken/model.py), looked up at run time by lookup_models() and saved with the
results. It is never typed from memory.
"""
from __future__ import annotations

import os
from pathlib import Path

import tiktoken

from .. import utc_now


class TiktokenCounter:
    def __init__(self, model_id: str, encoding: str, cache_dir: Path):
        os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(cache_dir / "tiktoken"))
        self.model_id = model_id
        self.encoding = tiktoken.get_encoding(encoding)

    def count(self, texts: list[str]) -> list[int]:
        # disallowed_special=(): text that looks like "<|endoftext|>" is counted as ordinary
        # text instead of raising an error or turning into one special token.
        return [len(self.encoding.encode(t, disallowed_special=())) for t in texts]

    def describe(self) -> dict:
        return {
            "model_id": self.model_id,
            "tokenizer": self.encoding.name,
            "library": f"tiktoken=={tiktoken.__version__}",
            "n_vocab": self.encoding.n_vocab,
            "special_tokens_added": 0,
            "described_utc": utc_now(),
        }


def lookup_models(model_ids: list[str]) -> dict[str, str | None]:
    """OpenAI model id -> encoding name, or None if this tiktoken version does not know it."""
    mapping: dict[str, str | None] = {}
    for model_id in model_ids:
        try:
            mapping[model_id] = tiktoken.encoding_name_for_model(model_id)
        except KeyError:
            mapping[model_id] = None
    return mapping


LOOKUP_SOURCE = f"https://github.com/openai/tiktoken/blob/{tiktoken.__version__}/tiktoken/model.py"
