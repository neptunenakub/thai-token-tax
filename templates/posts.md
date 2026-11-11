# Post drafts

Drafts to edit before posting. Every number is filled in from the result files by `ttt docs`.
{{urls_note}}
Attach `site/card.th.png` to Thai posts and `site/card.en.png` to English posts.
Hashtags: `#ภาษีภาษา` and `#ThaiTokenTax` only. No person or team is named or tagged.

## X thread, Thai

Each block is one post (limit 280 characters; a link counts as 23).

```
ราคาป้ายเท่ากัน แต่งานภาษาไทยบน Claude จ่ายแพงกว่า GPT {{th_ratio_price}} เท่า

ผมวัดว่าข้อความไทยเดียวกันถูกนับเป็นกี่ token บน {{th_n_models}} โมเดล แล้วคิดเป็นเงินบาท

วัดต้นทุน ไม่ใช่คุณภาพคำตอบ

{{site_url}}
#ภาษีภาษา #ThaiTokenTax
```

```
สาเหตุคือ tokenizer ค่า API คิดตาม token และข้อความไทย 1,000 ตัวอักษรเดียวกันถูกนับเป็น

{{short_claude}}: {{th_claude_1k}} token
{{short_gpt}}: {{th_gpt_1k}}
{{short_gemini}}: {{th_gemini_1k}}
{{short_gemini_other}}: {{th_gemini_other_1k}}

วัดจากคู่ประโยคไทย–อังกฤษ {{th_pairs}} คู่ (FLORES-200)
```

```
คิดเป็นเงิน: {{th_scenario}}

ราคาป้ายเท่ากันที่ {{th_pair1_in}} / {{th_pair1_out}} ต่อล้าน token
{{th_pair1_a}}: {{th_pair1_a_thb}}
{{th_pair1_b}}: {{th_pair1_b_thb}}

ขนาดงานเป็นสมมติฐาน ใส่ตัวเลขของคุณเองได้ในตัวคำนวณบนหน้าเว็บ
```

```
แต่ token มากกว่าไม่ได้แปลว่าแพงกว่าเสมอ

งานเดียวกัน {{th_counter_more}} จ่าย {{th_counter_more_thb}} น้อยกว่า {{th_counter_fewer}} ที่จ่าย {{th_counter_fewer_thb}} ทั้งที่ใช้ token ไทยมากกว่า

ต้องคูณ token กับราคาต่อ token ของโมเดลนั้นเสมอ
```

```
ตัวเลข "ไทยแพงกว่าอังกฤษกี่เท่า" ใช้เทียบข้ามโมเดลไม่ได้

จาก {{th_gen_old}} ไป {{th_gen_new}} ค่านี้ลดจาก {{th_gen_old_premium}} เหลือ {{th_gen_new_premium}} แต่ token ไทยต่อ 1,000 ตัวอักษรแทบเท่าเดิม ({{th_gen_old_thai}} → {{th_gen_new_thai}}) ฝั่งอังกฤษต่างหากที่เพิ่มขึ้น
```

```
วิธีวัด: endpoint นับ token ทางการของแต่ละค่าย หัก token โครงคำขอที่ตรวจแล้วว่าคงที่ และตรวจ Claude กับยอดที่ถูกคิดเงินจริง {{th_bill_texts}} คำขอ

ราคา ณ {{th_date_prices}} โค้ดและข้อมูลดิบเปิดทั้งหมด รันซ้ำได้

{{clone_url}}
```

## X thread, English

```
The same Thai text takes {{ratio_gpt}}× the tokens on Claude as on GPT, and {{ratio_gemini}}× as on Gemini.

I measured {{n_models}} models on {{pairs}} parallel Thai–English sentences.

This is cost, not answer quality.

{{site_url}}
#ThaiTokenTax #ภาษีภาษา
```

```
Tokens per 1,000 Thai characters:

{{short_claude}}: {{claude_1k}}
{{short_gpt}}: {{gpt_1k}}
{{short_gemini}}: {{gemini_1k}}
{{short_gemini_other}}: {{gemini_other_1k}}

APIs bill per token, so at the same price per token this is the ratio of the bills.
```

```
Two pairs of models had the same list price on {{date_prices}}.

At {{pair1_in}} / {{pair1_out}} per million tokens, an example Thai chatbot workload comes to {{pair1_a_thb}} on {{pair1_a}} and {{pair1_b_thb}} on {{pair1_b}}.

The workload size is an assumption.
```

```
The usual "Thai costs N× English" ratio misleads across models.

From {{gen_old}} to {{gen_new}} it fell from {{gen_old_premium}} to {{gen_new_premium}}. Thai tokens per 1,000 characters barely moved ({{gen_old_thai}} → {{gen_new_thai}}). English rose from {{gen_old_english}} to {{gen_new_english}}.
```

```
More tokens is not always a higher bill.

On the same workload {{counter_more}} costs {{counter_more_thb}}, less than {{counter_fewer}} at {{counter_fewer_thb}}, although it uses more Thai tokens. Prices per token differ.
```

```
Method: official token-counting endpoints, framing overhead measured and tested for being constant, Claude counts checked against {{bill_texts}} billed requests.

Code and raw per-sentence counts are open, and it reruns without an API key.

{{clone_url}}
```

## LinkedIn, English

```
I measured what Thai text costs on major AI models.

The same Thai text takes {{ratio_gpt}}× the tokens on current Claude models as on GPT, and {{ratio_gemini}}× as on Gemini 3.x: {{claude_1k}}, {{gpt_1k}} and {{gemini_1k}} tokens per 1,000 Thai characters. APIs bill per token, so at the same list price ({{pair1_in}} in / {{pair1_out}} out per million tokens) an example Thai chatbot workload comes to {{pair1_a_thb}} on {{pair1_a}} and {{pair1_b_thb}} on {{pair1_b}}.

This is cost, not answer quality. A model that spends more tokens may still answer Thai better, and more tokens is not always a higher bill: on the same workload {{counter_more}} costs less than {{counter_fewer}}.

What I learned building it:
- The usual "Thai costs N× English" ratio cannot compare models. From {{gen_old}} to {{gen_new}} it fell from {{gen_old_premium}} to {{gen_new_premium}}, yet Thai tokens per character barely moved. English got more expensive.
- Counting endpoints include a few framing tokens per request. I measured that overhead, tested that it is constant, and checked Claude's counts against {{bill_texts}} billed requests.
- A number is only worth quoting if someone else can get it again. The site, the README and the article are generated from the raw result files, and a fresh clone reproduces the local counts without any API key.

{{n_models}} models, {{n_groups}} distinct tokenizers, {{pairs}} parallel Thai–English sentences (FLORES-200), measured {{date_data}}.

Page with a cost calculator: {{site_url}}
Code, data and method: {{clone_url}}

#ThaiTokenTax #ภาษีภาษา
```

## LinkedIn, Thai

```
ผมวัดว่าข้อความภาษาไทยมีต้นทุนเท่าไหร่บนโมเดล AI ค่ายหลัก

ข้อความไทยเดียวกันใช้ token บน Claude รุ่นปัจจุบันมากกว่า GPT {{th_ratio_gpt}} เท่า และมากกว่า Gemini 3.x {{th_ratio_gemini}} เท่า ค่า API คิดตาม token ที่ราคาป้ายเท่ากัน ({{th_pair1_in}} ขาเข้า / {{th_pair1_out}} ขาออก ต่อล้าน token) งานตัวอย่าง "{{th_scenario}}" จึงมีค่าใช้จ่าย {{th_pair1_a_thb}} บน {{th_pair1_a}} และ {{th_pair1_b_thb}} บน {{th_pair1_b}}

งานนี้วัดต้นทุน ไม่ใช่คุณภาพคำตอบ โมเดลที่ใช้ token มากกว่าอาจตอบภาษาไทยได้ดีกว่าก็ได้ และ token มากกว่าไม่ได้แปลว่าแพงกว่าเสมอ ในงานเดียวกัน {{th_counter_more}} จ่ายน้อยกว่า {{th_counter_fewer}}

สิ่งที่ได้เรียนรู้ระหว่างทำ:
- อัตราส่วน "ไทยแพงกว่าอังกฤษกี่เท่า" ใช้เทียบข้ามโมเดลไม่ได้ จาก {{th_gen_old}} ไป {{th_gen_new}} ค่านี้ลดจาก {{th_gen_old_premium}} เหลือ {{th_gen_new_premium}} แต่ token ต่อตัวอักษรไทยแทบไม่เปลี่ยน ฝั่งภาษาอังกฤษต่างหากที่ใช้ token มากขึ้น
- endpoint นับ token มี token โครงคำขอปนมาด้วย ผมวัดค่านี้ ทดสอบว่าคงที่ แล้วตรวจตัวเลขของ Claude กับยอดที่ถูกคิดเงินจริง {{th_bill_texts}} คำขอ
- ตัวเลขจะมีค่าก็ต่อเมื่อคนอื่นวัดซ้ำได้ หน้าเว็บ README และบทความสร้างจากไฟล์ผลดิบทั้งหมด และ clone ใหม่ก็รันซ้ำส่วนที่ใช้ tokenizer ในเครื่องได้โดยไม่ต้องมี API key

วัด {{th_n_models}} โมเดล ({{th_n_groups}} tokenizer) ด้วยคู่ประโยคไทย–อังกฤษ {{th_pairs}} คู่ (FLORES-200) เมื่อ {{th_date_data}}

หน้าเว็บพร้อมตัวคำนวณค่าใช้จ่าย: {{site_url}}
โค้ด ข้อมูล และวิธีวัด: {{clone_url}}

#ภาษีภาษา #ThaiTokenTax
```

## Facebook groups (Thai developers / AI)

```
ใครจ่ายค่า API โมเดล AI กับงานภาษาไทยอยู่ ผมวัดตัวเลขมาให้ดูครับ

ราคาป้ายต่อล้าน token เท่ากัน ไม่ได้แปลว่าจ่ายเท่ากัน เพราะข้อความไทยเดียวกันถูกนับเป็น token ไม่เท่ากันในแต่ละค่าย

token ต่อข้อความไทย 1,000 ตัวอักษร:
- {{short_claude}}: {{th_claude_1k}}
- {{short_gpt}}: {{th_gpt_1k}}
- {{short_gemini}}: {{th_gemini_1k}}
- {{short_gemini_other}}: {{th_gemini_other_1k}}

ตัวอย่างเป็นเงิน ({{th_scenario}}) ที่ราคาป้ายเท่ากัน {{th_pair1_in}} / {{th_pair1_out}} ต่อล้าน token: {{th_pair1_a}} {{th_pair1_a_thb}} ส่วน {{th_pair1_b}} {{th_pair1_b_thb}} ต่างกัน {{th_ratio_price}} เท่า

ข้อควรรู้:
- วัดต้นทุน ไม่ใช่คุณภาพคำตอบ โมเดลที่ใช้ token มากกว่าอาจตอบไทยได้ดีกว่าก็ได้
- token มากกว่าไม่ได้แปลว่าแพงกว่าเสมอ งานเดียวกัน {{th_counter_more}} ({{th_counter_more_thb}}) จ่ายน้อยกว่า {{th_counter_fewer}} ({{th_counter_fewer_thb}}) เพราะราคาต่อ token ต่างกัน
- ขนาดงานตัวอย่างเป็นสมมติฐาน หน้าเว็บมีตัวคำนวณให้ใส่ตัวเลขของงานตัวเอง
- โมเดลเปิดไม่มีราคาต่อ token ของตัวเอง ผมรายงานเฉพาะจำนวน token และพบว่าโมเดลที่ต่อยอดจากโมเดลฐานจะรับ tokenizer ของโมเดลฐานมาด้วย

วัด {{th_n_models}} โมเดลด้วยคู่ประโยคไทย–อังกฤษ {{th_pairs}} คู่ (FLORES-200) ผ่าน endpoint นับ token ทางการ ราคา ณ {{th_date_prices}} โค้ดและข้อมูลดิบเปิดทั้งหมด รันซ้ำได้ ถ้าเจอจุดที่วัดผิดบอกได้เลยครับ

หน้าเว็บ + ตัวคำนวณ: {{site_url}}
โค้ดและวิธีวัด: {{clone_url}}

#ภาษีภาษา #ThaiTokenTax
```

## Show HN

Title (limit 80 characters):

```
Show HN: Thai Token Tax – Thai takes {{ratio_gpt}}x the tokens on Claude as on GPT
```

Link: `{{site_url}}`

First comment:

```
I wanted to know what Thai text costs on LLM APIs, measured rather than guessed from one prompt.

What it does: counts the same {{pairs}} parallel Thai–English sentences (FLORES-200 devtest) with the tokenizer of {{n_models}} models, {{n_groups}} distinct tokenizers in the end. Claude, GPT and Gemini go through the vendors' token-counting endpoints; open models through their tokenizer.json.

Result: per 1,000 Thai characters, {{claude_1k}} tokens on current Claude models, {{gpt_1k}} on GPT-5.x/6, {{gemini_1k}} on Gemini 3.x. At the same list price that is the ratio of the bills.

Things that surprised me:

- The within-model "Thai / English" ratio is not comparable across models. From {{gen_old}} to {{gen_new}} it dropped from {{gen_old_premium}} to {{gen_new_premium}}, but Thai barely moved ({{gen_old_thai}} → {{gen_new_thai}} tokens per 1,000 characters). English went from {{gen_old_english}} to {{gen_new_english}}.
- The counting endpoints include a constant framing overhead per request. I measure it, subtract it, and test that it is constant across lengths and languages. For Claude I also compared count_tokens with billed usage on {{bill_texts}} real requests: equal on every one (single-message requests only).
- Several open models give identical counts on every sentence, because fine-tunes inherit the base tokenizer.

Limits: this is cost, not answer quality. FLORES is news and encyclopedia prose, so chat text may tokenize at a different rate. Output tokens are assumed to follow the input rate. Prices are list prices as of {{date_prices}}.

Everything on the page is generated from the raw result files, and the local tokenizers rerun from a fresh clone without any key. Repo: {{clone_url}}

I would like to hear where the method is weak.
```
