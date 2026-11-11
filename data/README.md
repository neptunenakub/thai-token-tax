# data/

## What is here

| file | in git? | what |
|---|---|---|
| `source.json` | yes | where the data came from: URL, SHA-256, license, date, FLORES+ access probe |
| `normalization_log.json` | yes | normalization rules and how many sentences each rule changed (sentence ids only, no text) |
| `flores200_devtest.tsv` | **no** | the 1,012 normalized sentences, one column per language in `registry/languages.toml` |
| `spotcheck_20.md` | **no** | 20 random pairs (fixed seed) for a human check of the translations |
| `raw/` | **no** | the downloaded tarball and extracted originals |

Rebuild the files that are not in git (downloads ~25 MB, checks the SHA-256):

```
ttt prepare
```

The result must have the SHA-256 recorded in `source.json` → `normalized_tsv.sha256`;
`ttt count` refuses to run on a file with a different hash.

## Source and license

- **Dataset:** FLORES-200, `devtest` split, `eng_Latn` and `tha_Thai` (1,012 aligned sentences).
- **Release used:** the original Meta release,
  <https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz>
  (linked as "the original version of the dataset" from
  <https://github.com/facebookresearch/flores/blob/main/flores200/README.md>).
- **License:** CC BY-SA 4.0, as stated in
  <https://github.com/facebookresearch/flores/blob/main/README.md> ("FLORES-200: CC-BY-SA 4.0").
- **Citation:** NLLB Team et al., "No Language Left Behind: Scaling Human-Centered Machine
  Translation", 2022 (arXiv:2207.04672), and the earlier FLORES-101 / FLORES papers listed in
  the repository above.

### Why not FLORES+ (the newer, maintained version)?

`openlanguagedata/flores_plus` on Hugging Face is a gated dataset: files return HTTP 401
without a token from an account that accepted its terms, so it could not be read when the
core set was prepared (the probe result is saved in `source.json`). FLORES-200 stayed the core
set; FLORES+ was compared with it later (see the last section).

### Why the sentences are not committed

The FLORES+ dataset card asks users not to redistribute the data publicly unless it is
protected from automatic scraping (to keep the benchmark out of model training data). The
license would allow committing the text with attribution, but this repo keeps the sentences
out of git and ships the exact recipe to rebuild them instead.

## FLORES+ (second set, for comparison only)

- Source: <https://huggingface.co/datasets/openlanguagedata/flores_plus>, revision `1147e2dc59f37fbb5c22fd8478770de02cd399f9`
  (version 5.0), license CC BY-SA 4.0. Gated: `ttt prepare --dataset floresplus` needs the `HF_TOKEN` of an
  account that accepted the dataset terms. Details and file hashes: `source_floresplus.json`.
- The terms ask users not to re-host FLORES+ where web crawlers can read it and not to train on it.
  No FLORES+ sentence is committed: `floresplus_devtest.tsv`, `spotcheck_floresplus_changes.md` and `raw/` are local only.
- FLORES-200 stays the core set. FLORES+ results live in `results/floresplus/` and in
  `results/comparison_flores200_vs_floresplus_<date>.*`.
