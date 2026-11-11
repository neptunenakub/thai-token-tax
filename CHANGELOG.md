# Changelog

Changes to the code and to the published result sets. Result files are never edited: a new
measurement is a new dated set in `results/`, and `LOG.md` records what was run each day.

## 0.1.0 (unreleased)

First version.

- `ttt` command: `prepare`, `count`, `verify`, `analyze`, `prices`, `cost`, `compare`,
  `billing-check`, `site`, `docs`, `card`.
- Counters for `tiktoken` encodings, Hugging Face `tokenizer.json` files, and the official
  token-counting endpoints of Anthropic, OpenAI and Google.
- First result set (Thai against English on FLORES-200 `devtest`): per-sentence counts, summary
  with bootstrap confidence intervals, official list prices, baht costs for example workloads,
  a check of Claude `count_tokens` against billed usage, and a comparison with FLORES+.
- Static site with a cost calculator; `README.md`, `README.th.md` and `docs/methodology.md`
  generated from the result files.
- Generated the same way: articles in Thai and English, post drafts, share cards
  (`site/card.<lang>.svg` and `.png`) and link-preview tags.
- Licences: MIT for code, CC BY 4.0 for results and text.
