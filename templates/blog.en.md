# The same Thai text takes {{ratio_gpt}}× the tokens on Claude as on GPT

Language model APIs bill per token, and tokenizers do not treat every language alike. I measured how
many tokens the tokenizers of {{n_models}} models spend on Thai. The same Thai text takes
{{ratio_gpt}}× the tokens on current Claude models as on GPT, and {{ratio_gemini}}× as on Gemini 3.x:
{{claude_1k}}, {{gpt_1k}} and {{gemini_1k}} tokens per 1,000 Thai characters.

The measurement covers {{n_groups}} distinct tokenizers on {{pairs}} parallel Thai–English sentences
from FLORES-200, counted on {{date_data}}. The main caveat comes first: this is **cost, not answer
quality**. A model that spends more tokens on Thai may still answer Thai better, and nothing here
ranks models.

## The numbers

{{table_headline}}

At the same price per token, a ratio of tokens is a ratio of money. Two pairs of models had identical
list prices on {{date_prices}}, which makes the comparison direct. For an example workload
({{scenario}}; its size is an assumption) at {{pair1_in}} in / {{pair1_out}} out per million tokens,
{{pair1_a}} comes to {{pair1_a_thb}} and {{pair1_b}} to {{pair1_b_thb}}.

More tokens does not always mean a higher bill, because prices differ. On the same workload
{{counter_more}} costs {{counter_more_thb}}, less than {{counter_fewer}} at {{counter_fewer_thb}},
although it uses {{counter_more_1k}} tokens per 1,000 Thai characters against {{counter_fewer_1k}}.

## The "Thai premium", and why it misleads across models

The number usually quoted for this topic is a ratio inside one model: tokens for Thai divided by tokens
for the same content in English. Here it is {{claude_p2}} for Claude, {{gpt_p2}} for GPT and
{{gemini_p2}} for Gemini 3.x, each with a {{ci_level}}% bootstrap confidence interval in the results.

It is a fair answer to "how much more does Thai cost than English in this model". It is a poor way
to compare models, because the denominator is each model's own English rate. From {{gen_old}} to
{{gen_new}} the premium fell from {{gen_old_premium}} to {{gen_new_premium}}, which reads like an
improvement for Thai. The absolute rates say otherwise: Thai went from {{gen_old_thai}} to
{{gen_new_thai}} tokens per 1,000 characters, while English went from {{gen_old_english}} to
{{gen_new_english}}. Thai did not get cheaper to encode; English got more expensive.

So the results report both numbers and compare models only on the absolute one.

## Why the numbers can be checked

- **Official counting endpoints.** Claude, GPT and Gemini were counted through each vendor's own
  token-counting endpoint, one request per sentence. Open models were counted with the tokenizer file
  from their repository, pinned to a commit.
- **The overhead is measured and tested, not assumed.** Those endpoints count the whole request, so
  each answer includes a few framing tokens. They are measured on a minimal message, subtracted, and
  then tested for being constant across lengths, languages and repeated calls.
- **Counted against billed.** Anthropic documents `count_tokens` as an estimate, so {{bill_texts}} real
  requests were sent to Claude. Billed input tokens equalled the count on every one. The check covered
  single-message requests only: no system prompt, no tools.
- **Equality sampling.** Vendors do not say which models share a tokenizer. {{n_full}} models and
  encodings were measured in full; {{n_sampled}} more were counted on a fixed sample of {{sample_size}}
  sentence pairs and assigned to a fully measured model only if every count was identical. That is
  evidence, not a statement from the vendor.
- **A second count.** Every local tokenizer was recounted in a second, independent way.
- **Reproduction from a fresh clone.** With no API key, a new clone reproduced every per-sentence
  count of the {{n_open_measured}} local tokenizers that need no access token.
- **No typed numbers.** The site, the README and this article are generated from the result files, and
  tests fail when they drift.

## Limits

- FLORES-200 is news and encyclopedia prose. Chat messages, product names and Thai mixed with English
  may tokenize at a different rate. This is the largest open question for anyone applying the numbers
  to their own bill.
- Output tokens are assumed to follow the same rate as input text. Nothing here measures what a model
  writes.
- Reasoning tokens, prompt caching, batch discounts and request framing are outside the numbers.
- Open models have no per-token price of their own, so they have token counts only. Thai fine-tunes
  inherit the base model's tokenizer: {{thai_group_label}} give identical counts,
  {{thai_group_1k}} tokens per 1,000 Thai characters.
- Tokenizers and prices change. Every number is tied to the dates above.

## Next

FLORES-200 covers the other languages of Southeast Asia, and adding a language is a registry line
rather than new code. Lao, Khmer, Burmese, Vietnamese, Indonesian, Malay and Tagalog are planned next.

## Reproduce it

```
git clone {{clone_url}} thai-token-tax && cd thai-token-tax
pip install -e .
ttt all --out rerun
```

Code, raw per-sentence counts and the method are at {{clone_url}}; the page with a cost calculator is
at {{site_url}}. If you find a wrong number or a hole in the method, please open an issue.
