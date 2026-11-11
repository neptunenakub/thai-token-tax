# Lab notebook

What was run, with which sources and versions, what came out, what went wrong or was
unexpected, and what is blocked and why. Every number here was copied from files in
`results/` and `data/` that the code in this repository wrote, unless the entry says otherwise.

"Day" is a stage of the work, not a calendar day: every run so far has the UTC date
2026-11-10. The labels `day2`, `day2b` and `day2c` in result file names come from these stages.
The entries up to day 3c were first written in Thai; they have been translated and condensed,
and every figure was carried over unchanged.

This project measures **cost** (token counts), not answer **quality**.

---

## Day 1 — measuring tools and local tokenizers

Run date: 2026-11-10 (UTC).

### What was run

| Step | Command (from the repository folder) | Output |
|---|---|---|
| 1 | `python -I -X utf8 scripts/prepare_data.py` | download FLORES-200, normalize, check sentence alignment |
| 2 | `python -I -X utf8 scripts/count_open.py` | count tokens per sentence → `results/open_counts_2026-11-10.csv` |
| 3 | `python -I -X utf8 scripts/analyze.py results/open_counts_2026-11-10.csv` | premium, 95% CI, characters per token |
| 4 | `python -I -X utf8 scripts/verify_open.py results/open_counts_2026-11-10.csv` | recount in a second way |

`python` is `.venv/Scripts/python` (Python 3.12.10), installed with `pip install -r requirements.txt`.
These scripts were replaced by the `ttt` command on day 1.5.

Versions: tiktoken 0.14.0, tokenizers 0.23.3, huggingface_hub 2.4.0, numpy 2.5.4, transformers 5.22.2,
sentencepiece 0.2.3 (the full set is in `requirements.lock.txt`).

### Data

- **FLORES-200 devtest, the original Meta release, was used, not FLORES+.** FLORES+ on Hugging Face
  (`openlanguagedata/flores_plus`) is a gated dataset: a request without a token got HTTP 401, and no
  `HF_TOKEN` was available that day (the probe result is in `data/source.json`).
- Source: <https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz>, which the official README of
  `facebookresearch/flores` links as "the original version of the dataset".
- Licence: CC BY-SA 4.0 (stated in the README of `facebookresearch/flores`); attribution is in `data/README.md`.
- Tarball SHA-256: `b8b0b76783024b85797e5cc75064eb83fc5288b41e9654dabc7be6ae944011f6` (25,585,843 bytes).
- Sentences: English 1,012 lines, Thai 1,012 lines, metadata 1,012 rows. All match; no empty line.

### Normalization

Rules: (1) Unicode NFC; (2) control characters (Cc): TAB/LF/CR/VT/FF become one space, any other is
deleted; format characters (Cf, such as the zero-width space) are deleted; (3) leading and trailing
whitespace is trimmed. Nothing else is touched.

| Language | Sentences | Changed by NFC | Changed by removing Cc/Cf | Changed by trimming | Changed in total |
|---|---:|---:|---:|---:|---:|
| eng_Latn | 1,012 | 0 | 1 | 0 | 1 |
| tha_Thai | 1,012 | 0 | 6 | 253 | 257 |

- Only one kind of character was removed, U+200B ZERO WIDTH SPACE: 2 in English (sentence 683), 9 in
  Thai (sentences 191, 310, 469, 492, 680, 741).
- 253 Thai sentences have one trailing space in the original file.
- Details and all sentence numbers: `data/normalization_log.json`.
- SHA-256 of the normalized file: `9df6db4cc0d577297870ceb68ff33f57d8c906df06d857be42843efaefc1924f`
  (two runs of `prepare_data.py` gave the same value).

### Which encoding OpenAI models use

- Reference: the tables `MODEL_TO_ENCODING` / `MODEL_PREFIX_TO_ENCODING` in
  <https://github.com/openai/tiktoken/blob/0.14.0/tiktoken/model.py> (tiktoken 0.14.0 was the newest
  release on PyPI on the run date).
- The current model list was read from <https://developers.openai.com/api/docs/models.md> on 2026-11-10,
  and the script asked `tiktoken.encoding_name_for_model()` for each name. Result:
  `results/open_tokenizers_2026-11-10.json`.

| Model | Encoding according to tiktoken 0.14.0 |
|---|---|
| gpt-5.2, gpt-5.2-pro, gpt-5.4, gpt-5.4-mini, gpt-5.4-pro, gpt-5.5, gpt-5.5-pro, gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna, gpt-4.1, gpt-4o, gpt-4o-mini | `o200k_base` |
| gpt-4-turbo, gpt-4, gpt-3.5-turbo | `cl100k_base` |
| gpt-oss-120b, gpt-oss-20b | `o200k_harmony` |
| **gpt-6-astra, gpt-6-sol, gpt-6-luna, gpt-6.1-sol, gpt-6.1-terra** | **not known to tiktoken (KeyError)** |

### Result: premium = total Thai tokens ÷ total English tokens

1,012 sentence pairs; 95% CI from a bootstrap over sentence pairs, 10,000 resamples (seed 20261110,
percentile method). Only the tokens of the text are counted: no BOS/EOS, no chat template. A
character is a Unicode code point.

| family | model / encoding | premium (TH/EN) | 95% CI | EN tokens | TH tokens | chars/token EN | chars/token TH | same counts as |
|---|---|---:|---|---:|---:|---:|---:|---|
| OpenAI | `tiktoken/o200k_base` | 1.954 | 1.930–1.979 | 26872 | 52520 | 4.91 | 2.40 |  |
| OpenAI | `tiktoken/cl100k_base` | 4.343 | 4.287–4.400 | 27181 | 118037 | 4.86 | 1.07 |  |
| OpenAI | `tiktoken/o200k_harmony` | 1.954 | 1.930–1.979 | 26872 | 52520 | 4.91 | 2.40 | `tiktoken/o200k_base` |
| Qwen | `Qwen/Qwen3-8B` | 2.541 | 2.508–2.575 | 27620 | 70195 | 4.78 | 1.80 |  |
| Qwen | `Qwen/Qwen3.5-9B` | 1.201 | 1.187–1.215 | 27529 | 33058 | 4.79 | 3.81 |  |
| Qwen | `Qwen/Qwen3.8-27B` | 1.201 | 1.187–1.215 | 27529 | 33058 | 4.79 | 3.81 | `Qwen/Qwen3.5-9B` |
| Typhoon | `typhoon-ai/typhoon2.5-qwen3-4b` | 2.541 | 2.508–2.575 | 27620 | 70195 | 4.78 | 1.80 | `Qwen/Qwen3-8B` |
| Typhoon | `typhoon-ai/typhoon2.1-gemma3-12b` | 1.600 | 1.580–1.621 | 27113 | 43385 | 4.87 | 2.91 |  |
| Typhoon | `typhoon-ai/llama3.1-typhoon2-8b-instruct` | 2.185 | 2.159–2.211 | 27170 | 59357 | 4.86 | 2.12 |  |
| Typhoon | `typhoon-ai/typhoon-7b` | 1.276 | 1.262–1.291 | 30027 | 38328 | 4.39 | 3.29 |  |
| Typhoon | `typhoon-ai/typhoon-s-thaillm-8b-instruct-research-preview` | 2.541 | 2.508–2.575 | 27620 | 70195 | 4.78 | 1.80 | `Qwen/Qwen3-8B` |
| OpenThaiGPT | `openthaigpt/openthaigpt1.5-7b-instruct` | 2.541 | 2.508–2.575 | 27620 | 70195 | 4.78 | 1.80 | `Qwen/Qwen3-8B` |
| OpenThaiGPT | `openthaigpt/openthaigpt-1.6-72b-instruct` | 2.541 | 2.508–2.575 | 27620 | 70195 | 4.78 | 1.80 | `Qwen/Qwen3-8B` |
| OpenThaiGPT | `openthaigpt/openthaigpt-r1-32b-instruct` | 2.541 | 2.508–2.575 | 27620 | 70195 | 4.78 | 1.80 | `Qwen/Qwen3-8B` |
| OpenThaiGPT | `openthaigpt/openthaigpt-1.0.0-7b-chat` | 1.024 | 1.013–1.035 | 31154 | 31894 | 4.24 | 3.95 |  |
| OpenThaiGPT | `openthaigpt/openthaigpt-thaillm-8b-instruct-v0.7.2-research-preview` | 2.541 | 2.508–2.575 | 27620 | 70195 | 4.78 | 1.80 | `Qwen/Qwen3-8B` |
| SEA-LION | `aisingapore/Nemotron-SEA-LION-v4.8-30B-A3B` | 2.365 | 2.335–2.395 | 27826 | 65795 | 4.74 | 1.92 |  |
| SEA-LION | `aisingapore/Qwen-SEA-LION-v4.5-27B-IT` | 1.201 | 1.187–1.215 | 27529 | 33058 | 4.79 | 3.81 | `Qwen/Qwen3.5-9B` |
| SEA-LION | `aisingapore/Qwen-SEA-LION-v4-32B-IT` | 2.541 | 2.508–2.575 | 27620 | 70195 | 4.78 | 1.80 | `Qwen/Qwen3-8B` |
| SEA-LION | `aisingapore/Gemma-SEA-LION-v4-27B-IT` | 1.600 | 1.580–1.621 | 27113 | 43385 | 4.87 | 2.91 | `typhoon-ai/typhoon2.1-gemma3-12b` |
| SEA-LION | `aisingapore/Llama-SEA-LION-v3.5-8B-R` | 2.185 | 2.159–2.211 | 27170 | 59357 | 4.86 | 2.12 | `typhoon-ai/llama3.1-typhoon2-8b-instruct` |
| SEA-LION | `aisingapore/Gemma-SEA-LION-v3-9B-IT` | 1.842 | 1.817–1.867 | 27035 | 49795 | 4.88 | 2.53 |  |
| Gemma | `google/gemma-4-31B-it` | 1.600 | 1.580–1.621 | 27113 | 43385 | 4.87 | 2.91 | `typhoon-ai/typhoon2.1-gemma3-12b` |

"same counts as" means the token counts are **identical on every sentence in both languages** to
the tokenizer named (measured on this data; it does not confirm the tokenizer files are the same file).

Result files:
- `results/open_counts_2026-11-10.csv`: raw, 46,552 rows (23 tokenizers × 2 languages × 1,012 sentences),
  SHA-256 `55fd00e330151fadaa6961cc9c440ff1d2239554f77be1c4933340a3ac66b304`
- `results/open_tokenizers_2026-11-10.json`: repository revision, SHA-256 of each `tokenizer.json`,
  vocabulary size, and the blocked items with their real errors
- `results/open_summary_2026-11-10.csv` / `.json` / `.md`: the table above
- `results/open_verification_2026-11-10.json`: the recount

### Blocked (not measured, and not guessed)

| Item | Reason | What would unblock it |
|---|---|---|
| `meta-llama/Llama-4-Scout-17B-16E-Instruct` | gated, HTTP 401 | `HF_TOKEN` of an account that accepted the terms on Hugging Face |
| `meta-llama/Llama-3.3-70B-Instruct` | gated, HTTP 401 | same |
| `meta-llama/Llama-3.1-8B-Instruct` | gated, HTTP 401 | same |
| `google/gemma-3-27b-it` | gated, HTTP 401 | same |
| `aisingapore/SEA-LION-v1-7B` | no `tokenizer.json` (HTTP 404); the repository uses its own tokenizer code, which would have to be executed (`trust_remote_code`) | running downloaded code, which this project does not do |
| FLORES+ (data) | gated, HTTP 401 | `HF_TOKEN` of an account that accepted the terms |
| OpenAI GPT-6 family | no official source says which encoding it uses | see note 1 below |

None of `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `HF_TOKEN` was set that day.

### Recount

- `count_open.py` and `analyze.py` were run twice: the SHA-256 of the raw CSV and of the summary CSV
  were the same both times.
- All 23 tokenizers: decode(encode(text)) returns the original text for 1,012/1,012 sentences in both languages.
- The 20 Hugging Face tokenizers: no `<unk>` at all (0 tokens), and a recount with
  `transformers.AutoTokenizer` gave the same count on every sentence.
- 5 repositories also ship a SentencePiece file (`tokenizer.model`). Recounted with the `sentencepiece`
  library: 3 agree, **2 do not** (note 5).

### Unexpected, or open

1. **GPT-6 could not be measured with tiktoken.** OpenAI's current flagship family is GPT-6, but
   tiktoken 0.14.0 has no mapping for it and the official documentation does not name an encoding. The
   tiktoken repository has issue #608 (closed), issue #629 and PR #616 (still open) about this. Outside
   experimenters report that GPT-6 token counts equal GPT-5, but OpenAI has not confirmed it. So the
   `o200k_base` row **can only be claimed for the GPT-5 family** at this point (tiktoken matches by the
   prefix rule `gpt-5`). Resolved on day 2 by measuring GPT-6 through OpenAI's counting endpoint.
2. **FLORES-200 was used instead of FLORES+.** FLORES+ may have corrected some translations; compared on day 2b.
3. **The sentences are not committed.** The FLORES+ dataset page asks that the data not be redistributed
   publicly unless protected from scraping (to keep test data out of training data). The sentence file
   stays local (`data/.gitignore`); the source, hashes and the script to rebuild it are committed
   instead. The licence would allow committing the text.
4. **Qwen changed tokenizer between versions.** Qwen3 gives 2.541; Qwen3.5 and Qwen3.8 give 1.201
   (vocabulary 151,669 → 248,070/248,077). Almost all current Thai models that could be measured
   (Typhoon 2.5, Typhoon-S ThaiLLM, OpenThaiGPT 1.5/1.6/R1/ThaiLLM) give the same count as Qwen3 on
   every sentence.
5. **typhoon-7b and openthaigpt-1.0.0-7b-chat can be counted two ways.** The table uses `tokenizer.json`
   (the same method as every model, and equal to `transformers`), but the SentencePiece file in the same
   repository gives slightly different counts:

   | Model | premium from `tokenizer.json` | premium from SentencePiece | sentences counted differently (EN / TH) |
   |---|---:|---:|---:|
   | `typhoon-ai/typhoon-7b` | 1.2765 | 1.2855 | 0 / 525 |
   | `openthaigpt/openthaigpt-1.0.0-7b-chat` | 1.0238 | 1.0215 | 251 / 609 |

   From the files: the two split Thai words differently in some positions, and the `tokenizer.json` of
   OpenThaiGPT 1.0.0 adds a `▁` at the start of the sentence while its SentencePiece file is set not to.
   A runtime that uses SentencePiece directly may therefore get the second number.
6. **The official Llama and Gemma 3 repositories were not measured yet.** What was measured are public
   derived repositories (such as `llama3.1-typhoon2-8b-instruct`, `Llama-SEA-LION-v3.5-8B-R`,
   `typhoon2.1-gemma3-12b`); whether their tokenizers equal Meta's and Google's could not be confirmed
   until the official repositories were reachable (Llama 3.1: day 2b; Llama 3.3: day 3c).
   `google/gemma-4-31B-it` is not gated and was measured.
7. **Translation spot check.** 20 pairs were drawn with a fixed seed into `data/spotcheck_20.md` (local
   only, not committed). In the first pair of that file (sentence 179) the Thai and English meanings do
   not appear to match. The data was not changed.

---

## Day 1.5 — code restructured into a package

Run date: 2026-11-10 (UTC). No API key. No new measurement: the day-1 files `results/*2026-11-10*`
were not changed.

### What changed

- `scripts/` was replaced by the package `src/thai_token_tax/` and the `ttt` command.

  | Command | What it does |
  |---|---|
  | `ttt prepare` | download FLORES-200, check the SHA-256, normalize, check alignment |
  | `ttt count [--out DIR]` | count tokens with every tokenizer in `registry/models.toml` |
  | `ttt verify COUNTS_CSV` | recount in a second way |
  | `ttt analyze COUNTS_CSV [--out DIR]` | premium, 95% CI, tokens per 1,000 characters, write `latest.json` |
  | `ttt all [--out DIR]` | prepare → count → verify → analyze |

- Install: `pip install -e ".[dev]"`. Versions are pinned in `pyproject.toml` (`requirements.txt` was
  removed; `requirements.lock.txt` is still the full `pip freeze`).
- `registry/models.toml` (28 entries: tiktoken 3, Hugging Face 25) and `registry/languages.toml`
  (baseline `eng_Latn`, target `tha_Thai`). The code no longer contains a list of models or languages.
- Counters share one interface (`count`, `describe`, the `Blocked` error): `tiktoken_counter.py`,
  `hf_counter.py`.
- Result files of the new code are named `counts_<date>.csv`, `counts_<date>.meta.json`,
  `verification_<date>.json`, `summary_<date>.{csv,json,md}`, and the code **refuses to overwrite an
  existing result file** (a new folder must be given with `--out`).
- The local sentence file was renamed `data/flores200_devtest.tsv`; same content (SHA-256
  `9df6db4cc0d577297870ceb68ff33f57d8c906df06d857be42843efaefc1924f`, equal to day 1).
- `tests/`: 26 tests, no network (normalization, alignment, premium arithmetic, bootstrap, registry,
  the count stage with a fake counter), and `.github/workflows/ci.yml` (ruff + pytest), which had not
  run on GitHub.
- `*.egg-info/`, `.pytest_cache/`, `.ruff_cache/` added to `.gitignore`.

### Regression against day 1

`ttt all --out .cache/regression_day1.5` (a folder outside git) was compared with the day-1 files:

| Compared | How | Result |
|---|---|---|
| Per-sentence token counts of 23 tokenizers (46,552 rows), every column except `run_date_utc` | `cut -d, -f2- <file> \| sha256sum` on both files | **equal**: `ecfc1febb91de02e68fa9ecec630aadc962b1ee6a7e93a965658d13242b629c7` for both |
| The whole raw CSV (same run date) | `sha256sum` | **byte-identical**: `55fd00e330151fadaa6961cc9c440ff1d2239554f77be1c4933340a3ac66b304` |
| Summary table, 23 models × 14 fields (premium, CI low/high to 6 decimals, total tokens, total characters, characters per token, `same_counts_as`, ...) | text comparison, field by field, with `results/open_summary_2026-11-10.csv` | **0 fields differ** |
| Blocked list | read from the run | the same 5, same reasons |
| Recount (`verify`) | read from the run | as day 1: decode returns 1,012/1,012; only the SentencePiece file differs for typhoon-7b (TH 525 sentences) and openthaigpt-1.0.0 (EN 251, TH 609) |

The test `test_day1_summary_is_reproduced_from_the_raw_counts` repeats the third check on every pytest run.

### Added to the summary: an absolute rate

`ttt analyze results/open_counts_2026-11-10.csv` wrote `results/summary_2026-11-10.{csv,json,md}` and
`results/latest.json` from the day-1 raw CSV (nothing was recounted). The premium and CI columns equal
`open_summary_2026-11-10.csv` in every value. New: tokens per 1,000 characters for each language.
Column names changed from `en_*`/`th_*` to `baseline_*`/`target_*`.

- **premium** compares Thai with English **inside one model**.
- **tokens per 1,000 Thai characters** compares **across models** (the same Thai text, 126,100 characters).

Distinct tokenizers only, from fewest Thai tokens to most:

| tokenizer | tokens per 1,000 Thai characters | total Thai tokens | tokens per 1,000 English characters | premium | others with identical counts |
|---|---:|---:|---:|---:|---:|
| `openthaigpt/openthaigpt-1.0.0-7b-chat` | 252.9 | 31,894 | 236.1 | 1.024 | 0 |
| `Qwen/Qwen3.5-9B` | 262.2 | 33,058 | 208.6 | 1.201 | 2 |
| `typhoon-ai/typhoon-7b` | 303.9 | 38,328 | 227.5 | 1.276 | 0 |
| `typhoon-ai/typhoon2.1-gemma3-12b` | 344.1 | 43,385 | 205.5 | 1.600 | 2 |
| `aisingapore/Gemma-SEA-LION-v3-9B-IT` | 394.9 | 49,795 | 204.9 | 1.842 | 0 |
| `tiktoken/o200k_base` | 416.5 | 52,520 | 203.6 | 1.954 | 1 |
| `typhoon-ai/llama3.1-typhoon2-8b-instruct` | 470.7 | 59,357 | 205.9 | 2.185 | 1 |
| `aisingapore/Nemotron-SEA-LION-v4.8-30B-A3B` | 521.8 | 65,795 | 210.9 | 2.365 | 0 |
| `Qwen/Qwen3-8B` | 556.7 | 70,195 | 209.3 | 2.541 | 7 |
| `tiktoken/cl100k_base` | 936.1 | 118,037 | 206.0 | 4.343 | 0 |

The full table of 23 rows is `results/summary_2026-11-10.md`.

### Design notes

1. There is no separate module for the registry or the count stage: `data.load_languages()` reads
   `languages.toml`; `counters/__init__.py` reads `models.toml` and runs the count stage.
2. `models.toml` has an optional `revision` field. 20 Hugging Face repositories are pinned to the commit
   measured on day 1, so a rerun gives the same result. Measuring a newer tokenizer means changing or
   removing that field.
3. `counts_<date>.meta.json` holds versions, hashes and the blocked list.
4. Result file names carry only the date, so one UTC day can hold one set per folder (extended on day 2
   with a source name, and on day 2b with labels).
5. At this point `results/latest.json` pointed at the day-1 raw CSV and the new-format summary, so it
   had no `counts_meta`/`verification` fields (the day-1 files are named `open_tokenizers_*` /
   `open_verification_*`).
6. `ttt all` runs verify before analyze, so `latest.json` can point at the verification file.
7. GitHub Pages deployed from a branch can only serve the root or `/docs`, so publishing a `site/`
   folder needs a workflow. Not checked against the official documentation until day 4.

---

## Day 2 — Claude, Gemini and OpenAI through their APIs

Run date: 2026-11-10 (UTC). API keys were read from environment variables only; no key is in any
result file or log.

### Cost and rate limits, checked in the official documentation before any call (read 2026-11-10)

| Service | Endpoint | Billed? | Rate limit | Source |
|---|---|---|---|---|
| Anthropic | `POST /v1/messages/count_tokens` | the documentation says it is free | documentation table: tier Start 5,000 requests/minute, **but this account got 100 requests/minute** (header `anthropic-ratelimit-requests-limit: 100`) | <https://platform.claude.com/docs/en/build-with-claude/token-counting>, section "Pricing and rate limits" |
| OpenAI | `POST /v1/responses/input_tokens` | the article says it is free and does not use inference quota | no number found for this endpoint | <https://help.openai.com/en/articles/4936856> and <https://developers.openai.com/api/docs/guides/token-counting> |
| Gemini | `POST v1beta/models/{model}:countTokens` | the billing FAQ item "Is `GetTokens` billed?" says token-counting requests are not billed and do not count against inference quota | no number found for this endpoint | <https://ai.google.dev/gemini-api/docs/billing> (item `is-gettokens-billed`), <https://ai.google.dev/gemini-api/docs/tokens> |

- Gemini: the FAQ calls it `GetTokens`, not `countTokens`. It was read as the same thing (the item
  follows the one that teaches `count_tokens`), and the pricing page has no price for token counting.
- Every call was to a token-counting endpoint. No model was asked to generate an answer.

### Model lists (read from the official pages that day, not from memory)

- OpenAI: <https://developers.openai.com/api/docs/models.md>
- Gemini: <https://ai.google.dev/gemini-api/docs/models>
- Anthropic: <https://platform.claude.com/docs/en/about-claude/models/overview> and
  <https://platform.claude.com/docs/en/about-claude/model-deprecations>

### What was built

- Three counters in `src/thai_token_tax/counters/`: `openai_api_counter.py`, `gemini_counter.py`,
  `anthropic_counter.py` (the last uses the official SDK, `anthropic==2.7.0`). All share `ApiCounter` in
  `base.py`:
  - **Overhead subtraction:** the endpoints count the whole request, so the same framing tokens come
    with every answer. The counter measures them on the message `"a"` (raw result minus 1) and subtracts
    them from every sentence. The value is recorded in `.meta.json`.
  - **Checkpoint:** every answer is saved to `.cache/checkpoints/<date>/<model>.jsonl`; an interrupted
    run resumes without asking again.
  - **Polite to the API:** at most 4 requests at once, retry with backoff on 429/5xx, pacing from
    `[rate_limits]` in the registry (Anthropic 90 requests/minute).
- `sample_of` in `registry/models.toml`: a model with this field is counted on 100 sentence pairs only,
  a fixed random sample (seed 20261110); `analyze` compares it with a fully measured model. If every
  sentence matches they are treated as the same tokenizer generation; if not, the model must be
  measured in full.
- One result set per source: `counts_<date>_<source>.csv` + `.meta.json`, `verification_<date>_<source>.json`;
  `analyze` merges the sources into one table (new columns `source`, `coverage`).
- 42 tests, no network (overhead subtraction, checkpoint, retry, blocking, pacing, merging sources,
  sampled rows).

### Commands

```
ttt count --out results
ttt verify --dir results
ttt analyze --dir results --label day2
```

The sources were run one at a time (`--source`). The API calls happened in a first run written to
`.cache/day2_run/`; the files in `results/` were built from the same answers in the checkpoint and
equal the first run byte for byte.

### Results

The same 1,012 FLORES-200 devtest sentence pairs as day 1 (SHA-256 `9df6db4c…`). premium = total Thai
tokens ÷ total English tokens, **for use inside one model**; tokens per 1,000 Thai characters **for use
across models**.

**Distinct tokenizers, from fewest Thai tokens to most**

| tokenizer (first one measured with these counts) | source | tokens per 1,000 Thai characters | total Thai tokens | tokens per 1,000 English characters | premium (95% CI) | other models with identical counts |
|---|---|---:|---:|---:|---|---|
| `openthaigpt/openthaigpt-1.0.0-7b-chat` | open | 252.9 | 31,894 | 236.1 | 1.024 (1.013–1.035) |  |
| `Qwen/Qwen3.5-9B` | open | 262.2 | 33,058 | 208.6 | 1.201 (1.187–1.215) | 2 more open models |
| `typhoon-ai/typhoon-7b` | open | 303.9 | 38,328 | 227.5 | 1.276 (1.262–1.291) |  |
| `gemini-4-argon` | gemini | 325.9 | 41,094 | 205.0 | 1.519 (1.500–1.538) |  |
| `typhoon-ai/typhoon2.1-gemma3-12b` | open | 344.1 | 43,385 | 205.5 | 1.600 (1.580–1.621) | `gemini-3.8-flash`, `gemini-3.6-flash` (sample of 100), `gemini-3.5-flash-lite` (sample of 100), `gemini-3.1-pro-preview` (sample of 100); 2 more open models |
| `aisingapore/Gemma-SEA-LION-v3-9B-IT` | open | 394.9 | 49,795 | 204.9 | 1.842 (1.817–1.867) |  |
| `tiktoken/o200k_base` | open | 416.5 | 52,520 | 203.6 | 1.954 (1.930–1.979) | `gpt-6-astra`, `gpt-6-sol` (sample of 100), `gpt-6-luna` (sample of 100), `gpt-6.1-sol` (sample of 100), `gpt-6.1-terra` (sample of 100), `gpt-5.5`, `gpt-5.6-sol` (sample of 100), `gpt-5.4` (sample of 100), `gpt-5.2` (sample of 100); 1 more open model |
| `typhoon-ai/llama3.1-typhoon2-8b-instruct` | open | 470.7 | 59,357 | 205.9 | 2.185 (2.159–2.211) | 1 more open model |
| `aisingapore/Nemotron-SEA-LION-v4.8-30B-A3B` | open | 521.8 | 65,795 | 210.9 | 2.365 (2.335–2.395) |  |
| `Qwen/Qwen3-8B` | open | 556.7 | 70,195 | 209.3 | 2.541 (2.508–2.575) | 7 more open models |
| `claude-haiku-4-5-20251001` | anthropic | 886.5 | 111,785 | 218.9 | 3.870 (3.820–3.922) | `claude-sonnet-4-6` (sample of 100) |
| `claude-opus-5-5` | anthropic | 889.5 | 112,169 | 317.6 | 2.676 (2.645–2.709) | `claude-fable-5-2` (sample of 100), `claude-sonnet-5-5` (sample of 100), `claude-haiku-5-5` (sample of 100) |
| `tiktoken/cl100k_base` | open | 936.1 | 118,037 | 206.0 | 4.343 (4.287–4.400) |  |

"Identical counts" means the same token count on every sentence in both languages (sampled models: on
all 100 sampled pairs).

**Models measured through an API**

| Model | Source | Measured | Sentences | Overhead subtracted | premium (95% CI) | tokens per 1,000 Thai characters | Same counts as |
|---|---|---|---:|---:|---|---:|---|
| `gpt-6-astra` | openai | full | 1012 | 6 | 1.954 (1.930–1.979) | 416.5 | `tiktoken/o200k_base` |
| `gpt-6-sol` | openai | sample of 100 pairs | 100 | 6 | — | — | `tiktoken/o200k_base` |
| `gpt-6-luna` | openai | sample of 100 pairs | 100 | 6 | — | — | `tiktoken/o200k_base` |
| `gpt-6.1-sol` | openai | sample of 100 pairs | 100 | 6 | — | — | `tiktoken/o200k_base` |
| `gpt-6.1-terra` | openai | sample of 100 pairs | 100 | 6 | — | — | `tiktoken/o200k_base` |
| `gpt-5.5` | openai | full | 1012 | 6 | 1.954 (1.930–1.979) | 416.5 | `tiktoken/o200k_base` |
| `gpt-5.6-sol` | openai | sample of 100 pairs | 100 | 6 | — | — | `tiktoken/o200k_base` |
| `gpt-5.4` | openai | sample of 100 pairs | 100 | 6 | — | — | `tiktoken/o200k_base` |
| `gpt-5.2` | openai | sample of 100 pairs | 100 | 6 | — | — | `tiktoken/o200k_base` |
| `gemini-3.8-flash` | gemini | full | 1012 | 1 | 1.600 (1.580–1.621) | 344.1 | `typhoon-ai/typhoon2.1-gemma3-12b` |
| `gemini-4-argon` | gemini | full | 1012 | 31 | 1.519 (1.500–1.538) | 325.9 |  |
| `gemini-3.6-flash` | gemini | sample of 100 pairs | 100 | 1 | — | — | `typhoon-ai/typhoon2.1-gemma3-12b` |
| `gemini-3.5-flash-lite` | gemini | sample of 100 pairs | 100 | 1 | — | — | `typhoon-ai/typhoon2.1-gemma3-12b` |
| `gemini-3.1-pro-preview` | gemini | sample of 100 pairs | 100 | 1 | — | — | `typhoon-ai/typhoon2.1-gemma3-12b` |
| `claude-opus-5-5` | anthropic | full | 1012 | 8 | 2.676 (2.645–2.709) | 889.5 |  |
| `claude-fable-5-2` | anthropic | sample of 100 pairs | 100 | 8 | — | — | `claude-opus-5-5` |
| `claude-sonnet-5-5` | anthropic | sample of 100 pairs | 100 | 8 | — | — | `claude-opus-5-5` |
| `claude-haiku-5-5` | anthropic | sample of 100 pairs | 100 | 8 | — | — | `claude-opus-5-5` |
| `claude-haiku-4-5-20251001` | anthropic | full | 1012 | 7 | 3.870 (3.820–3.922) | 886.5 |  |
| `claude-sonnet-4-6` | anthropic | sample of 100 pairs | 100 | 7 | — | — | `claude-haiku-4-5-20251001` |

A sampled model has no premium of its own. Full table: `results/summary_2026-11-10_day2.md`.

### Is the overhead really constant? (tested, not assumed)

Done for every fully measured model (`ttt verify`):

1. **Length:** send `"a"`, `"a a"`, … up to 500 words. Raw result minus the number of words must equal
   the overhead every time (one more ` a` must add exactly 1 token).
2. **Content and language:** draw 3 real sentences from Thai and English, 24 sets, and send each set as
   a 3-message conversation. Its raw result minus the raw results of the three sentences sent alone must
   be one constant. If the overhead depended on language, script or length, this value would vary.
3. **Repeat:** send 50 sentences a second time; the answer must be the same.
4. **Against the local tokenizer** (only models tiktoken knows): the API result after subtracting the
   overhead must equal tiktoken on every sentence.

| Model | Overhead | Length test (1–500 words) | Content test (24 sets, differences found) | Repeat, 50 sentences | Against tiktoken, per sentence |
|---|---:|---|---|---|---|
| `gpt-6-astra` | 6 | constant | constant [-2] | 0/50 differ | not known to tiktoken |
| `gpt-5.5` | 6 | constant | constant [-2] | 0/50 differ | o200k_base: EN 0, TH 0 sentences differ |
| `gemini-3.8-flash` | 1 | constant | constant [0] | 0/50 differ | not known to tiktoken |
| `gemini-4-argon` | 31 | constant | constant [-52] | 0/50 differ | not known to tiktoken |
| `claude-opus-5-5` | 8 | constant | constant [-12] | 0/50 differ | not known to tiktoken |
| `claude-haiku-4-5-20251001` | 7 | constant | constant [-8] | 0/50 differ | not known to tiktoken |

### Blocked (not measured, and not guessed)

| Item | Source | HTTP | Real message from the API (shortened) |
|---|---|---:|---|
| `aisingapore/SEA-LION-v1-7B` | open | 404 | repo has no tokenizer.json (custom tokenizer code would have to be executed; not done): 404 Client Error. |
| `meta-llama/Llama-4-Scout-17B-16E-Instruct` | open | 403 | gated repo: needs HF_TOKEN from an account that accepted the model terms: 403 Client Error. |
| `meta-llama/Llama-3.3-70B-Instruct` | open | 403 | gated repo: needs HF_TOKEN from an account that accepted the model terms: 403 Client Error. |
| `meta-llama/Llama-3.1-8B-Instruct` | open | 403 | gated repo: needs HF_TOKEN from an account that accepted the model terms: 403 Client Error. |
| `google/gemma-3-27b-it` | open | 403 | gated repo: needs HF_TOKEN from an account that accepted the model terms: 403 Client Error. |
| `gemini-2.5-pro` | gemini | 404 | POST v1beta/models/{model}:countTokens refused the request: This model models/gemini-2.5-pro is no longer available to new users. Please update your code to use models/ge |
| `gemini-2.5-flash` | gemini | 404 | POST v1beta/models/{model}:countTokens refused the request: This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/ |

What would unblock each:

| Item | Needed |
|---|---|
| The 3 Llama repositories (`meta-llama/…`) | accept the terms on the model page with the account of the `HF_TOKEN`, then approval by Meta (the token works but gets HTTP 403) |
| `google/gemma-3-27b-it` | the same: accept the Gemma terms on the model page |
| `aisingapore/SEA-LION-v1-7B` | nothing planned: it would need code from the repository to be executed |
| `gemini-2.5-pro`, `gemini-2.5-flash` | cannot be unblocked from this side: the API says the model is no longer available to new users |
| FLORES+ | accept the dataset terms on Hugging Face |

### Findings

1. **Current Claude models** (`claude-opus-5-5` measured in full; Fable 5.2, Sonnet 5.5, Haiku 5.5 match
   on all 100 sampled pairs) have a premium of 2.676 (95% CI 2.645–2.709). Across models, in tokens per
   1,000 Thai characters: Claude 889.5, `o200k_base` (GPT-5.x and GPT-6) 416.5, Gemini 3.x 344.1,
   Gemini 4 Argon 325.9.
2. **The two Claude tokenizer generations spend almost the same number of tokens on Thai, yet their
   premiums differ a lot.** The older one (`claude-haiku-4-5-20251001`; `claude-sonnet-4-6` matches on the
   sample) uses 111,785 Thai tokens in total, the current one 112,169. But English tokens per 1,000
   characters moved from 218.9 to 317.6, so the premium fell from 3.870 to 2.676 because **English got
   more expensive, not because Thai got cheaper**. This is why the absolute rate is reported next to the premium.
3. **GPT-6 was measured, and it counts the same as `o200k_base` on every sentence.** `gpt-6-astra`,
   measured in full through the official endpoint, equals tiktoken `o200k_base` on all 1,012 pairs;
   `gpt-6-sol`, `gpt-6-luna`, `gpt-6.1-sol`, `gpt-6.1-terra` match on the sample of 100 pairs. The open
   point from day 1 is closed by measurement. This is a result on this data, not a statement by OpenAI
   that the encoding is the same.
4. **The overhead subtraction checks out against a local tokenizer:** `gpt-5.5` through the API, minus
   6 tokens, equals tiktoken `o200k_base` on every sentence in both languages (0 of 2,024 differ).
5. **Gemini 3.x counts the same as the Gemma tokenizer on every sentence.** `gemini-3.8-flash` (full,
   overhead 1) equals `typhoon-ai/typhoon2.1-gemma3-12b` and `google/gemma-4-31B-it` measured locally;
   `gemini-3.6-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-pro-preview` match on the sample.
   **`gemini-4-argon` uses a different tokenizer** (its sample did not match, so it was measured in full)
   and has an overhead of 31 tokens per request, constant in every test.
6. **Limit of the Claude numbers:** Anthropic's documentation says the result of `count_tokens` is an
   estimate that may differ slightly from actual usage and may include tokens added by the system that
   are not billed. Here the excess was constant (8 and 7 tokens) and subtracted; a comparison with the
   usage of real requests followed on day 3b.
7. **Sanity check against an external single-prompt dataset** (a token-cost-by-language dataset on
   Hugging Face, October 2026): all within ±20%. Claude 2.676 against 2.53, GPT 1.954 against 1.74,
   Gemini 3.x 1.600 and Gemini 4 1.519 against 1.35. The reference values were noted before this project
   and are not reproduced by any file in this repository.
8. **The Anthropic rate limit on this account is 100 requests/minute**, not the 5,000 in the
   documentation table. The first run sent 4 requests at once without pacing and met 429 responses for a
   while (the counter retried and no answer was lost). A pacer at 90 requests/minute was then added to
   the registry, so one full Claude generation takes about 23 minutes (2,024 requests at 90 per minute).
9. **API answers used in the result files:** OpenAI 5,515, Gemini 4,711, Anthropic 4,854 (not counting
   the verify stage and connection tests). All were token counts. The billing pages of the three vendors
   cannot be read by the code.
10. **Rerun of the `open` source with `HF_TOKEN`:** the 23 tokenizers gave the same result as day 1 in
    every value (the hash of every column except the date is equal). The 4 gated repositories still
    answered HTTP 403: the account had not accepted their terms.
11. **Not done:** no second full pass over the APIs (only the 50 repeated sentences per fully measured
    model), and no comparison with FLORES+ yet.
12. **The summary of this stage is named `summary_2026-11-10_day2.*`** because
    `summary_2026-11-10.*` from day 1.5 existed and the code does not overwrite. `ttt analyze` got a
    `--label` option for this. `results/latest.json` points at the day2 set; the files of day 1 and 1.5
    were not changed.
13. **Additions to the design:** (a) `sample_of` and `[rate_limits]` in `models.toml`; (b) the shared
    class `ApiCounter` and the HTTP helper live in `counters/base.py`; (c) OpenAI and Gemini are called
    with the standard library, Anthropic with its official SDK, so there is one more dependency
    (`anthropic==2.7.0`); (d) if a whole source is blocked the code writes only
    `counts_<date>_<source>.blocked.json` and no result set, so the source can be run again the same
    day once unblocked; (e) checkpoints are tied to the UTC date, so a run across midnight starts counting again.

### Addendum (no measured number changed)

- **Whether token counting used any credit cannot be seen from the API.** One counting request was sent
  to each vendor and every field of the answer inspected: no field or header about cost, credit, usage
  or balance.
  - Anthropic `count_tokens`: the body has only `input_tokens`
  - OpenAI `input_tokens`: the body has only `object`, `input_tokens`
  - Gemini `countTokens`: the body has only `totalTokens`, `promptTokensDetails`

  Anthropic's usage and cost reports are in the Admin API, which needs an Admin API key; this project
  has only a normal key. So the code cannot confirm that the charge was zero; that can only be seen on
  each vendor's usage or billing page.
- **Meta's Llama repositories:** an access request was pending review; all 3 still answered HTTP 403
  and stayed on the blocked list.
- **`google/gemma-3-27b-it`:** tried with `HF_TOKEN`, HTTP 403 (the Gemma terms had not been accepted on
  the model page).
- **The Anthropic rate limit actually seen:** 100 requests/minute (header
  `anthropic-ratelimit-requests-limit: 100`), against 5,000 for tier Start in the documentation table.
  Real runs were paced at 90 requests/minute.

---

## Day 2b — Llama 3.1, and FLORES+ (first attempt)

### Meta's Llama 3.1

- Access to `meta-llama/Llama-3.1-8B-Instruct` was granted. `Llama-3.3-70B-Instruct`,
  `Llama-4-Scout-17B-16E-Instruct` and `google/gemma-3-27b-it` still answered 403 and stayed blocked.
- **Adding without overwriting:** the new option `ttt count --source open --model <id> --label llama31`
  writes its own set, `counts_2026-11-10_open-llama31.csv` (+ `.meta.json`,
  `verification_…_open-llama31.json`); the earlier set is untouched. `analyze` merges sets named
  `<source>-<label>`, and `ttt verify --source` takes the set name.
- Repository revision pinned in the registry: `0e9e39f249a16976918f6564b8830bc894c89659`.
- Result on 1,012 sentence pairs: premium **2.185 (2.159–2.211)**, 470.7 tokens per 1,000 Thai
  characters; decode returns 1,012/1,012 in both languages, no `<unk>`, and `transformers` agrees.
- **Answer to the open point of day 1:** Llama 3.1 counts the same as
  `typhoon-ai/llama3.1-typhoon2-8b-instruct` and `aisingapore/Llama-SEA-LION-v3.5-8B-R` **on every
  sentence in both languages** (0 of 2,024 values differ, per model). On this data those two use the
  same tokenizer as Llama 3.1.
- New summary: `results/summary_2026-11-10_day2b.*` (44 rows); `results/latest.json` points at it.
- 44 tests pass (new: add-on sets, merging in source order).

### FLORES+ (blocked at this point)

- Fetching `devtest/eng_Latn.jsonl` and `devtest/tha_Thai.jsonl` of `openlanguagedata/flores_plus` with
  `HF_TOKEN` got **HTTP 403** (`GatedRepoError`: "you are not in the authorized list").
- Cross-check: the dataset metadata page answered 200 and `README.md` answered 200, but the data files
  answered 403. A 200 seen on a HEAD request was therefore the dataset page, not a data file. The
  account had not accepted the dataset terms
  (<https://huggingface.co/datasets/openlanguagedata/flores_plus>).
- No other source was used instead, and no code for a second dataset was written at this point.

---

## Day 3 — prices, exchange rate, and cost in baht

Run date: 2026-11-10 (UTC). No API key. No new token measurement (uses
`results/summary_2026-11-10_day2b.csv`).

### What was run

```
ttt prices     # fetch the 3 official pricing pages + the Bank of Thailand rate -> results/prices_2026-11-10.json
ttt cost       # measured tokens x price x exchange rate                        -> results/costs_2026-11-10.{csv,json,md}
```

- Exchange rate: **33.527 baht per US dollar**, the Bank of Thailand weighted-average interbank
  exchange rate for 09 November 2026 (the newest published value when it was fetched at
  2026-11-10T09:25:04Z; the value for 10 November had not been published).
- Prices: 20 models read, 0 not found.
- Cost table: 132 rows = 3 scenarios × 44 models (20 models have a price; 24 open models have token
  counts only).

### Price sources (fetched 2026-11-10; no number from memory)

| Vendor | Official page |
|---|---|
| Anthropic | <https://platform.claude.com/docs/en/about-claude/pricing> |
| OpenAI | <https://developers.openai.com/api/docs/pricing> |
| Google | <https://ai.google.dev/gemini-api/docs/pricing> |
| Bank of Thailand | <https://www.bot.or.th/en/statistics/exchange-rate.html> (the code reads the JSON data file this page uses) |

- Price tier used: the standard list price for text; not batch, not cached, the shortest context tier.
- `registry/pricing.toml` only says which row of the page belongs to which model. **No price is written
  in the code or the registry.** Numbers are read from the page at run time, and the URL, time, SHA-256
  of the page and the text of the price cell are saved in `prices_2026-11-10.json` (copies of the pages
  are in `.cache/pricing/`, not in git).
- Checked by eye: all 20 prices the code read match the text on the pages, and the Bank of Thailand
  rate matches what the page shows in a browser.

| Model | input $ per 1M tokens | output $ per 1M tokens | text on the pricing page (input) |
|---|---:|---:|---|
| `claude-opus-5-5` | 4 | 20 | $4 / MTok |
| `claude-fable-5-2` | 8 | 40 | $8 / MTok |
| `claude-sonnet-5-5` | 2 | 10 | $2 / MTok |
| `claude-haiku-5-5` | 0.1 | 0.5 | $0.10 / MTok |
| `claude-haiku-4-5-20251001` | 1 | 5 | $1 / MTok |
| `claude-sonnet-4-6` | 3 | 15 | $3 / MTok |
| `gpt-6-astra` | 10 | 50 | $10.00 |
| `gpt-6-sol` | 2 | 10 | $2.00 |
| `gpt-6-luna` | 0.1 | 0.5 | $0.10 |
| `gpt-6.1-sol` | 2 | 10 | $2.00 |
| `gpt-6.1-terra` | 1 | 5 | $1.00 |
| `gpt-5.6-sol` | 4 | 20 | $4.00 |
| `gpt-5.5` | 5 | 30 | $5.00 |
| `gpt-5.4` | 2.5 | 15 | $2.50 |
| `gpt-5.2` | 1.75 | 14 | $1.75 |
| `gemini-3.8-flash` | 0.75 | 3.75 | $0.75 through December 31, 2026. $1.50 starting January 1, 2027. |
| `gemini-4-argon` | 2 | 10 | $2.00 through November 30, 2026. $4.00 starting December 1, 2026. |
| `gemini-3.6-flash` | 0.75 | 3.75 | $0.75 through December 31, 2026. $1.50 starting January 1, 2027. |
| `gemini-3.5-flash-lite` | 0.3 | 2.5 | $0.30 (text / image / video / audio) |
| `gemini-3.1-pro-preview` | 2 | 12 | $2.00, prompts <= 200k tokens $4.00, prompts > 200k tokens |

Notes on prices:
- **Some Gemini prices are launch prices.** The pricing page says `gemini-4-argon` doubles from
  1 December 2026, and `gemini-3.8-flash` and `gemini-3.6-flash` from 1 January 2027. The baht tables
  use the price in force on the run date; `ttt prices` run after those dates picks up the new price.
- Prices by context length (OpenAI long context, `gemini-3.1-pro-preview` above 200k,
  `claude-haiku-5-5` above 100,000 tokens) are not used: every scenario sends much shorter requests.
  Those numbers are still in the prices file.
- Gemini output includes thinking tokens, as its pricing page says. The scenarios count no thinking
  tokens for any vendor.

### How costs are computed

`baht = tokens × price (dollars per million tokens) ÷ 1,000,000 × baht per dollar`, and
`tokens = characters × measured tokens per 1,000 characters ÷ 1,000`.

- Thai tokens use the model's `target_tokens_per_1k_chars`; English uses `baseline_tokens_per_1k_chars`.
- A model measured on the 100-pair sample uses the token rate of the fully measured model it matched
  (named in the `token_rate_from` field), with its own price.
- "The same content in English" is the number of Thai characters × the English-to-Thai character ratio
  measured on FLORES-200 (131,964 ÷ 126,100). So Thai ÷ English in the table equals that model's premium.
- Open models have no per-token price of their own; the CSV has their token counts only.

### Scenarios (`registry/scenarios.toml`): every size is an **assumption**, not a measurement

| Scenario | Volume | Turns per unit | system prompt | input message | output message | history resent |
|---|---|---:|---:|---:|---:|---|
| `line_oa_chatbot` | 10,000 conversations a month | 6 | 2,000 characters | 60 | 250 | yes |
| `summarize_documents` | 100 documents | 1 | 500 | 20,000 | 1,500 | no |
| `write_content` | 1,000 pieces | 1 | 800 | 300 | 3,000 | no |

No scenario contains real text, only character counts. Change the file and rerun `ttt cost`.

### Result: LINE OA chatbot, 10,000 conversations a month (cheapest first)

| model | token rate from | $ in / out per 1M | Thai tokens in | Thai tokens out | Thai, baht | same content in English, baht | Thai ÷ English |
|---|---|---|---:|---:|---:|---:|---:|
| `gpt-6-luna` | `tiktoken/o200k_base` (sample matched) | 0.1 / 0.5 | 70,845,773 | 6,247,423 | 342.25 | 175.11 | 1.954 |
| `claude-haiku-5-5` | `claude-opus-5-5` (sample matched) | 0.1 / 0.5 | 151,308,064 | 13,342,863 | 730.96 | 273.13 | 2.676 |
| `gemini-3.5-flash-lite` | `typhoon-ai/typhoon2.1-gemma3-12b` (sample matched) | 0.3 / 2.5 | 58,523,303 | 5,160,785 | 1,021.20 | 638.19 | 1.600 |
| `gemini-3.8-flash` | own full run | 0.75 / 3.75 | 58,523,303 | 5,160,785 | 2,120.43 | 1,325.14 | 1.600 |
| `gemini-3.6-flash` | `typhoon-ai/typhoon2.1-gemma3-12b` (sample matched) | 0.75 / 3.75 | 58,523,303 | 5,160,785 | 2,120.43 | 1,325.14 | 1.600 |
| `gpt-6.1-terra` | `tiktoken/o200k_base` (sample matched) | 1 / 5 | 70,845,773 | 6,247,423 | 3,422.53 | 1,751.15 | 1.954 |
| `gemini-4-argon` | own full run | 2 / 10 | 55,432,906 | 4,888,263 | 5,355.89 | 3,526.54 | 1.519 |
| `gemini-3.1-pro-preview` | `typhoon-ai/typhoon2.1-gemma3-12b` (sample matched) | 2 / 12 | 58,523,303 | 5,160,785 | 6,000.53 | 3,749.97 | 1.600 |
| `gpt-6-sol` | `tiktoken/o200k_base` (sample matched) | 2 / 10 | 70,845,773 | 6,247,423 | 6,845.07 | 3,502.30 | 1.954 |
| `gpt-6.1-sol` | `tiktoken/o200k_base` (sample matched) | 2 / 10 | 70,845,773 | 6,247,423 | 6,845.07 | 3,502.30 | 1.954 |
| `gpt-5.2` | `tiktoken/o200k_base` (sample matched) | 1.75 / 14 | 70,845,773 | 6,247,423 | 7,089.08 | 3,627.15 | 1.954 |
| `claude-haiku-4-5-20251001` | own full run | 1 / 5 | 150,790,075 | 13,297,185 | 7,284.61 | 1,882.13 | 3.870 |
| `gpt-5.4` | `tiktoken/o200k_base` (sample matched) | 2.5 / 15 | 70,845,773 | 6,247,423 | 9,079.98 | 4,645.79 | 1.954 |
| `gpt-5.6-sol` | `tiktoken/o200k_base` (sample matched) | 4 / 20 | 70,845,773 | 6,247,423 | 13,690.13 | 7,004.59 | 1.954 |
| `claude-sonnet-5-5` | `claude-opus-5-5` (sample matched) | 2 / 10 | 151,308,064 | 13,342,863 | 14,619.27 | 5,462.63 | 2.676 |
| `gpt-5.5` | own full run | 5 / 30 | 70,845,773 | 6,247,423 | 18,159.95 | 9,291.59 | 1.954 |
| `claude-sonnet-4-6` | `claude-haiku-4-5-20251001` (sample matched) | 3 / 15 | 150,790,075 | 13,297,185 | 21,853.84 | 5,646.40 | 3.870 |
| `claude-opus-5-5` | own full run | 4 / 20 | 151,308,064 | 13,342,863 | 29,238.55 | 10,925.26 | 2.676 |
| `gpt-6-astra` | own full run | 10 / 50 | 70,845,773 | 6,247,423 | 34,225.33 | 17,511.48 | 1.954 |
| `claude-fable-5-2` | `claude-opus-5-5` (sample matched) | 8 / 40 | 151,308,064 | 13,342,863 | 58,477.09 | 21,850.51 | 2.676 |

The other two scenarios are in `results/costs_2026-11-10.md`. The order of models is almost the same in each.

**Token counts and money do not rank the same way:** `claude-haiku-5-5` uses more than twice the Thai
tokens of `gemini-3.5-flash-lite` yet costs less, because its price per token is lower.

### Limits written into the result files as well (`costs_*.md` and `.json`)

1. This is token cost only. It says nothing about answer quality.
2. Token rates were measured on FLORES-200, which is news and encyclopedia style text; chat messages may tokenize differently.
3. Output tokens are assumed to have the same tokens-per-character as input text of that language.
4. Reasoning/thinking tokens, prompt caching, batch discounts, free tiers and long-context prices are not included.
5. Claude token rates come from `count_tokens`, which Anthropic documents as an estimate.
6. Open models have no per-token price of their own.
7. The English column is the same content, not the same number of characters.
8. Scenario sizes are assumptions.

### Summary statements the results support

Each is a ratio of two values from one file; file and field are given.

1. **Tokens, across models.** The same Thai text takes 2.14x the tokens on Claude as on GPT, and 2.59x
   as on Gemini. Source: `summary_2026-11-10_day2b.csv`, field `target_tokens_per_1k_chars`:
   `claude-opus-5-5` 889.5, `tiktoken/o200k_base` (= GPT-5.x, GPT-6) 416.5, `gemini-3.8-flash` 344.1,
   `gemini-4-argon` 325.9 (against Gemini 4 Argon the ratio is 2.73).
2. **Premium, inside one model.** The same content costs 2.68x the tokens in Thai as in English on
   Claude, 1.95x on GPT, 1.52–1.60x on Gemini. Source: `summary_2026-11-10_day2b.csv`, field `premium`
   (CI in `ci95_low`, `ci95_high`).
3. **Baht, same list price, small models.** Same list price ($0.1 / $0.5 per million tokens), but a Thai
   chatbot with 10,000 conversations a month costs 731 baht on Claude Haiku 5.5 and 342 baht on GPT-6
   Luna. Source: `costs_2026-11-10.csv`, scenario `line_oa_chatbot`, field `thai_thb`; prices from
   `prices_2026-11-10.json` (scenario sizes are assumptions in `registry/scenarios.toml`).
4. **Baht, same list price, large models.** Same list price ($4 / $20), same Thai chatbot workload:
   29,239 baht on Claude Opus 5.5, 13,690 baht on GPT-5.6 Sol (2.14x). Source: `costs_2026-11-10.csv`,
   scenario `line_oa_chatbot`, field `thai_thb`.
5. **Baht, cheapest and dearest.** The same Thai chatbot workload costs from 342 baht a month
   (`gpt-6-luna`) to 58,477 baht (`claude-fable-5-2`), a 171x spread. Source: `costs_2026-11-10.csv`,
   scenario `line_oa_chatbot`, field `thai_thb` (minimum and maximum of the 20 priced models). Caution:
   these two models are in different capability classes; most of the spread comes from the list price,
   not the token count. This statement is not used as a headline for that reason.
6. **Claude's newer tokenizer.** It did not make Thai cheaper: 112,169 Thai tokens against 111,785
   before, while English went from 218.9 to 317.6 tokens per 1,000 characters. Source:
   `summary_2026-11-10_day2b.csv`, fields `target_tokens`, `baseline_tokens_per_1k_chars` of
   `claude-opus-5-5` and `claude-haiku-4-5-20251001`.

### Gaps and things to know

- No price was missing: all 20 models measured through an API and still available have a price
  (`gemini-2.5-pro` and `gemini-2.5-flash` were not measured, so no price was fetched).
- The exchange rate is for 9 November 2026, not the day the prices were fetched, because the Bank of
  Thailand had not yet published 10 November. To match the day, `ttt prices` and `ttt cost` must be
  run again after publication (with `--out`/`--label`, because that day's files exist).
- The Bank of Thailand's official API (`gateway.api.bot.or.th`) needs a key, so the code reads the
  public JSON file its web page uses. If the page structure changes, this step stops with a message; it
  does not guess a value.
- The price reader depends on each vendor's page format. If a page changes, that model is recorded as missing.
- At this point `ttt analyze` rewrote `latest.json` whole, so `ttt cost` had to follow an analyze run to
  bring the costs fields back (fixed on day 2b, second part, and day 3c).
- 54 tests pass (new: reading prices from tables, Gemini's dated prices, the Bank of Thailand rate,
  scenario arithmetic, sampled models using the full model's rate, models without a price, more tokens
  yet cheaper).

---

## Day 2b, second part — FLORES-200 against FLORES+

The dataset terms were accepted and the data files could be fetched (the earlier attempt got 403).

- **Source:** <https://huggingface.co/datasets/openlanguagedata/flores_plus>, revision
  `1147e2dc59f37fbb5c22fd8478770de02cd399f9` (version 5.0 according to its CHANGELOG, last modified
  2026-10-25), licence CC BY-SA 4.0. Files `devtest/eng_Latn.jsonl` and `devtest/tha_Thai.jsonl`
  (SHA-256 in `data/source_floresplus.json`).
- **Redistribution terms:** the dataset asks not to be re-hosted where web crawlers can read it and not
  to be used as training data. No FLORES+ sentence is in git (the sentence file, the sample file and
  `data/raw/` are local only, `data/.gitignore`). The terms are recorded in
  `data/source_floresplus.json` and `data/README.md`.
- **Code change (small, layered):** `ttt prepare --dataset floresplus`, `ttt count --dataset floresplus`,
  `load_sentences(root, dataset)`; the dataset name is carried into the `dataset` column and
  `.meta.json`. FLORES+ results live in their own folder, `results/floresplus/`, apart from the core
  set; `ttt compare` is the new module `compare.py`.
- **Sentence pairs:** 1,012 (FLORES+ ids start at 0; 1 was added to match FLORES-200).
- **Sentences compared after the same normalization:** **zero sentences differ from FLORES-200 in
  either language** (English 0, Thai 0, pairs where both differ 0). The normalized sentence files of the
  two sets have the **same SHA-256, byte for byte** (`9df6db4c…`). Before normalization: English 0 lines
  differ, Thai 253 lines differ, and only by the trailing space (after trimming, 0 differ). The sample
  file of differing sentences (`data/spotcheck_floresplus_changes.md`) is therefore empty.
- **Consequence:** the tokenizer input is the same byte for byte, so the token counts must be the same
  by construction. This experiment does not show that the numbers are robust to translation fixes in
  FLORES+, because the Thai–English part of devtest has no change at all between FLORES-200 and
  FLORES+ v5.0.
- **How it was counted:** the 24 local tokenizers (including Llama 3.1) were **really counted again**
  and gave the same result on every sentence. The 6 fully measured API models (`gpt-5.5`, `gpt-6-astra`,
  `gemini-3.8-flash`, `gemini-4-argon`, `claude-opus-5-5`, `claude-haiku-4-5-20251001`) were not called
  again: checkpoints are keyed by the hash of the text, and the text is the same, so the code read that
  day's earlier answers (`api_calls_this_run: 0`, `answers_resumed_from_checkpoint: 4108` per model in the
  `.meta.json` files of `results/floresplus/`). The API numbers for FLORES+ are therefore **not an
  independent second measurement** but a replay of the same answers on text proven identical. The
  overhead was not tested again (done on FLORES-200).
- **Comparison table** `results/comparison_flores200_vs_floresplus_2026-11-10.{csv,json,md}`: the 30
  tokenizers measured in full on both sets (24 local + 6 API) **count the same on every sentence,
  30/30**. The FLORES+ premium and tokens per 1,000 Thai characters are inside the FLORES-200 95% CI for
  all 30/30 (in fact equal in every digit). Example: `claude-opus-5-5` premium 2.676 (2.645–2.709),
  equal; Thai 889.5 tokens per 1,000 characters (886.4–892.6), equal. The CI of tokens per 1,000
  characters is computed in this comparison file with the same bootstrap (the main summary has no such column).
- `results/latest.json` still points at the FLORES-200 set and costs (untouched).
- **Fix of the day-3 gap:** `ttt analyze` keeps the `prices` and `costs_*` fields of `latest.json` when
  it rewrites it (the costs fields still refer to the summary used when they were computed, which is
  recorded in `costs_*.json`).
- 60 tests pass (new: reading jsonl, comparison table with same / different / unmatched rows,
  latest.json, counting a second dataset).
- **What this leaves open:** independent evidence for the API numbers would need FLORES+ text that
  differs, and there is none (the whole set is identical), so devtest Thai–English adds nothing more.
  Robustness to other text would need the `dev` split of FLORES+ or real-world text.

---

## Day 3b — Claude `count_tokens` against billed usage

Run date: 2026-11-10 (UTC). **The only stage that sent paid requests**, under a hard cap of 0.10 US
dollars. No published number needed correcting.

Commands: `ttt billing-check --dry-run` (prints the estimate, sends nothing billable), then
`ttt billing-check`.

### Method

- The **same request** was sent two ways: `count_tokens` (free) and the real Messages API with
  `max_tokens=1` (billed). No system prompt, no tools, no `cache_control`, no thinking setting (each
  model's default). `count_tokens` was then compared with `usage.input_tokens`, text by text.
- Sample with a fixed seed (20261110) from FLORES-200: `claude-haiku-5-5` 20 sentence pairs (40 texts),
  `claude-haiku-4-5-20251001` 20 pairs (40 texts), `claude-opus-5-5` the first 5 pairs of the same set
  (10 texts); 90 billable requests in total.
- Cost guard: the cost was estimated from already measured tokens × the prices in
  `results/prices_2026-11-10.json` before sending, and the run stops if it exceeds the cap; the SDK's
  automatic retry was switched off; each answer was written to a checkpoint at once, and a request that
  succeeded is never sent again; retry only after a rate-limit rejection, which is not billed.

### Cost

| | US dollars |
|---|---:|
| Cap | 0.10 |
| Estimate before sending | 0.007477 |
| **Actual** (usage of every answer × list price) | **0.007477** |

90 billable requests: 90 succeeded, 0 failed, none sent twice. "Actual" is computed from the `usage`
the API returned; the invoice itself is only visible in the vendor's console.

### Result

| Model | Texts | billed input against `count_tokens` | billed input minus published content tokens | overhead subtracted in the day-2 results | cache tokens | output tokens | US dollars |
|---|---:|---|---|---:|---|---:|---:|
| `claude-haiku-5-5` | 40 | equal for every text | 8 for every text | 8 | none | 1 | 0.000358 |
| `claude-haiku-4-5-20251001` | 40 | equal for every text | 7 for every text | 7 | none | 1 | 0.003295 |
| `claude-opus-5-5` | 10 | equal for every text | 8 for every text | 8 | none | 1 | 0.003824 |

- **`usage.input_tokens` equals `count_tokens` on all 90 texts.** Not one differs by a single token.
- **The subtracted overhead (8 and 7) is what billing shows:** billed input minus the published content
  tokens is 8 (current tokenizer generation) and 7 (older one) for every text.
- **`claude-opus-5-5` and `claude-haiku-5-5` are billed the same input on the same text**, all 10 texts
  (0 differ). This supports using one token rate for both, as the baht tables of day 3 do.
- The cache fields of `usage` are all 0; `output_tokens` = 1 and `thinking_tokens` = 0 in every answer;
  `service_tier` = standard.

### What it means for the results

- For the kind of request tested (one message, no system prompt), `count_tokens` is not merely an
  estimate: it equals the billed amount every time in this sample. The Claude tokens per 1,000
  characters and baht tables need no correction.
- **The overhead of 8/7 tokens per request is really billed**; it is not unbilled system tokens. The
  published results (content tokens) leave it out, so the scenarios are slightly below a real bill:
  8 tokens per request, against requests of several thousand tokens in the chatbot scenario. This is
  listed among the limits; no number was changed.
- Scope of the evidence: 90 short texts (one sentence each), a single user message. Not tested: system
  prompts, multi-turn conversations, tools, caching, long texts. Fable 5.2 and Sonnet 5.5 were not
  tested with real requests (their `count_tokens` matches Opus 5.5 on the 100-pair sample of day 2).

### Files

- `results/billing_check_2026-11-10.json` (every text: `count_tokens`, the full `usage`, no sentence
  text) and `.md`; `results/latest.json` has a `billing_check` field.
- `src/thai_token_tax/billing.py`, `tests/test_billing.py`. 68 tests pass in total (new: classifying the
  result as equal / constant difference / irregular difference, estimating the cost and stopping above
  the cap, dry-run sends nothing billable, a billable request is sent once even when rerun).
- The checkpoint of billed answers is `.cache/billing/answers.jsonl` (outside git). Rerunning
  `ttt billing-check` is not billed again while that file exists.

---

## Day 3c — Meta's Llama 3.3

- `meta-llama/Llama-3.3-70B-Instruct` became accessible. Measured as an add-on set like Llama 3.1:
  `ttt count --source open --model meta-llama/Llama-3.3-70B-Instruct --label llama33` gave
  `results/counts_2026-11-10_open-llama33.csv` (2,024 rows) + `.meta.json` +
  `verification_2026-11-10_open-llama33.json`. Repository revision pinned in the registry:
  `6f6073b423013f6a7d4d9f39144961bfbfbc386b`.
- Result on 1,012 sentence pairs: premium **2.185 (2.159–2.211)**, 470.7 tokens per 1,000 Thai
  characters. Verified: decode returns 1,012/1,012 in both languages, no `<unk>`, and `transformers` agrees.
- **Llama 3.3 counts the same as Llama 3.1 on every sentence in both languages** (0 of 2,024 values
  differ), and the same as `typhoon-ai/llama3.1-typhoon2-8b-instruct` and
  `aisingapore/Llama-SEA-LION-v3.5-8B-R`. The `tokenizer.json` files of 3.3 and 3.1 have different
  SHA-256 values (not the same bytes) but give the same token counts on this data.
- Summary and costs rerun: `results/summary_2026-11-10_day2c.*` (45 rows) and
  `results/costs_2026-11-10_day2c.*` (135 rows = 3 scenarios × 45 models). The cost rows of the earlier
  models are byte-identical to `costs_2026-11-10.csv`; the only difference is the added Llama 3.3 rows
  (an open model, token counts only). `results/latest.json` points at the day2c set.
- **Bug fixed:** `ttt analyze` had dropped the `billing_check` field from `latest.json` (the earlier fix
  kept only `prices`/`costs_*`). It now keeps every field analyze does not own; a test covers it, and
  the `billing_check` field was restored (pointing at the same file, `billing_check_2026-11-10.json`).
- Still blocked (HTTP 403): `meta-llama/Llama-4-Scout-17B-16E-Instruct`, `google/gemma-3-27b-it`.
- This stage was interrupted and resumed. Before anything was used, every result file was checked: row
  counts complete, the hashes in `.meta.json`/summary/costs equal the real files, every file
  `latest.json` points at exists. Nothing had to be rerun. 68 tests pass.

---

## Day 4 — the site

Run date: 2026-11-10 (UTC). No API key, nothing measured, no new file in `results/`.

View locally: `python -m http.server 8765` in the repository root, then <http://localhost:8765/site/>.
It needs a web server (the page fetches `data.json`, so `file://` does not work). `?lang=th` /
`?lang=en` forces a language.

### What was built

| File | What it does |
|---|---|
| `src/thai_token_tax/site.py`, command `ttt site` | Writes `site/data.json` from `results/latest.json` and the files it points to (summary, costs, prices, billing check, blocked lists), plus `data/source_floresplus.json`, `registry/scenarios.toml` and `registry/display.toml` |
| `site/index.html` | One page, inline CSS and JS. No framework, CDN, build step, tracker or web font; no external URL is loaded. Relative paths only, so it works under a sub-path |
| `site/data.json` | Everything the page shows (generated, committed, no timestamp) |
| `site/config.json` | `repo_url`, `null` at this point; the repository link in the footer appears once it is set |
| `registry/display.toml` | Short group labels, display names, the two same-list-price pairs, which models the headline uses. No measured number |
| `registry/scenarios.toml` | Thai names and units added (numbers unchanged) |
| `tests/test_site.py` | 11 tests |
| `.github/workflows/pages.yml` | Publishes `site/` (see below) |

### No number is typed into the page

- All text is a template with placeholders such as `{ratio_price}`; headline, charts, table, dates,
  model counts and limits are filled from `data.json` on load.
- `test_the_page_contains_no_measured_number` searches `index.html` for the measured values (headline
  ratios, tokens per 1,000 characters and premium of every group, baht totals, exchange rate, sentence
  count) and must find none.
- Tests rebuild `data.json` and compare it with the committed file, and compare every group, price,
  cost row and the exchange rate with the result files read directly.
- `ttt site` stops if the inputs do not belong together: costs not computed from the current summary or
  prices, a scenario edited after costing, a "same list price" pair whose prices now differ, a group
  label naming a model that did not give identical counts (one test per case).
- Three side notes are shown only while the data still supports them (checked in `ttt site`): "more
  tokens yet cheaper", "two Claude tokenizer generations", and the group the Thai models share.

### Page content, top to bottom

1. Headline (baht-led in Thai, token-led in English), with the baht figures of the first same-price
   pair and a four-bar token chart on the first screen, then "cost, not answer quality", the size of the
   measurement, data date and price date.
2. Lead chart: tokens per 1,000 Thai characters, one bar per tokenizer (13); a bar expands to list its
   models and how each was measured.
3. Same list price, different bill: the two pairs, in baht for the chatbot scenario.
4. Calculator: preset, editable assumptions, model picker; baht for Thai and for the same content in
   English; a ranked list of all priced models.
5. Thai against English inside each model (premium with 95% CI), and why it cannot be compared across models.
6. Full table, 45 models, sortable; shows identical-count groups and which rows were measured on a sample.
7. Method (6 points) and limits: everything in `costs_*.md`, plus FLORES translation errors, Gemini
   price end dates (quoted from the pricing page text), the billed-against-counted check and its scope,
   and request overhead tokens that are billed but not in these numbers.
8. Not measured: 5 models with reasons.
9. Footer: data, price and exchange-rate dates; licences; link to `data.json`.

Language switch at the top (default from the browser, remembered locally). Light and dark follow the system.

### Charts

- Ranked horizontal bars, with the value printed at the end of every bar (readable without hover); the
  full table is the companion view.
- One blue for tokenizers behind a per-token API, gray for tokenizers used only by open models; every
  bar also carries a text tag ("API" / "open model"), so identity never depends on colour alone.
- Colours were checked with a palette validator script, not by eye. Blue (`#2a78d6` light, `#3987e5`
  dark) passes every check in both modes. Blue against gray: ΔE 15.9 under colour-vision deficiency,
  17.8 (light) / 17.0 (dark) for normal vision. The gray fails the chroma floor on purpose: it is the
  de-emphasis colour.
- Contrast against the page background (light / dark): blue bar 4.30 / 4.79, gray bar 3.50 / 4.85,
  secondary text 7.73 / 9.72, muted text 5.28 / 6.74, links 6.46 / 6.96.

### The calculator matches `pricing.py`

1. `test_the_page_formula_gives_the_published_cost_table` cuts the formula out of the page (between the
   `CALC-START` / `CALC-END` markers), runs it with Node for every preset × every priced model (60
   combinations) and compares with `results/costs_2026-11-10_day2c.csv`: Thai baht, English baht, Thai
   input and output tokens all match. The test is skipped where Node is not installed.
2. The page checks itself on every load: 120 values (60 combinations × Thai/English) against
   `data.json`. In the browser: 120 of 120 match. A mismatch shows a warning on the page.
3. By hand in the browser: changing preset and model gives the published amounts, doubling the volume
   doubles the total, empty or negative input does not break the page.

### Checked in a real browser

Served locally under `/site/` (a sub-path), Chrome:

| Viewport | Mode | Language | Result |
|---|---|---|---|
| 375 × 812 | light | Thai | no horizontal page scroll (content width 375 = viewport 375) |
| 375 × 812 | dark | English | same |
| 1280 × 900 | light | English | full table fits the width |
| 1280 × 900 | dark | Thai | same |

- No console error or warning in any combination.
- Working: language switch (stored; calculator state kept), expanding a bar, table sorting, calculator.
- On a phone the full table scrolls sideways inside its own box; the page does not.
- Fixed during the check: baht value wrapping in the pair cards, the API tag making rows too tall, the
  model-name column collapsing in the table, the calculator form too long on a phone.
- A first-screen and a full-page screenshot of each combination were saved under `.cache/screenshots/`
  (not in git).

### Review of the first screen

The first screen was read as two sceptical readers would: a Thai developer who pays API bills, and
someone who skims for 30 seconds. Changed because of it:

| What failed | Change |
|---|---|
| The Thai headline is about money but the first screen only had a token chart ("which model, how much?") | Two figures under the headline: the baht totals of the first same-price pair, with model names, scenario and list price; the token chart follows as "the cause". English swaps the order because its headline is about tokens |
| Nothing said what the page is | A line above the headline: "Benchmark: what Thai text costs on AI models" |
| No sense of scale or where the numbers come from | Trust lines give the number of models, tokenizers, sentence pairs and the dates, and add "Every number on this page is generated from the measurement files · Claude token counts were checked against billed usage" |
| First-screen chart rows too tall; the "not quality" line fell below the fold | One-line rows with short names (Claude 5.5, GPT-5.x / 6, Gemini 3.x, Gemini 4) |
| "Fewer is cheaper" is not always true (the page itself shows Haiku 5.5 against Gemini 3.5 Flash-Lite) | "At the same price per token, fewer costs less" |
| The top bar of the lead chart is the older GPT encoding; a skimmer could read it as "GPT is worst" | Label changed to "GPT-4, GPT-3.5 (older generation)"; order still follows the values |
| Whole-number values showed GPT as 416, not the published 416.5 | One decimal everywhere, as in the result tables |
| On a phone the main number column of the table was off-screen | Moved next to the model name |

### GitHub Pages

- Official documentation read on 2026-11-10:
  - <https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages>
  - <https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site>
- A branch source can only publish `/` or `/docs`, so `site/` needs a workflow.
- `.github/workflows/pages.yml` uses the actions from the documentation (`actions/checkout@v6`,
  `configure-pages@v5`, `upload-pages-artifact@v4` with `path: site`, `deploy-pages@v4`), permissions
  `pages: write` and `id-token: write`, environment `github-pages`.
- **Manual only** (`workflow_dispatch`), no push trigger. Publishing takes two steps: set
  Settings > Pages > Source to "GitHub Actions", then run the workflow.
- The documentation warns that a Pages site is public even when the repository is private.
- `ci.yml` uses `actions/checkout@v6` too. Neither workflow had run on GitHub.

### Notes

1. An earlier draft of the headline text gave 417 for GPT. **The measured value is 416.49** (416 as a
   whole number, 416.5 with one decimal). The page shows 416.5.
2. The phrase "almost 1 token per character" is not used on the page: it is an interpretation that
   would be wrong if the number moved. The page shows 889.5 per 1,000 characters.
3. The page reads `site/data.json`, not `results/latest.json` directly.
4. The older GPT encoding (`cl100k_base`) bar is drawn as "API" because its family is OpenAI, but it was
   measured with `tiktoken` only and has no price row.
5. Short names on the first screen and the group labels in `registry/display.toml` are wording, not measurements.
6. Statements about Thai models and vendors are limited to numbers and "inherits the base model's tokenizer".
7. Known limits of the page: it needs JavaScript; tooltips are mouse/keyboard only (every value is also printed).

79 tests pass, lint clean.

---

## Day 5 — README, methodology, licences

Run date: 2026-11-10 (UTC). No API key, nothing measured, no file in `results/` changed.

### What was added

| File | What it is |
|---|---|
| `src/thai_token_tax/docs.py`, command `ttt docs` | Fills the templates from the result files and writes the documents |
| `templates/readme.en.md`, `readme.th.md`, `methodology.en.md` | The wording, with `{{placeholders}}`. These are edited, not the outputs |
| `README.md`, `README.th.md`, `docs/methodology.md` | Generated. First screen of each README: the finding, a four-row table with text bars, three commands |
| `LICENSE` | MIT, "Copyright (c) 2026 Thai Token Tax authors" |
| `LICENSE-DATA` | A scope notice (what is CC BY 4.0, what is MIT, FLORES-200 attribution CC BY-SA 4.0) followed by the official CC BY 4.0 text |
| `CITATION.cff` | Version 0.1.0; author, repository address and release date are marked TODO |
| `CHANGELOG.md` | 0.1.0 (unreleased) |
| `tests/test_docs.py` | 10 tests |
| `ARCHITECTURE.md` | Brought in line with the code (below) |
| `registry/display.toml` `[licences]`, `site.py`, `site/index.html`, `site/data.json` | Licence names reach the site footer through `data.json`; none is written in the page |
| `pyproject.toml` | `readme`, `license = "MIT"`, `license-files` |

### How numbers get into the documents

- Each document is a whole-file template. Numbers also appear inside sentences (the headline, the
  limits), so every number, date, file name and table is a placeholder, including those in prose.
- Values come from `site.build()` (the same checked data as the site) plus the count metadata,
  verification files, `data/*.json`, the FLORES+ comparison and `site/config.json`.
- **Statements made in words are guarded.** Seven sentences are true only while the results say so (for
  example "billed input tokens equalled `count_tokens`", "FLORES+ is identical after normalization",
  "the overhead is constant", "a model with more tokens is cheaper"). If a rerun makes one false,
  `ttt docs` stops and writes nothing; the wording has to be changed by a person.
- The repository address has one source: `repo_url` in `site/config.json`. While it is `null`, the
  clone command shows `REPO_URL` and the README says it is a placeholder.
- Tests: the committed documents equal a fresh render; no placeholder is left; **no measured number is
  typed in a template**; the headline ratios and rates are recomputed straight from the per-sentence
  count CSVs (not through the summary) and must appear in the three documents; the overhead and billing
  tables equal the verification and billing files; an unknown placeholder stops the build; a false
  claim stops the build; both READMEs carry the same three commands; licence files, `display.toml`,
  package version, `CITATION.cff` and `CHANGELOG.md` agree.

### Licence texts

- `LICENSE-DATA` contains the official legal text fetched on 2026-11-10 from
  <https://creativecommons.org/licenses/by/4.0/legalcode.txt> (18,657 bytes, SHA-256
  `9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411`), unchanged, after the scope notice.
- The scope notice is not legal advice. The result files hold sentence numbers and token counts, no
  FLORES text.

### `ARCHITECTURE.md` brought in line with the code

- Pipeline diagram: prices and cost added; `site` writes `site/data.json`, `docs` writes the documents;
  `compare` and `billing-check` named.
- Layout: `registry/pricing.toml`, `scenarios.toml`, `display.toml`; `compare.py`, `billing.py`,
  `site.py`, `docs.py`; `templates/`; `CHANGELOG.md`; `pages.yml`; the full command list.
- Results contract: labelled add-on sets, `sample_of`, prices and costs files; the site reads
  `site/data.json`, not `results/latest.json`.

### Fresh-clone check (run twice, same outcome)

Cloned into `.cache/fresh-clone`, new virtual environment (Python 3.12.10), no `ANTHROPIC_API_KEY`,
`GEMINI_API_KEY`, `OPENAI_API_KEY` or `HF_TOKEN`, and `HF_HOME` pointed at an empty folder so that no
saved Hugging Face login could be used.

| Step | Result |
|---|---|
| `git clone` | 118 files |
| `pip install -e .` (README command 2) | exit 0 |
| `ttt all --out rerun` (README command 3) | exit 0 in 3 min 17 s |
| Local tokenizers | 23 measured; 5 blocked: four gated repositories (HTTP 401 without a token) and `SEA-LION-v1-7B` (no `tokenizer.json`) |
| API sources | Not a crash: openai 9, gemini 7, anthropic 6 models reported `BLOCKED … <NAME>_API_KEY is not set`; each source writes a `.blocked.json` and no result set |
| Rerun counts against `results/counts_2026-11-10_open.csv` | 46,552 rows, 0 differ (every column except the date) |
| Rerun summary against the published summary | 23 rows, 0 differ (tokens, rates, premium, CI) |
| `pip install -e ".[dev]"`, `pytest -q`, `ruff check .` | 89 passed; lint clean |
| `ttt site`, `ttt docs` in the clone | `site/data.json` and the three documents unchanged |

The clone command itself could only be tested with a local path, because no repository address existed.

### Found along the way

1. **`ttt all` leaves two tracked files modified** in a clone: `ttt prepare` rewrites `data/source.json`
   and `data/normalization_log.json`. Only timestamps and the word "downloaded" change; all hashes are
   the same. The README says so.
2. **A disagreement that was only in the day-1 notes is now in the methodology:** for
   `typhoon-ai/typhoon-7b` and `openthaigpt/openthaigpt-1.0.0-7b-chat` the repository's SentencePiece
   file counts differently from its `tokenizer.json` (section 5 there, with the numbers). Published
   values use `tokenizer.json`, like every other open model.
3. Adding a language: `prepare`, `count`, `verify` and `analyze` take every language in the registry,
   but only Thai has been run, and the cost tables, the site and the documents assume one target language.
4. The README link to the web page points at the `site/` folder until a page address exists; there is
   no CI badge for the same reason.

89 tests pass, lint clean.

---

## Day 6 — articles, post drafts, share cards

Run date: 2026-11-10 (UTC). No API key, nothing measured, no file in `results/` changed.

### What was added

| File | What it is |
|---|---|
| `blog/thai-token-tax.th.md` | Article for Thai developers and business owners: baht first, why, what to do, the two Claude tokenizer generations, open and Thai models, limits, how to rerun |
| `blog/thai-token-tax.en.md` | Article for an international technical reader: tokens first, why the within-model premium misleads across models, why the numbers can be checked, limits, what is next |
| `blog/posts.md` | Drafts: X thread in Thai and in English (6 posts each), LinkedIn in English and Thai, a post for Thai developer / AI Facebook groups, Show HN title and first comment |
| `templates/blog.th.md`, `blog.en.md`, `posts.md` | The wording. All are generated by `ttt docs` with the same guards as the README |
| `src/thai_token_tax/card.py`, command `ttt card [--png]` | Share cards from `site/data.json` |
| `site/card.th.svg`, `card.en.svg`, `card.th.png`, `card.en.png`, `cards.json` | The cards, 1080 × 1080 |
| `site/index.html`, `site.py` | Link-preview (Open Graph / Twitter) tags, written by `ttt site` |
| `site/config.json` | New keys `site_url` (null) and `og_lang` ("th") |
| `tests/test_card.py`, additions to `test_docs.py` and `test_site.py` | 96 tests in total |

### Articles and posts

- Each article is its own piece, not a translation. In both, the part before the first heading holds
  the finding, the size of the measurement and "cost, not answer quality" (a test checks this).
- Length: the English article has 860 words of prose (tables and code blocks not counted; a test keeps
  it between 700 and 1,100). No Thai word counter was available, so the Thai article is reported in
  characters: 4,363 without spaces, tables and code.
- Posts: every X post is within 280 characters as X counts them (Thai thread 209 to 220, English thread
  190 to 252; a link counts as 23). The Show HN title is 73 characters. Only `#ภาษีภาษา` and
  `#ThaiTokenTax` are used.
- A post draft uses Thai and English values in one file: `ttt docs` gives every template the other
  language's values as `{{th_name}}` / `{{en_name}}`.
- Until `site_url` and `repo_url` are set in `site/config.json`, links show as `SITE_URL` and `REPO_URL`.

### Share cards

- `ttt card` writes the two SVG files from `site/data.json`: project name, headline, two figures (Thai
  card: the two baht amounts at the same list price; English card: the two token ratios), the four-bar
  chart with values printed, "cost, not answer quality", data date, price date, dataset size. Same
  colours and font stack as the site's light theme.
- `ttt card --png` renders the PNG files with an installed Chrome or Edge in headless mode (here:
  Chrome). It is not a package dependency. Fonts are the machine's system fonts, so a PNG made on
  another operating system will look slightly different.
- A PNG is a picture of numbers and can go stale. `site/cards.json` records the SHA-256 of the SVG each
  PNG was made from; a test fails if they differ.
- Both PNG files were inspected at full size. One fix: the last line of the English card ran past the
  right edge and was shortened. Text sizes: headline 60 px, figures 72 px, labels 30 to 34 px, the last
  line 26 px (at a 360 px wide phone display that line is about 9 px).
- The four short names (Claude 5.5, GPT-5.x / 6, Gemini 3.x, Gemini 4) moved from the page's text into
  `registry/display.toml`, so the site and the cards share them.

### Link previews

- A preview needs the absolute address of its image. `ttt site` writes the tags between two markers in
  `site/index.html` only when `site_url` is set; while it is null the block is empty.
- `og_lang` in `site/config.json` picks the wording and the card ("th" by default).
- **Known weakness:** the cards are square, which suits an image attached to a post. Link previews on X,
  Facebook and LinkedIn are usually cropped to about 1.91:1, which would cut the top and bottom of a
  square card. `twitter:card` is therefore `summary` (a small square thumbnail, not cropped). A
  1200 × 630 variant for link previews would fix this; it has not been built.

### Rehearsal of a release in a scratch clone

Run in `.cache/launch-rehearsal` (outside git), not in the working repository:

| Step | Result |
|---|---|
| Set `repo_url` and `site_url`, then `ttt site && ttt docs && ttt card --png` | exit 0; link-preview tags written with absolute addresses; clone command and page link filled in the READMEs, articles and posts |
| `pytest` after that | 96 passed |
| `ttt prices`, `ttt cost`, then site, docs, card | exit 0; 20 prices, 0 missing |
| `pytest` after that | 96 passed |

- **Bug found and fixed:** `ttt site` used to stop when the billing check pointed at an older prices
  file, so a later `ttt prices` would have blocked the site. The guard was removed (what the billing
  check found does not depend on a price), and a test covers the price-refresh flow offline.
- A test assumed the README shows `REPO_URL`; it now follows `site/config.json`, so the tests stay green
  once the addresses are set.
- The published prices file has the same UTC date as the rehearsal, and result files are never
  overwritten, so the rehearsal moved the old file aside inside the scratch clone and used
  `ttt cost --label rehearsal`. On a later date the commands work as written.

### Found along the way

1. **The Bank of Thailand rate has moved on.** The published set uses 33.527 baht per US dollar, the
   rate for 9 November 2026, which was the newest one when prices were fetched at 09:25 UTC on
   10 November. The rehearsal's fetch at 17:25 UTC got 33.392 for 10 November. All 20 model prices were
   unchanged (Google's page changed somewhere else: its hash differs, no price row does). With the
   newer rate the headline pair would read 29,121 and 13,635 baht instead of 29,239 and 13,690; the
   ratio is the same. These rehearsal numbers come from the scratch clone and are not in any committed
   result file. **The published set was not changed**; the next `ttt prices` and `ttt cost` run brings
   prices and rate to the same date.

96 tests pass, lint clean.

---

## Day 6b — housekeeping

Run date: 2026-11-10 (UTC). No API key, nothing measured, no file in `results/` changed.

- `ttt docs` now writes six documents: the two README files, `docs/methodology.md`, the two articles
  and the post drafts.
- This notebook was rewritten in English as described at the top. A script compared every number, hash
  and link of the previous version with this one; what was not carried over is administrative, not a
  measurement.
- `ttt site`, `ttt docs` and `ttt card --png` were run again; 96 tests pass, lint clean.
