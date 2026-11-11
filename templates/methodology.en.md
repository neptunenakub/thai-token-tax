# Methodology

How Thai Token Tax was measured, written so the weak points are easy to find. Every number in this
file is filled in from the result files by `ttt docs`; the sections name the file each one comes from.

Current result set: measured {{date_data}} (UTC), prices fetched {{date_prices}}, package version
{{version}}.

## 1. What is measured

The number of tokens that each model's own tokenizer produces for the same content written in Thai and
in English, and what that costs at official list prices.

It is **not** a measure of answer quality, speed or value. A model that uses more tokens for Thai may
still answer Thai better. Nothing here ranks models; it reports what the same text costs to send.

## 2. Data and provenance

- **Dataset:** FLORES-200, `devtest` split, `eng_Latn` and `tha_Thai`: {{pairs}} sentences translated
  into both languages, so the content is the same on both sides. Thai side {{thai_chars}} characters,
  English side {{english_chars}} characters (a character is a Unicode code point after normalization).
- **Release used:** the original Meta release, <{{flores_url}}> (SHA-256 `{{flores_tarball_sha256}}`).
  `ttt prepare` downloads it, checks that hash, extracts the two files and checks that the result has
  the hash recorded in `data/source.json` (`{{tsv_sha256}}`). `ttt count` refuses to run on any other file.
- **Not in git:** the sentences themselves. The maintained successor of the dataset asks that the text
  not be re-hosted where crawlers can collect it, so this repository ships the recipe and the hashes
  instead. Result files contain sentence ids and counts only.
- **Licence:** CC BY-SA 4.0 (Meta, NLLB Team). See `data/README.md`.
- **Never edited:** no sentence was changed, removed or re-translated. FLORES contains translations
  whose meaning does not match the source (for example sentence 179 of `devtest`, noted in `LOG.md` on
  day 1). They stay in.

## 3. Normalization

Applied to both languages before counting (`src/thai_token_tax/data.py`, Unicode data version
{{unicode_version}}):

{{list_normalization_rules}}

What it changed (`data/normalization_log.json`, which also lists the sentence ids):

{{table_normalization}}

Zero-width spaces are common in Thai web text and some tokenizers spend a token on each. Removing them
makes the Thai counts slightly lower than on raw text, never higher.

## 4. Counting: "content tokens"

Every count in the results is the number of tokens of the sentence text alone: no beginning or end
tokens, no chat template, no request framing. That is the part of a bill that grows with the text.

### Local tokenizers

- OpenAI encodings: `tiktoken`, `encode(text, disallowed_special=())`.
- Open models: the repository's `tokenizer.json`, loaded with the Hugging Face `tokenizers` library,
  `add_special_tokens=False`, truncation and padding switched off. Only the tokenizer file is downloaded,
  never model weights. The registry pins the repository commit, and the metadata file records the commit
  and the SHA-256 of the `tokenizer.json` that was used.
- Library versions of this run: {{libraries}}, Python {{python}} (pinned in `pyproject.toml`).

### API token-counting endpoints, and the overhead

Claude, GPT and Gemini are counted through the vendors' official token-counting endpoints: one request
per sentence, the sentence as a single user message, nothing else in the request. These endpoints
count the whole request, so the answer includes a few tokens of message framing. The counter measures
that overhead as the raw count of the message `"a"` minus one, subtracts it from every sentence, and
records it.

Subtracting a constant is only valid if the overhead really is constant. `ttt verify` tests that for
every fully measured API model instead of assuming it:

- **Length:** messages of one to several hundred repetitions of a one-token word. Raw count minus the
  number of words must equal the overhead every time.
- **Content:** real sentences X, Y, Z from both languages sent as one three-message conversation. Its
  raw count minus the raw counts of X, Y and Z sent alone must be the same number for every triple. An
  overhead that depended on script, language or length would make it vary.
- **Repeat:** sentences sent a second time must get the same answer.
- **Against a local tokenizer**, where one exists: the API count minus the overhead must equal the
  `tiktoken` count for every sentence in both languages.

{{table_overheads}}

Source: the `verification_<date>_<source>.json` files named in `results/latest.json`.

Requests were rate-limited (Anthropic: {{rate_limit_anthropic}} per minute) with retry and backoff, and
every answer was written to a checkpoint so that an interrupted run resumes without asking twice.
These endpoints only count; no model was asked to generate anything for the measurements (the
billing check in section 10 is the one exception).

### Equality sampling

Vendors do not say which models share a tokenizer. Rather than send thousands of identical requests,
one model per suspected tokenizer generation was measured in full ({{n_full}} models and encodings
in total, local and API), and {{n_sampled}} further API models were counted on a fixed random sample of
{{sample_size}} sentence pairs (seed {{sample_seed}}, the same sample for every model, drawn before any
counting).

A sampled model is assigned to a fully measured model only if its counts are **identical on every
sampled sentence in both languages**. One mismatch means it is a different tokenizer and must be
measured in full; that happened once and the model was then measured in full (see `LOG.md`, day 2).

{{table_samples}}

What this does and does not show: identical counts on the sample make a different tokenizer very
unlikely, but it is evidence, not a statement from the vendor. A sampled model has no premium or
confidence interval of its own; tables give it the values of the model it matched and mark it as
sampled.

The same rule groups fully measured models: two models are reported as one tokenizer only if their
counts are identical on all {{pairs}} sentence pairs in both languages. That is how the {{n_models}}
measured models reduce to {{n_groups}} distinct tokenizers.

### Models that could not be measured

{{table_blocked}}

A blocked model has no number anywhere in the results. Mirrors, unofficial copies and estimates were
not used.

## 5. Independent recount of the local tokenizers

`ttt verify` recounts each local tokenizer in a second way and reports any disagreement instead of
hiding it. For this result set ({{open_checked}} tokenizers, both languages):

- Recount from scratch against the published counts: {{open_recount_mismatch}} sentences differ.
- `decode(encode(text)) == text`: holds for at least {{open_roundtrip_min}} of {{pairs}} sentences in
  every tokenizer and language (nothing in the text is dropped by the tokenizer).
- Unknown (`<unk>`) tokens, which would hide real cost: {{open_unk}}.
- `transformers.AutoTokenizer`, the path most users take, on the {{open_transformers_checked}} Hugging
  Face tokenizers: {{open_transformers_mismatch}} sentences differ.
- **One real disagreement.** {{sp_checked}} repositories also ship a SentencePiece file
  (`tokenizer.model`) next to `tokenizer.json`. Counting with the `sentencepiece` library agrees for all
  but {{sp_differ}}:

{{table_sentencepiece}}

  The published numbers use `tokenizer.json` for every open model: it is the same method throughout and
  it is what `transformers` gives. A runtime that loads the SentencePiece file directly would get the
  other count for these models. No API model is affected.

## 6. The two reported numbers, and why both

- **Tokens per 1,000 Thai characters** = 1,000 × total Thai tokens ÷ total Thai characters. It is an
  absolute rate, so it can be compared across models, and it is what gets multiplied by a price.
- **Premium** = total Thai tokens ÷ total English tokens over the same sentence pairs. It answers "in
  this model, how much more does Thai cost than the same content in English".

The premium must not be used to compare models: its denominator is each model's own English rate, and
those differ. From {{gen_old}} to {{gen_new}} the premium fell from {{gen_old_premium}} to
{{gen_new_premium}}, which reads like an improvement for Thai. The absolute rates show otherwise: Thai
went from {{gen_old_thai}} to {{gen_new_thai}} tokens per 1,000 characters, English from
{{gen_old_english}} to {{gen_new_english}}. English became more expensive; Thai did not become cheaper.

Both are ratios of sums over the whole set, not averages of per-sentence ratios, so long sentences
weigh more, as they do on a bill.

The headline compares {{claude_1k}} (Claude), {{gpt_1k}} (GPT), {{gemini_1k}} (Gemini 3.x) and
{{gemini_other_1k}} (Gemini 4) tokens per 1,000 Thai characters: ratios of {{ratio_gpt}} and
{{ratio_gemini}}.

## 7. Confidence intervals

The {{ci_level}}% interval of each premium is a {{ci_method}}: {{ci_resamples}} resamples, seed
{{ci_seed}}, the same resamples for every tokenizer. Sentence pairs are resampled together, so the Thai
and English side of one sentence never separate.

What the interval covers: the uncertainty from having these {{pairs}} sentences rather than another
sample of the same kind of text. What it does not cover: a different kind of text (chat, code, product
names), which is a question of bias, not of sampling noise. The tokenizers themselves are deterministic;
there is no measurement noise to average out.

Example: Claude {{claude_premium}}, GPT {{gpt_premium}}.

## 8. Prices and exchange rate

- Prices are read by `ttt prices` from the vendors' official pricing pages on the day of the run and
  saved with the page hash and the exact cell text in `results/{{prices_json}}`. No price is typed by
  hand; `registry/pricing.toml` only says which row of which page belongs to which model.
- Tier: the standard list price for text. Not batch, not cached, the shortest-context tier, the price
  in force on the fetch date.

{{table_price_sources}}

- Exchange rate: {{rate}} baht per US dollar, the {{rate_what}}, for {{date_rate}}, read from the Bank
  of Thailand (<{{rate_page}}>) and saved in the same file.
- Prices move. On the fetch date Google's page already announced an end date for the current price of:

{{list_price_end_dates}}

## 9. From tokens to baht: scenarios are assumptions

```
tokens = characters × measured tokens per 1,000 characters ÷ 1,000
baht   = (input tokens × input price + output tokens × output price) ÷ 1,000,000 × baht per dollar
```

The workloads are written in `registry/scenarios.toml`. Every size in them is an assumption chosen to
be plain and easy to argue with, not a measurement:

{{table_scenarios}}

- "The same content in English" scales the character counts by the English-to-Thai character ratio
  measured on FLORES-200 ({{en_per_th}}), not by an equal number of characters.
- Output tokens are assumed to have the same tokens-per-character rate as input text of that language.
  This is the weakest step: nothing here measures what a model writes.
- Example ({{scenario}}): at the same list price of {{pair1_in}} / {{pair1_out}} per million tokens,
  {{pair1_a_thb}} on {{pair1_a}} and {{pair1_b_thb}} on {{pair1_b}}, a ratio of {{ratio_price}}. At equal
  prices the cost ratio is the token ratio by construction.
- Open models have no per-token price of their own, so they have token counts only.

The site's calculator uses the same formula; a test runs the page's formula against
`results/{{costs_csv}}` for every preset and priced model.

## 10. Check against real billing, and its scope

Anthropic documents `count_tokens` as an estimate. To see whether it matches what is billed,
`ttt billing-check` sent real, paid requests on {{date_billing}}: {{bill_what}}

{{table_billing}}

Total cost {{bill_cost}} against a cap of {{bill_cap}}. Files: `results/{{billing_json}}` and
`results/{{billing_md}}`.

Result: billed input tokens equalled `count_tokens` on all {{bill_texts}} requests, and exceeded the
published content tokens by exactly the overhead that had been subtracted.

Scope, stated plainly:

- Claude only. GPT and Gemini counts were not compared with a bill.
- Single user message, no system prompt, no tools, no caching, default thinking settings. Requests with
  those features may be framed and billed differently.
- A small sample, on one day.
- The overhead ({{overheads}} tokens per request on Claude) is billed on every real request. It is left
  out of the published numbers because it does not depend on the language, so real bills are slightly
  higher than the tables for both languages.

## 11. FLORES-200 against FLORES+

FLORES+ is the maintained successor of FLORES-200 and may contain corrections. Version {{fp_version}}
(revision `{{fp_revision}}`) was prepared the same way and compared: after normalization {{fp_diff}}
sentences differ in English and Thai together, and {{fp_identical}} of {{fp_tokenizers}} compared
tokenizers gave identical per-sentence counts on both sets (`results/{{comparison_md}}`). The published
numbers therefore hold for both.

## 12. Known limits

{{list_limits_costs}}
- FLORES is news and encyclopedia style prose. Chat messages, code-switching, product names, emoji and
  numbers are common in real Thai workloads and may tokenize at a different rate. This is the largest
  open question for anyone applying the numbers to their own bill.
- The translations are not perfect, so "the same content" is approximately the same content.
- One dataset, one split, one pair of languages.
- Token counts for the API models are what the vendors' counting endpoints report. Only Claude's were
  compared with a bill (section 10).
- Tokenizers and prices change without notice. Every number here is tied to the dates at the top.
- Sampled models are assigned by equality on a sample (section 4), not confirmed by the vendor.
- For {{sp_differ}} open models the repository's two tokenizer files disagree (section 5).
- Request framing, system prompts, tools, caching, batch discounts and reasoning tokens are outside
  the numbers.

## 13. What would change the conclusions

- **A vendor changes a tokenizer.** The comparison between Claude, GPT and Gemini is a property of
  today's tokenizers. A rerun (`ttt count`, `ttt analyze`) would show it; old result sets stay in
  `results/`.
- **Prices change.** The "same list price" comparison depends on two pairs of models having equal
  prices on {{date_prices}}. `ttt site` and `ttt docs` stop with an error if a rerun finds they no
  longer do.
- **Your text is not like FLORES.** If real Thai chat tokenizes very differently from Thai news prose,
  the absolute rates move. The ordering of tokenizers would change only if the difference were large
  and went in opposite directions for different tokenizers; that has not been tested here.
- **Output is not like input.** If models write Thai at a different token rate than they read it,
  output-heavy workloads change.
- **Quality per token.** If a model that spends more tokens needs fewer turns or fewer retries to get a
  usable Thai answer, its real cost per task is lower than its cost per character. This benchmark
  cannot see that.
- **The billing check does not generalise.** If requests with system prompts or tools are billed
  differently from `count_tokens`, the Claude numbers would need a correction that this check could not
  detect.

## 14. Files

| What | Where |
|---|---|
| Per-sentence counts | {{counts_files}} in `results/`, each with a `.meta.json` |
| Verification | the `verification_*` files named in `results/latest.json` |
| Summary of every model | `results/{{summary_md}}`, `results/{{summary_csv}}` |
| Prices and exchange rate | `results/{{prices_json}}` |
| Costs per scenario | `results/{{costs_md}}`, `results/{{costs_csv}}` |
| Billing check | `results/{{billing_md}}` |
| FLORES-200 against FLORES+ | `results/{{comparison_md}}` |
| What was run, day by day | `LOG.md` |

Result files are never edited or overwritten. A correction is a new dated run and a line in `LOG.md`.
