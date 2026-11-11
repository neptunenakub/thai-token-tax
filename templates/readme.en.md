# Thai Token Tax · ภาษีภาษา

**The same Thai text takes {{ratio_gpt}}× the tokens on Claude as on GPT, and {{ratio_gemini}}× as on Gemini.**
APIs bill per token, so the bill follows. At the same list price ({{pair1_in}} in / {{pair1_out}} out per
million tokens), an example workload ({{scenario}}) costs {{pair1_a_thb}} on {{pair1_a}} and
{{pair1_b_thb}} on {{pair1_b}}.

{{table_headline}}

This measures **cost, not answer quality**: a model that uses more tokens may still answer Thai better.
{{n_models}} models ({{n_groups}} distinct tokenizers) on {{pairs}} parallel Thai–English sentences
(FLORES-200), measured {{date_data}}; official list prices as of {{date_prices}}.

Reproduce it:

```
git clone {{clone_url}} thai-token-tax && cd thai-token-tax
pip install -e .
ttt all --out rerun
```

[ภาษาไทย](README.th.md) · [Method and limits](docs/methodology.md) · [Result files](results/) ·
web page with a cost calculator: {{site_ref}}

---

## Reproducing

- Needs Python 3.11 or newer (use a virtual environment) and no API key. {{repo_url_note}}
- `ttt all` downloads FLORES-200 (about {{flores_mb}} MB) and the tokenizer files, counts every sentence with
  every local tokenizer, recounts in a second independent way, and writes `rerun/summary_<date>.md`.
- Those rows must equal the rows with source `open` in [`results/{{summary_md}}`](results/{{summary_md}}).
  The published per-sentence counts are in `results/{{counts_open}}`.
- Claude, GPT and Gemini are counted through their official token-counting endpoints. Without
  `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` and `GEMINI_API_KEY` those sources are reported as blocked and
  skipped; gated Hugging Face repositories need `HF_TOKEN`. A model that cannot be measured is listed as
  blocked with the real error. It is never replaced by an estimate.
- Result files are never overwritten: every run writes a new dated set, which is why the example writes
  to `rerun/`. `ttt prepare` (the first step of `ttt all`) also rewrites `data/source.json` and
  `data/normalization_log.json`; only their timestamps should change.
- `pytest` runs the tests (no network, no keys): `pip install -e ".[dev]"`, then `pytest -q`.

## What is measured, and what is not

Every model's own tokenizer counts the same content in Thai and in English. Two numbers come out, and
they answer different questions:

- **Tokens per 1,000 Thai characters** compares models with each other: the same Thai text, how many
  tokens. Multiplied by a price it gives the bill.
- **Thai ÷ English** (the "premium") compares the two languages inside one model, with a {{ci_level}}%
  bootstrap confidence interval. It cannot be compared across models, because each model spends a
  different number of tokens on English. Example: from {{gen_old}} to {{gen_new}} the premium fell from
  {{gen_old_premium}} to {{gen_new_premium}}, yet Thai tokens per 1,000 characters barely moved
  ({{gen_old_thai}} → {{gen_new_thai}}) while English rose from {{gen_old_english}} to
  {{gen_new_english}}.

Baht costs are measured tokens × official list price × the Bank of Thailand rate, for example
workloads whose sizes are assumptions.

Not measured: answer quality, speed, reasoning or thinking tokens, prompt caching, batch discounts, and
any kind of text other than the FLORES-200 sentences (news and encyclopedia style).

## Results

### Tokens for the same Thai text

{{table_groups}}

One row is one distinct tokenizer. Models in a row gave identical token counts on every sentence
(models measured on a sample: on every sampled sentence). The table of all {{n_models}} models is
[`results/{{summary_md}}`](results/{{summary_md}}).

{{thai_group_label}} give identical counts: {{thai_group_1k}} tokens per 1,000 Thai characters. The Thai
models in this group inherit the base model's tokenizer.

### Same list price, different bill

Example workload: {{scenario}}.

{{table_pairs}}

### Every priced model, same example workload

{{table_costs}}

More tokens does not always mean a higher bill: {{counter_more}} costs {{counter_more_thb}}, less than
{{counter_fewer}} at {{counter_fewer_thb}}, although it uses more Thai tokens ({{counter_more_1k}} vs
{{counter_fewer_1k}} per 1,000 characters). The price per token differs.

Open models have no per-token price of their own, so they have token counts only. The other
workloads are in [`results/{{costs_md}}`](results/{{costs_md}}); the web page has a calculator with
editable assumptions.

The workloads (assumptions, from `registry/scenarios.toml`; sizes in Thai characters):

{{table_scenarios}}

### Planned but not measured

{{table_blocked}}

## Limits

{{list_limits_costs}}
- FLORES contains some translations whose meaning does not match the source. The data was not edited.
- The check against real billing ({{bill_texts}} paid requests to Claude; billed input tokens equalled
  `count_tokens` on every one) covered single-message requests only: no system prompt, no tools.
- Claude's request framing ({{overheads}} tokens per request) is billed, but is not part of these numbers.
- Prices change. On {{date_prices}} Google's pricing page stated an end date for the current price of:

{{list_price_end_dates}}

The full list of weak points, and what would change the conclusions, is in
[`docs/methodology.md`](docs/methodology.md).

## Adding a model or a language

Both are registry changes, not new code.

- **Model:** add one `[[model]]` block to `registry/models.toml` (`id`, `family`, `counter`; `revision`
  pins a Hugging Face repository; `sample_of` checks an API model against a fully measured one on a fixed
  sample). Then `ttt count`, `ttt verify`, `ttt analyze`. For a price, add its row to
  `registry/pricing.toml` and run `ttt prices` and `ttt cost`. Then `ttt site` and `ttt docs`.
- **Language:** add one `[[target]]` block with a FLORES-200 code to `registry/languages.toml`, then
  `ttt prepare` and the steps above. `prepare`, `count`, `verify` and `analyze` take every language in
  the registry; only Thai has been run so far, and the cost tables, the site and this README present one
  target language.

## Repository layout

```
registry/              what is measured: models, languages, price sources, example workloads, display names
src/thai_token_tax/    the `ttt` command: prepare, count, verify, analyze, prices, cost, compare, site, docs
tests/                 pytest, no network
data/                  provenance and logs; the FLORES sentences are rebuilt locally, not committed
results/               dated raw counts, summaries, prices, costs; latest.json points at the newest set
site/                  one static page; reads site/data.json, written by `ttt site`
templates/             the sources of this README and docs/methodology.md, filled by `ttt docs`
docs/methodology.md    how it was measured, limits, what would change the conclusions
blog/                  articles (Thai, English) and post drafts, generated like this README
ARCHITECTURE.md        how the code is organised
LOG.md                 what was run each day, including the things that went wrong
```

No number in this README, the methodology or the site is typed by hand: they are generated from
`results/`, and tests fail if a document is out of date.

## Dates and sources

- Token counts: measured {{date_data}} (UTC). Raw per-sentence counts: {{counts_files}}.
- Prices: official pricing pages of Anthropic, OpenAI and Google, fetched {{date_prices}}, saved with the
  page hashes in `results/{{prices_json}}`.
- Exchange rate: {{rate}} baht per US dollar, {{rate_what}}, {{date_rate}}
  (<{{rate_page}}>).
- Data: FLORES-200 `devtest`, English and Thai, the original Meta release. FLORES+ {{fp_version}} differs
  from it in {{fp_diff}} of these sentences after normalization.

## Licences

- Code: {{lic_code}} ([LICENSE](LICENSE)).
- Result files, documentation and site text: {{lic_results}} ([LICENSE-DATA](LICENSE-DATA)).
- FLORES-200 is by Meta (NLLB Team) under {{lic_dataset}}. Its sentences are not redistributed here;
  `ttt prepare` downloads them from the original release. See [`data/README.md`](data/README.md).

## How to cite

```
{{holder}}. Thai Token Tax: how many more tokens Thai text costs than the same
English text on major AI models. Version {{version}}, measured {{date_data}}. {{clone_url}}
```

Machine-readable: [`CITATION.cff`](CITATION.cff).
