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
