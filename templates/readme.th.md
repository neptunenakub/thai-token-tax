# ภาษีภาษา · Thai Token Tax

**ราคาป้ายเท่ากัน แต่งานภาษาไทยบน Claude จ่ายแพงกว่า GPT {{ratio_price}} เท่า**
ค่า API คิดตามจำนวน token และข้อความไทยเดียวกันใช้ token บน Claude มากกว่า GPT {{ratio_gpt}} เท่า
มากกว่า Gemini 3.x {{ratio_gemini}} เท่า ตัวอย่าง: {{scenario}} ที่ราคาป้ายเท่ากัน
({{pair1_in}} ขาเข้า / {{pair1_out}} ขาออก ต่อล้าน token) {{pair1_a}} จ่าย {{pair1_a_thb}} ส่วน {{pair1_b}}
จ่าย {{pair1_b_thb}}

{{table_headline}}

งานนี้วัด**ต้นทุน ไม่ใช่คุณภาพคำตอบ** โมเดลที่ใช้ token มากกว่าอาจตอบภาษาไทยได้ดีกว่าก็ได้
วัด {{n_models}} โมเดล ({{n_groups}} tokenizer) ด้วยคู่ประโยคไทย–อังกฤษ {{pairs}} คู่ (FLORES-200)
เมื่อ {{date_data}} ราคาป้ายจากหน้า pricing ทางการ ณ {{date_prices}}

รันซ้ำเอง:

```
git clone {{clone_url}} thai-token-tax && cd thai-token-tax
pip install -e .
ttt all --out rerun
```

[English](README.md) · [วิธีวัดและข้อจำกัด (อังกฤษ)](docs/methodology.md) · [ไฟล์ผลการวัด](results/) ·
หน้าเว็บพร้อมตัวคำนวณค่าใช้จ่าย: {{site_ref}}

---

## การรันซ้ำ

- ใช้ Python 3.11 ขึ้นไป (แนะนำให้ใช้ virtual environment) ไม่ต้องมี API key {{repo_url_note}}
- `ttt all` ดาวน์โหลด FLORES-200 (ประมาณ {{flores_mb}} MB) และไฟล์ tokenizer นับทุกประโยคด้วย tokenizer
  ทุกตัวที่รันในเครื่องได้ นับซ้ำด้วยวิธีที่สอง แล้วเขียน `rerun/summary_<date>.md`
- แถวที่ได้ต้องเท่ากับแถวที่มี source เป็น `open` ใน [`results/{{summary_md}}`](results/{{summary_md}})
  จำนวน token ทีละประโยคที่เผยแพร่อยู่ใน `results/{{counts_open}}`
- Claude, GPT และ Gemini นับผ่าน endpoint นับ token ทางการ ถ้าไม่มี `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
  และ `GEMINI_API_KEY` แหล่งเหล่านี้จะถูกรายงานว่าถูกบล็อกแล้วข้ามไป ส่วน repo บน Hugging Face
  ที่จำกัดการเข้าถึงต้องใช้ `HF_TOKEN` โมเดลที่วัดไม่ได้จะถูกบันทึกว่าถูกบล็อกพร้อมข้อความ error จริง
  ไม่มีการใช้ค่าประมาณแทน
- ไฟล์ผลไม่ถูกเขียนทับ ทุกครั้งที่รันจะได้ชุดใหม่ที่ระบุวันที่ ตัวอย่างจึงเขียนลง `rerun/`
  ส่วน `ttt prepare` (ขั้นแรกของ `ttt all`) จะเขียน `data/source.json` และ `data/normalization_log.json` ใหม่
  ซึ่งควรต่างจากเดิมแค่เวลาที่บันทึก
- รันเทสต์ (ไม่ใช้เน็ต ไม่ใช้ key): `pip install -e ".[dev]"` แล้ว `pytest -q`

## วัดอะไร และไม่ได้วัดอะไร

ให้ tokenizer ของแต่ละโมเดลนับเนื้อหาเดียวกันทั้งฉบับภาษาไทยและภาษาอังกฤษ ได้ตัวเลขสองตัว
ซึ่งตอบคำถามคนละข้อ:

- **token ต่อ 1,000 ตัวอักษรไทย** ใช้เทียบข้ามโมเดล: ข้อความไทยเดียวกัน ใช้กี่ token เมื่อคูณราคาจะได้ค่าใช้จ่าย
- **ไทย ÷ อังกฤษ** (premium) ใช้เทียบสองภาษาภายในโมเดลเดียวกัน พร้อมช่วงความเชื่อมั่น {{ci_level}}%
  จาก bootstrap ค่านี้เทียบข้ามโมเดลไม่ได้ เพราะแต่ละโมเดลใช้ token กับภาษาอังกฤษไม่เท่ากัน
  ตัวอย่าง: จาก {{gen_old}} ไป {{gen_new}} ค่านี้ลดจาก {{gen_old_premium}} เหลือ {{gen_new_premium}}
  แต่ token ไทยต่อ 1,000 ตัวอักษรแทบไม่เปลี่ยน ({{gen_old_thai}} → {{gen_new_thai}})
  ส่วนภาษาอังกฤษเพิ่มจาก {{gen_old_english}} เป็น {{gen_new_english}}

ค่าใช้จ่ายเป็นบาท = token ที่วัดได้ × ราคาป้ายทางการ × อัตราแลกเปลี่ยนของ ธปท. คิดกับงานตัวอย่างซึ่งขนาดงานเป็นสมมติฐาน

ไม่ได้วัด: คุณภาพคำตอบ, ความเร็ว, reasoning/thinking token, prompt caching, ส่วนลด batch
และข้อความประเภทอื่นนอกจากประโยคของ FLORES-200 (แนวข่าวและสารานุกรม)

## ผลการวัด

### ข้อความไทยเดียวกัน ใช้กี่ token

{{table_groups}}

หนึ่งแถวคือหนึ่ง tokenizer โมเดลในแถวเดียวกันนับ token ได้เท่ากันทุกประโยค (โมเดลที่วัดแบบสุ่ม:
เท่ากันทุกประโยคในชุดสุ่ม) ตารางของทั้ง {{n_models}} โมเดลอยู่ที่
[`results/{{summary_md}}`](results/{{summary_md}})

{{thai_group_label}} นับ token ได้เท่ากัน คือ {{thai_group_1k}} token ต่อ 1,000 ตัวอักษรไทย
โมเดลไทยในกลุ่มนี้รับ tokenizer มาจากโมเดลฐาน

### ราคาป้ายเท่ากัน จ่ายไม่เท่ากัน

งานตัวอย่าง: {{scenario}}

{{table_pairs}}

### ทุกโมเดลที่มีราคา งานตัวอย่างเดียวกัน

{{table_costs}}

token มากกว่าไม่ได้แปลว่าแพงกว่าเสมอ: {{counter_more}} จ่าย {{counter_more_thb}} น้อยกว่า {{counter_fewer}}
ที่จ่าย {{counter_fewer_thb}} ทั้งที่ใช้ token ไทยมากกว่า ({{counter_more_1k}} เทียบกับ {{counter_fewer_1k}}
ต่อ 1,000 ตัวอักษร) เพราะราคาต่อ token ต่างกัน

โมเดลเปิดไม่มีราคาต่อ token ของตัวเอง จึงมีแต่จำนวน token งานตัวอย่างอื่นอยู่ใน
[`results/{{costs_md}}`](results/{{costs_md}}) และหน้าเว็บมีตัวคำนวณที่ปรับสมมติฐานได้

งานตัวอย่าง (เป็นสมมติฐาน จาก `registry/scenarios.toml` ขนาดเป็นจำนวนตัวอักษรไทย):

{{table_scenarios}}

### อยู่ในแผนแต่ยังไม่ได้วัด

{{table_blocked}}

## ข้อจำกัด

- เป็นต้นทุน token เท่านั้น ไม่ได้บอกคุณภาพคำตอบ
- จำนวน token วัดจาก FLORES-200 ซึ่งเป็นข้อความแนวข่าวและสารานุกรม ข้อความแชทหรือข้อความประเภทอื่นอาจถูกแบ่ง token ต่างออกไป
- FLORES มีคำแปลบางประโยคที่ความหมายไม่ตรงกับต้นฉบับ เราไม่ได้แก้ไขข้อมูล
- token ขาออกสมมติว่าใช้ token ต่อตัวอักษรเท่ากับข้อความขาเข้าของภาษาเดียวกัน
- ไม่รวม reasoning/thinking token, prompt caching, ส่วนลด batch, free tier และราคาช่วง context ยาว ใช้ราคาป้ายมาตรฐานเท่านั้น
- จำนวน token ของ Claude มาจาก `count_tokens` ซึ่ง Anthropic ระบุว่าเป็นค่าประมาณ การตรวจกับยอดคิดเงินจริง
  (คำขอที่เสียเงินจริง {{bill_texts}} ครั้งบน Claude ซึ่ง input token ที่ถูกคิดเงินเท่ากับผลของ `count_tokens` ทุกครั้ง)
  ครอบคลุมเฉพาะคำขอที่มีข้อความเดียว ไม่มี system prompt ไม่มี tools
- token โครงคำขอของ Claude ({{overheads}} token ต่อคำขอ) ถูกคิดเงินจริง แต่ไม่รวมอยู่ในตัวเลขเหล่านี้
- โมเดลเปิดไม่มีราคาต่อ token ของตัวเอง จึงรายงานเฉพาะจำนวน token
- "เนื้อหาเดียวกันเป็นภาษาอังกฤษ" คิดจากอัตราส่วนตัวอักษรอังกฤษต่อไทยที่วัดจาก FLORES-200 ({{en_per_th}} เท่า) ไม่ใช่จำนวนตัวอักษรเท่ากัน
- ขนาดงานในงานตัวอย่างเป็นสมมติฐาน ไม่ใช่ค่าที่วัด
- ราคาเปลี่ยนได้ ณ {{date_prices}} หน้า pricing ของ Google ระบุราคาที่มีวันสิ้นสุดสำหรับ:

{{list_price_end_dates}}

จุดอ่อนทั้งหมดของวิธีวัด และสิ่งที่จะทำให้ข้อสรุปเปลี่ยน อยู่ใน [`docs/methodology.md`](docs/methodology.md) (ภาษาอังกฤษ)

## เพิ่มโมเดลหรือภาษา

ทั้งสองอย่างแก้ที่ registry ไม่ต้องเขียนโค้ดใหม่

- **โมเดล:** เพิ่มบล็อก `[[model]]` หนึ่งบล็อกใน `registry/models.toml` (`id`, `family`, `counter`
  ใช้ `revision` เพื่อปักเวอร์ชัน repo บน Hugging Face และ `sample_of` เพื่อเทียบโมเดล API
  กับโมเดลที่วัดเต็มชุดด้วยชุดสุ่มที่กำหนดตายตัว) แล้วรัน `ttt count`, `ttt verify`, `ttt analyze`
  ถ้าต้องการราคา ให้เพิ่มแถวใน `registry/pricing.toml` แล้วรัน `ttt prices` และ `ttt cost`
  จากนั้นรัน `ttt site` และ `ttt docs`
- **ภาษา:** เพิ่มบล็อก `[[target]]` หนึ่งบล็อกที่ใช้รหัสภาษาของ FLORES-200 ใน `registry/languages.toml`
  แล้วรัน `ttt prepare` และขั้นตอนข้างบน คำสั่ง `prepare`, `count`, `verify` และ `analyze` รับทุกภาษาใน registry
  ตอนนี้รันแล้วเฉพาะภาษาไทย ส่วนตารางค่าใช้จ่าย หน้าเว็บ และ README นี้แสดงภาษาเป้าหมายภาษาเดียว

## โครงสร้าง repo

```
registry/              สิ่งที่วัด: โมเดล ภาษา แหล่งราคา งานตัวอย่าง ชื่อที่ใช้แสดง
src/thai_token_tax/    คำสั่ง `ttt`: prepare, count, verify, analyze, prices, cost, compare, site, docs
tests/                 pytest ไม่ใช้เน็ต
data/                  ที่มาของข้อมูลและ log ประโยคของ FLORES สร้างใหม่ในเครื่อง ไม่ได้ commit
results/               จำนวน token ดิบ ตารางสรุป ราคา ค่าใช้จ่าย ระบุวันที่ทุกไฟล์ latest.json ชี้ชุดล่าสุด
site/                  หน้าเว็บ static หน้าเดียว อ่าน site/data.json ที่ `ttt site` เขียน
templates/             ต้นฉบับของ README นี้และ docs/methodology.md ซึ่ง `ttt docs` เติมตัวเลขให้
docs/methodology.md    วิธีวัด ข้อจำกัด และสิ่งที่จะทำให้ข้อสรุปเปลี่ยน (ภาษาอังกฤษ)
blog/                  บทความ (ไทย อังกฤษ) และร่างโพสต์ สร้างแบบเดียวกับ README นี้
ARCHITECTURE.md        โครงสร้างของโค้ด
LOG.md                 บันทึกว่าแต่ละวันรันอะไร รวมถึงสิ่งที่ผิดพลาด
```

ไม่มีตัวเลขใดใน README นี้ เอกสารวิธีวัด หรือหน้าเว็บ ที่พิมพ์ด้วยมือ ทุกตัวสร้างจาก `results/`
และเทสต์จะไม่ผ่านถ้าเอกสารไม่ตรงกับผลชุดล่าสุด

## วันที่และแหล่งข้อมูล

- จำนวน token: วัดเมื่อ {{date_data}} (UTC) จำนวน token ดิบทีละประโยค: {{counts_files}}
- ราคา: หน้า pricing ทางการของ Anthropic, OpenAI และ Google ดึงเมื่อ {{date_prices}}
  บันทึกพร้อม hash ของหน้าใน `results/{{prices_json}}`
- อัตราแลกเปลี่ยน: {{rate}} บาทต่อดอลลาร์สหรัฐ อัตราแลกเปลี่ยนถัวเฉลี่ยถ่วงน้ำหนักระหว่างธนาคารของ ธปท.
  ณ {{date_rate}} (<{{rate_page}}>)
- ข้อมูล: FLORES-200 ชุด `devtest` ภาษาอังกฤษและไทย ชุดต้นฉบับของ Meta ส่วน FLORES+ รุ่น {{fp_version}}
  ต่างจากชุดนี้ {{fp_diff}} ประโยคหลัง normalize

## License

- โค้ด: {{lic_code}} ([LICENSE](LICENSE))
- ไฟล์ผลการวัด เอกสาร และข้อความบนหน้าเว็บ: {{lic_results}} ([LICENSE-DATA](LICENSE-DATA))
- FLORES-200 เป็นของ Meta (NLLB Team) ใช้ license {{lic_dataset}} repo นี้ไม่ได้เผยแพร่ประโยคของชุดข้อมูลซ้ำ
  คำสั่ง `ttt prepare` ดาวน์โหลดจากแหล่งต้นฉบับ ดู [`data/README.md`](data/README.md)

## การอ้างอิง

```
{{holder}}. Thai Token Tax: how many more tokens Thai text costs than the same
English text on major AI models. Version {{version}}, measured {{en_date_data}}. {{clone_url}}
```

ไฟล์สำหรับโปรแกรมอ้างอิง: [`CITATION.cff`](CITATION.cff)
