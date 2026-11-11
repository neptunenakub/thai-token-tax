Billing check, 2026-11-10T09:55:05Z. the identical request sent to count_tokens (free) and to the Messages API with max_tokens=1 (billed): no system prompt, no tools, no cache_control, default thinking settings.

Cost: expected $0.007477, actual $0.007477 (cap $0.10); 90 billable requests.

| model | texts | billed input vs count_tokens | billed input - published content tokens | overhead subtracted in results | cache tokens | output tokens | cost USD |
|---|---:|---|---|---:|---|---|---:|
| `claude-haiku-5-5` | 40 | equal for every text | [8] | 8 | none | [1] | 0.000358 |
| `claude-haiku-4-5-20251001` | 40 | equal for every text | [7] | 7 | none | [1] | 0.003295 |
| `claude-opus-5-5` | 10 | equal for every text | [8] | 8 | none | [1] | 0.003824 |

claude-opus-5-5 vs claude-haiku-5-5 on the same texts: 0 of 10 billed a different number of input tokens.
