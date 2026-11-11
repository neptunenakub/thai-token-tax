"""Open models on Hugging Face, counted with the repo's own tokenizer.json.

Only tokenizer.json is downloaded, never model weights, and no code from a repo is
executed (no trust_remote_code).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import tokenizers
from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import (
    EntryNotFoundError,
    GatedRepoError,
    HfHubHTTPError,
    RepositoryNotFoundError,
)
from tokenizers import Tokenizer

from .. import sha256_file, utc_now
from .base import Blocked

OVERHEAD_PROBE = "Hello"  # only used to report how many special tokens a tokenizer WOULD add


def _with_retry(fn, tries: int = 4):
    """Retry transient network errors with backoff. Access errors are not retried."""
    for attempt in range(tries):
        try:
            return fn()
        except (GatedRepoError, RepositoryNotFoundError, EntryNotFoundError):
            raise
        except HfHubHTTPError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (401, 403, 404) or attempt == tries - 1:
                raise
        except OSError:
            if attempt == tries - 1:
                raise
        time.sleep(2**attempt * 2)


def download_tokenizer_json(model_id: str, revision: str | None, cache_dir: Path):
    """-> (model info, local path of tokenizer.json). Raises Blocked with the real reason."""
    token = os.environ.get("HF_TOKEN") or None
    try:
        info = _with_retry(lambda: HfApi(token=token).model_info(model_id, revision=revision))
        path = _with_retry(
            lambda: hf_hub_download(
                model_id, "tokenizer.json", revision=info.sha, cache_dir=cache_dir / "hf", token=token
            )
        )
    except GatedRepoError as e:
        raise Blocked("gated repo: needs HF_TOKEN from an account that accepted the model terms", e) from e
    except EntryNotFoundError as e:
        raise Blocked(
            "repo has no tokenizer.json (custom tokenizer code would have to be executed; not done)", e
        ) from e
    except RepositoryNotFoundError as e:
        raise Blocked("repo not found, or private/gated and no valid HF_TOKEN", e) from e
    except (HfHubHTTPError, OSError) as e:
        raise Blocked("download failed", e) from e
    return info, Path(path)


class HFCounter:
    def __init__(self, model_id: str, revision: str | None, cache_dir: Path):
        self.model_id = model_id
        self.info, self.path = download_tokenizer_json(model_id, revision, cache_dir)
        self.tokenizer = Tokenizer.from_file(str(self.path))
        self.tokenizer.no_truncation()  # a tokenizer.json may carry truncation/padding settings
        self.tokenizer.no_padding()

    def count(self, texts: list[str]) -> list[int]:
        return [len(e.ids) for e in self.tokenizer.encode_batch(texts, add_special_tokens=False)]

    def describe(self) -> dict:
        spec = json.loads(self.path.read_text(encoding="utf-8"))
        card = self.info.card_data.to_dict() if self.info.card_data else {}
        plain = len(self.tokenizer.encode(OVERHEAD_PROBE, add_special_tokens=False).ids)
        special = len(self.tokenizer.encode(OVERHEAD_PROBE, add_special_tokens=True).ids)
        modified = self.info.last_modified
        return {
            "model_id": self.model_id,
            "tokenizer": f"tokenizer.json@{self.info.sha[:12]}",
            "library": f"tokenizers=={tokenizers.__version__}",
            "repo_revision": self.info.sha,
            "repo_last_modified": modified.strftime("%Y-%m-%dT%H:%M:%SZ") if modified else None,
            "gated": self.info.gated,
            "license": card.get("license"),
            "base_model": card.get("base_model"),
            "tokenizer_json_sha256": sha256_file(self.path),
            "tokenizer_model_type": (spec.get("model") or {}).get("type"),
            "n_vocab_with_added_tokens": self.tokenizer.get_vocab_size(with_added_tokens=True),
            "special_tokens_added": 0,
            "special_tokens_the_tokenizer_would_add": special - plain,
            "described_utc": utc_now(),
        }
