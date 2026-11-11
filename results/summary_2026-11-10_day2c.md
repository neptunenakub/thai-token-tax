| source | family | model / encoding | language | premium vs baseline | 95% CI | tokens | tokens per 1,000 chars | baseline tokens | baseline tokens per 1,000 chars | sentences | same counts as |
|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---|
| open | OpenAI | `tiktoken/o200k_base` | tha_Thai | 1.954 | 1.930–1.979 | 52520 | 416.5 | 26872 | 203.6 | 1012 |  |
| open | OpenAI | `tiktoken/cl100k_base` | tha_Thai | 4.343 | 4.287–4.400 | 118037 | 936.1 | 27181 | 206.0 | 1012 |  |
| open | OpenAI | `tiktoken/o200k_harmony` | tha_Thai | 1.954 | 1.930–1.979 | 52520 | 416.5 | 26872 | 203.6 | 1012 | `tiktoken/o200k_base` |
| open | Qwen | `Qwen/Qwen3-8B` | tha_Thai | 2.541 | 2.508–2.575 | 70195 | 556.7 | 27620 | 209.3 | 1012 |  |
| open | Qwen | `Qwen/Qwen3.5-9B` | tha_Thai | 1.201 | 1.187–1.215 | 33058 | 262.2 | 27529 | 208.6 | 1012 |  |
| open | Qwen | `Qwen/Qwen3.8-27B` | tha_Thai | 1.201 | 1.187–1.215 | 33058 | 262.2 | 27529 | 208.6 | 1012 | `Qwen/Qwen3.5-9B` |
| open | Typhoon | `typhoon-ai/typhoon2.5-qwen3-4b` | tha_Thai | 2.541 | 2.508–2.575 | 70195 | 556.7 | 27620 | 209.3 | 1012 | `Qwen/Qwen3-8B` |
| open | Typhoon | `typhoon-ai/typhoon2.1-gemma3-12b` | tha_Thai | 1.600 | 1.580–1.621 | 43385 | 344.1 | 27113 | 205.5 | 1012 |  |
| open | Typhoon | `typhoon-ai/llama3.1-typhoon2-8b-instruct` | tha_Thai | 2.185 | 2.159–2.211 | 59357 | 470.7 | 27170 | 205.9 | 1012 |  |
| open | Typhoon | `typhoon-ai/typhoon-7b` | tha_Thai | 1.276 | 1.262–1.291 | 38328 | 303.9 | 30027 | 227.5 | 1012 |  |
| open | Typhoon | `typhoon-ai/typhoon-s-thaillm-8b-instruct-research-preview` | tha_Thai | 2.541 | 2.508–2.575 | 70195 | 556.7 | 27620 | 209.3 | 1012 | `Qwen/Qwen3-8B` |
| open | OpenThaiGPT | `openthaigpt/openthaigpt1.5-7b-instruct` | tha_Thai | 2.541 | 2.508–2.575 | 70195 | 556.7 | 27620 | 209.3 | 1012 | `Qwen/Qwen3-8B` |
| open | OpenThaiGPT | `openthaigpt/openthaigpt-1.6-72b-instruct` | tha_Thai | 2.541 | 2.508–2.575 | 70195 | 556.7 | 27620 | 209.3 | 1012 | `Qwen/Qwen3-8B` |
| open | OpenThaiGPT | `openthaigpt/openthaigpt-r1-32b-instruct` | tha_Thai | 2.541 | 2.508–2.575 | 70195 | 556.7 | 27620 | 209.3 | 1012 | `Qwen/Qwen3-8B` |
| open | OpenThaiGPT | `openthaigpt/openthaigpt-1.0.0-7b-chat` | tha_Thai | 1.024 | 1.013–1.035 | 31894 | 252.9 | 31154 | 236.1 | 1012 |  |
| open | OpenThaiGPT | `openthaigpt/openthaigpt-thaillm-8b-instruct-v0.7.2-research-preview` | tha_Thai | 2.541 | 2.508–2.575 | 70195 | 556.7 | 27620 | 209.3 | 1012 | `Qwen/Qwen3-8B` |
| open | SEA-LION | `aisingapore/Nemotron-SEA-LION-v4.8-30B-A3B` | tha_Thai | 2.365 | 2.335–2.395 | 65795 | 521.8 | 27826 | 210.9 | 1012 |  |
| open | SEA-LION | `aisingapore/Qwen-SEA-LION-v4.5-27B-IT` | tha_Thai | 1.201 | 1.187–1.215 | 33058 | 262.2 | 27529 | 208.6 | 1012 | `Qwen/Qwen3.5-9B` |
| open | SEA-LION | `aisingapore/Qwen-SEA-LION-v4-32B-IT` | tha_Thai | 2.541 | 2.508–2.575 | 70195 | 556.7 | 27620 | 209.3 | 1012 | `Qwen/Qwen3-8B` |
| open | SEA-LION | `aisingapore/Gemma-SEA-LION-v4-27B-IT` | tha_Thai | 1.600 | 1.580–1.621 | 43385 | 344.1 | 27113 | 205.5 | 1012 | `typhoon-ai/typhoon2.1-gemma3-12b` |
| open | SEA-LION | `aisingapore/Llama-SEA-LION-v3.5-8B-R` | tha_Thai | 2.185 | 2.159–2.211 | 59357 | 470.7 | 27170 | 205.9 | 1012 | `typhoon-ai/llama3.1-typhoon2-8b-instruct` |
| open | SEA-LION | `aisingapore/Gemma-SEA-LION-v3-9B-IT` | tha_Thai | 1.842 | 1.817–1.867 | 49795 | 394.9 | 27035 | 204.9 | 1012 |  |
| open | Gemma | `google/gemma-4-31B-it` | tha_Thai | 1.600 | 1.580–1.621 | 43385 | 344.1 | 27113 | 205.5 | 1012 | `typhoon-ai/typhoon2.1-gemma3-12b` |
| open-llama31 | Llama | `meta-llama/Llama-3.1-8B-Instruct` | tha_Thai | 2.185 | 2.159–2.211 | 59357 | 470.7 | 27170 | 205.9 | 1012 | `typhoon-ai/llama3.1-typhoon2-8b-instruct` |
| open-llama33 | Llama | `meta-llama/Llama-3.3-70B-Instruct` | tha_Thai | 2.185 | 2.159–2.211 | 59357 | 470.7 | 27170 | 205.9 | 1012 | `typhoon-ai/llama3.1-typhoon2-8b-instruct` |
| openai | OpenAI | `gpt-6-astra` | tha_Thai | 1.954 | 1.930–1.979 | 52520 | 416.5 | 26872 | 203.6 | 1012 | `tiktoken/o200k_base` |
| openai | OpenAI | `gpt-6-sol` | tha_Thai | | | | | | | 100 (sample) | `tiktoken/o200k_base` |
| openai | OpenAI | `gpt-6-luna` | tha_Thai | | | | | | | 100 (sample) | `tiktoken/o200k_base` |
| openai | OpenAI | `gpt-6.1-sol` | tha_Thai | | | | | | | 100 (sample) | `tiktoken/o200k_base` |
| openai | OpenAI | `gpt-6.1-terra` | tha_Thai | | | | | | | 100 (sample) | `tiktoken/o200k_base` |
| openai | OpenAI | `gpt-5.5` | tha_Thai | 1.954 | 1.930–1.979 | 52520 | 416.5 | 26872 | 203.6 | 1012 | `tiktoken/o200k_base` |
| openai | OpenAI | `gpt-5.6-sol` | tha_Thai | | | | | | | 100 (sample) | `tiktoken/o200k_base` |
| openai | OpenAI | `gpt-5.4` | tha_Thai | | | | | | | 100 (sample) | `tiktoken/o200k_base` |
| openai | OpenAI | `gpt-5.2` | tha_Thai | | | | | | | 100 (sample) | `tiktoken/o200k_base` |
| gemini | Gemini | `gemini-3.8-flash` | tha_Thai | 1.600 | 1.580–1.621 | 43385 | 344.1 | 27113 | 205.5 | 1012 | `typhoon-ai/typhoon2.1-gemma3-12b` |
| gemini | Gemini | `gemini-4-argon` | tha_Thai | 1.519 | 1.500–1.538 | 41094 | 325.9 | 27058 | 205.0 | 1012 |  |
| gemini | Gemini | `gemini-3.6-flash` | tha_Thai | | | | | | | 100 (sample) | `typhoon-ai/typhoon2.1-gemma3-12b` |
| gemini | Gemini | `gemini-3.5-flash-lite` | tha_Thai | | | | | | | 100 (sample) | `typhoon-ai/typhoon2.1-gemma3-12b` |
| gemini | Gemini | `gemini-3.1-pro-preview` | tha_Thai | | | | | | | 100 (sample) | `typhoon-ai/typhoon2.1-gemma3-12b` |
| anthropic | Claude | `claude-opus-5-5` | tha_Thai | 2.676 | 2.645–2.709 | 112169 | 889.5 | 41913 | 317.6 | 1012 |  |
| anthropic | Claude | `claude-fable-5-2` | tha_Thai | | | | | | | 100 (sample) | `claude-opus-5-5` |
| anthropic | Claude | `claude-sonnet-5-5` | tha_Thai | | | | | | | 100 (sample) | `claude-opus-5-5` |
| anthropic | Claude | `claude-haiku-5-5` | tha_Thai | | | | | | | 100 (sample) | `claude-opus-5-5` |
| anthropic | Claude | `claude-haiku-4-5-20251001` | tha_Thai | 3.870 | 3.820–3.922 | 111785 | 886.5 | 28882 | 218.9 | 1012 |  |
| anthropic | Claude | `claude-sonnet-4-6` | tha_Thai | | | | | | | 100 (sample) | `claude-haiku-4-5-20251001` |
