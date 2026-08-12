---
license: mit
language:
- ar
- de
- en
- es
- fr
- hi
- id
- it
- ja
- ms
- nl
- pl
- pt
- ru
- th
- tl
- vi
- zh
pretty_name: I-Matrix Calibration Dataset
size_categories:
- 10K<n<100K
task_categories:
- text-generation
---

# Importance Matrix Calibration Datasets

This repository provides calibration datasets used to generate importance matrices ([imatrix](https://github.com/ggml-org/llama.cpp/tree/master/tools/imatrix)), which are required to minimize errors when quantizing models with [LLaMA C++](https://github.com/ggml-org/llama.cpp).

The `llama-imatrix` program cannot handle parquet files directly and thus requires them to be converted into text format first. There are many ways to do this but a simple approach is to use [DuckDB](https://duckdb.org/) with the following command: `duckdb -noheader -ascii -c "SELECT content FROM 'tools_micro.parquet';" > tools_micro.txt`

## Code calibration datasets

This dataset consists of cleaned and de-duplicated code prompts and is available in six sizes, ranging from `huge` (~ 200,000 lines equivalent to approx. 14.5M tokens), to `micro` (~ 6,200 lines and 2.4M tokens avg).

Original data sourced from [Vezora/Open-Critic-GPT](https://huggingface.co/datasets/Vezora/Open-Critic-GPT), [OpenCoder-LLM/opc-sft-stage2](https://huggingface.co/datasets/OpenCoder-LLM/opc-sft-stage2), [ise-uiuc/Magicoder-Evol-Instruct-110K](https://huggingface.co/datasets/ise-uiuc/Magicoder-Evol-Instruct-110K), and [Multilingual-Multimodal-NLP/McEval-Instruct](https://huggingface.co/datasets/Multilingual-Multimodal-NLP/McEval-Instruct)

| File                                 | Language |   Lines |
| ------------------------------------ | -------- | ------: |
| [code_huge](./code_huge.parquet)     | English  | 200,000 |
| [code_large](./code_large.parquet)   | English  | 100,000 |
| [code_medium](./code_medium.parquet) | English  |  50,000 |
| [code_small](./code_small.parquet)   | English  |  25,000 |
| [code_tiny](./code_tiny.parquet)     | English  |  12,500 |
| [code_micro](./code_micro.parquet)   | English  |   6,250 |

## Math calibration datasets

This dataset consists of cleaned and de-duplicated math prompts and is available in six sizes, ranging from `huge` (~ 200,000 lines equivalent to approx. 6 million), to `micro` (~ 6,250 lines and 0.9 million tokens avg).

Original data sourced from [nvidia/OpenMathInstruct-2](https://huggingface.co/datasets/nvidia/OpenMathInstruct-2)

| File                                 | Language |   Lines |
| ------------------------------------ | -------- | ------: |
| [math_huge](./math_huge.parquet)     | English  | 200,000 |
| [math_large](./math_large.parquet)   | English  | 100,000 |
| [math_medium](./math_medium.parquet) | English  |  50,000 |
| [math_small](./math_small.parquet)   | English  |  25,000 |
| [math_tiny](./math_tiny.parquet)     | English  |  12,500 |
| [math_micro](./math_micro.parquet)   | English  |   6,250 |

## Tools calibration datasets

This dataset consists of cleaned and de-duplicated tool prompts and is available in six sizes, ranging from `huge` (~ 100,000 lines equivalent to approx. 10 million tokens), to `micro` (~ 3,100 lines and 1 million tokens).

Original data sourced from [BitAgent/tool_calling](https://huggingface.co/datasets/BitAgent/tool_calling) and [JungHun/Efficient_ToolCalling](https://huggingface.co/datasets/JungHun/Efficient_ToolCalling)

| File                                   | Language |   Lines |
| -------------------------------------- | -------- | ------: |
| [tools_huge](./tools_huge.parquet)     | English  | 100,000 |
| [tools_large](./tools_large.parquet)   | English  |  50,000 |
| [tools_medium](./tools_medium.parquet) | English  |  25,000 |
| [tools_small](./tools_small.parquet)   | English  |  12,500 |
| [tools_tiny](./tools_tiny.parquet)     | English  |   6,250 |
| [tools_micro](./tools_micro.parquet)   | English  |   3,125 |

## Language calibration datasets

This dataset consists of cleaned and de-duplicated text prompts for 18 different languages. Each language file is available in five sizes, ranging from `large` (~ 25,000 lines equivalent to approx. 725K tokens), to `micro` (~ 1,600 lines and 125K tokens avg).

Original data sourced from [HuggingFaceFW/fineweb](https://huggingface.co/datasets/HuggingFaceFW/fineweb), [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2), and [Common Crawl](https://commoncrawl.org/)

| File                                       | Language   |  Lines |
| ------------------------------------------ | ---------- | -----: |
| [text_ar_large](./text_ar_large.parquet)   | Arabic     | 25,000 |
| [text_ar_medium](./text_ar_medium.parquet) | Arabic     | 12,500 |
| [text_ar_small](./text_ar_small.parquet)   | Arabic     |  6,250 |
| [text_ar_tiny](./text_ar_tiny.parquet)     | Arabic     |  3,125 |
| [text_ar_micro](./text_ar_micro.parquet)   | Arabic     |  1,562 |
| [text_cn_large](./text_cn_large.parquet)   | Chinese    | 25,000 |
| [text_cn_medium](./text_cn_medium.parquet) | Chinese    | 12,500 |
| [text_cn_small](./text_cn_small.parquet)   | Chinese    |  6,250 |
| [text_cn_tiny](./text_cn_tiny.parquet)     | Chinese    |  3,125 |
| [text_cn_micro](./text_cn_micro.parquet)   | Chinese    |  1,562 |
| [text_de_large](./text_de_large.parquet)   | German     | 25,000 |
| [text_de_medium](./text_de_medium.parquet) | German     | 12,500 |
| [text_de_small](./text_de_small.parquet)   | German     |  6,250 |
| [text_de_tiny](./text_de_tiny.parquet)     | German     |  3,125 |
| [text_de_micro](./text_de_micro.parquet)   | German     |  1,562 |
| [text_en_large](./text_en_large.parquet)   | English    | 25,000 |
| [text_en_medium](./text_en_medium.parquet) | English    | 12,500 |
| [text_en_small](./text_en_small.parquet)   | English    |  6,250 |
| [text_en_tiny](./text_en_tiny.parquet)     | English    |  3,125 |
| [text_en_micro](./text_en_micro.parquet)   | English    |  1,562 |
| [text_es_large](./text_es_large.parquet)   | Spanish    | 25,000 |
| [text_es_medium](./text_es_medium.parquet) | Spanish    | 12,500 |
| [text_es_small](./text_es_small.parquet)   | Spanish    |  6,250 |
| [text_es_tiny](./text_es_tiny.parquet)     | Spanish    |  3,125 |
| [text_es_micro](./text_es_micro.parquet)   | Spanish    |  1,562 |
| [text_fr_large](./text_fr_large.parquet)   | French     | 25,000 |
| [text_fr_medium](./text_fr_medium.parquet) | French     | 12,500 |
| [text_fr_small](./text_fr_small.parquet)   | French     |  6,250 |
| [text_fr_tiny](./text_fr_tiny.parquet)     | French     |  3,125 |
| [text_fr_micro](./text_fr_micro.parquet)   | French     |  1,562 |
| [text_hi_large](./text_hi_large.parquet)   | Hindi      | 25,000 |
| [text_hi_medium](./text_hi_medium.parquet) | Hindi      | 12,500 |
| [text_hi_small](./text_hi_small.parquet)   | Hindi      |  6,250 |
| [text_hi_tiny](./text_hi_tiny.parquet)     | Hindi      |  3,125 |
| [text_hi_micro](./text_hi_micro.parquet)   | Hindi      |  1,562 |
| [text_id_large](./text_id_large.parquet)   | Indonesian | 24,999 |
| [text_id_medium](./text_id_medium.parquet) | Indonesian | 12,500 |
| [text_id_small](./text_id_small.parquet)   | Indonesian |  6,250 |
| [text_id_tiny](./text_id_tiny.parquet)     | Indonesian |  3,125 |
| [text_id_micro](./text_id_micro.parquet)   | Indonesian |  1,562 |
| [text_it_large](./text_it_large.parquet)   | Italian    | 25,000 |
| [text_it_medium](./text_it_medium.parquet) | Italian    | 12,500 |
| [text_it_small](./text_it_small.parquet)   | Italian    |  6,250 |
| [text_it_tiny](./text_it_tiny.parquet)     | Italian    |  3,125 |
| [text_it_micro](./text_it_micro.parquet)   | Italian    |  1,562 |
| [text_jp_large](./text_jp_large.parquet)   | Japanese   | 25,000 |
| [text_jp_medium](./text_jp_medium.parquet) | Japanese   | 12,500 |
| [text_jp_small](./text_jp_small.parquet)   | Japanese   |  6,250 |
| [text_jp_tiny](./text_jp_tiny.parquet)     | Japanese   |  3,125 |
| [text_jp_micro](./text_jp_micro.parquet)   | Japanese   |  1,562 |
| [text_mm_large](./text_mm_large.parquet)   | Burmese    | 25,000 |
| [text_mm_medium](./text_mm_medium.parquet) | Burmese    | 12,500 |
| [text_mm_small](./text_mm_small.parquet)   | Burmese    |  6,250 |
| [text_mm_tiny](./text_mm_tiny.parquet)     | Burmese    |  3,125 |
| [text_mm_micro](./text_mm_micro.parquet)   | Burmese    |  1,562 |
| [text_nl_large](./text_nl_large.parquet)   | Dutch      | 25,000 |
| [text_nl_medium](./text_nl_medium.parquet) | Dutch      | 12,500 |
| [text_nl_small](./text_nl_small.parquet)   | Dutch      |  6,250 |
| [text_nl_tiny](./text_nl_tiny.parquet)     | Dutch      |  3,125 |
| [text_nl_micro](./text_nl_micro.parquet)   | Dutch      |  1,562 |
| [text_ph_large](./text_ph_large.parquet)   | Filipino   | 25,000 |
| [text_ph_medium](./text_ph_medium.parquet) | Filipino   | 12,500 |
| [text_ph_small](./text_ph_small.parquet)   | Filipino   |  6,250 |
| [text_ph_tiny](./text_ph_tiny.parquet)     | Filipino   |  3,125 |
| [text_ph_micro](./text_ph_micro.parquet)   | Filipino   |  1,562 |
| [text_pl_large](./text_pl_large.parquet)   | Polish     | 25,000 |
| [text_pl_medium](./text_pl_medium.parquet) | Polish     | 12,500 |
| [text_pl_small](./text_pl_small.parquet)   | Polish     |  6,250 |
| [text_pl_tiny](./text_pl_tiny.parquet)     | Polish     |  3,125 |
| [text_pl_micro](./text_pl_micro.parquet)   | Polish     |  1,562 |
| [text_pt_large](./text_pt_large.parquet)   | Portuguese | 25,000 |
| [text_pt_medium](./text_pt_medium.parquet) | Portuguese | 12,500 |
| [text_pt_small](./text_pt_small.parquet)   | Portuguese |  6,250 |
| [text_pt_tiny](./text_pt_tiny.parquet)     | Portuguese |  3,125 |
| [text_pt_micro](./text_pt_micro.parquet)   | Portuguese |  1,562 |
| [text_ru_large](./text_ru_large.parquet)   | Russian    | 25,000 |
| [text_ru_medium](./text_ru_medium.parquet) | Russian    | 12,500 |
| [text_ru_small](./text_ru_small.parquet)   | Russian    |  6,250 |
| [text_ru_tiny](./text_ru_tiny.parquet)     | Russian    |  3,125 |
| [text_ru_micro](./text_ru_micro.parquet)   | Russian    |  1,562 |
| [text_th_large](./text_th_large.parquet)   | Thai       | 25,000 |
| [text_th_medium](./text_th_medium.parquet) | Thai       | 12,500 |
| [text_th_small](./text_th_small.parquet)   | Thai       |  6,250 |
| [text_th_tiny](./text_th_tiny.parquet)     | Thai       |  3,125 |
| [text_th_micro](./text_th_micro.parquet)   | Thai       |  1,562 |
| [text_vn_large](./text_vn_large.parquet)   | Vietnamese | 25,000 |
| [text_vn_medium](./text_vn_medium.parquet) | Vietnamese | 12,500 |
| [text_vn_small](./text_vn_small.parquet)   | Vietnamese |  6,250 |
| [text_vn_tiny](./text_vn_tiny.parquet)     | Vietnamese |  3,125 |
| [text_vn_micro](./text_vn_micro.parquet)   | Vietnamese |  1,562 |

## Language groups

In addition to single language files, the dataset includes randomized and files by `language family/region` and `all languages in dataset`

### All languages (all)

| File                                         |  Lines |
| -------------------------------------------- | -----: |
| [text_all_large](./text_all_large.parquet)   | 60,000 |
| [text_all_medium](./text_all_medium.parquet) | 30,000 |
| [text_all_small](./text_all_small.parquet)   | 15,009 |
| [text_all_tiny](./text_all_tiny.parquet)     |  7,496 |
| [text_all_micro](./text_all_micro.parquet)   |  3,748 |

### European languages: English, French, German, Italian, Portuguese & Spanish (eur)

| File                                         |  Lines |
| -------------------------------------------- | -----: |
| [text_eur_large](./text_eur_large.parquet)   | 60,000 |
| [text_eur_medium](./text_eur_medium.parquet) | 30,000 |
| [text_eur_small](./text_eur_small.parquet)   | 14,998 |
| [text_eur_tiny](./text_eur_tiny.parquet)     |  7,500 |
| [text_eur_micro](./text_eur_micro.parquet)   |  3,750 |

### Germanic languages: Dutch, English & German (gem)

| File                                         |  Lines |
| -------------------------------------------- | -----: |
| [text_gem_large](./text_gem_large.parquet)   | 60,000 |
| [text_gem_medium](./text_gem_medium.parquet) | 30,000 |
| [text_gem_small](./text_gem_small.parquet)   | 15,001 |
| [text_gem_tiny](./text_gem_tiny.parquet)     |  7,500 |
| [text_gem_micro](./text_gem_micro.parquet)   |  3,750 |

### Romance languages: French, Italian, Portuguese & Spanish (roa)

| File                                         |  Lines |
| -------------------------------------------- | -----: |
| [text_roa_large](./text_roa_large.parquet)   | 60,000 |
| [text_roa_medium](./text_roa_medium.parquet) | 30,000 |
| [text_roa_small](./text_roa_small.parquet)   | 15,000 |
| [text_roa_tiny](./text_roa_tiny.parquet)     |  7,500 |
| [text_roa_micro](./text_roa_micro.parquet)   |  3,752 |

### Rest of World: Arabic, Chinese, Hindi & Japanese (row)

| File                                         |  Lines |
| -------------------------------------------- | -----: |
| [text_row_large](./text_row_large.parquet)   | 60,000 |
| [text_row_medium](./text_row_medium.parquet) | 30,000 |
| [text_row_small](./text_row_small.parquet)   | 15,000 |
| [text_row_tiny](./text_row_tiny.parquet)     |  7,500 |
| [text_row_micro](./text_row_micro.parquet)   |  3,752 |

### Southeast Asia languages: Burmese, Filipino, Indonesian, Thai & Vietnamese (sea)

| File                                         |  Lines |
| -------------------------------------------- | -----: |
| [text_sea_large](./text_sea_large.parquet)   | 60,000 |
| [text_sea_medium](./text_sea_medium.parquet) | 30,000 |
| [text_sea_small](./text_sea_small.parquet)   | 15,000 |
| [text_sea_tiny](./text_sea_tiny.parquet)     |  7,500 |
| [text_sea_micro](./text_sea_micro.parquet)   |  3,750 |

### Slavic languages: Polish & Russian (sla)

| File                                         |  Lines |
| -------------------------------------------- | -----: |
| [text_sla_large](./text_sla_large.parquet)   | 50,000 |
| [text_sla_medium](./text_sla_medium.parquet) | 30,000 |
| [text_sla_small](./text_sla_small.parquet)   | 15,000 |
| [text_sla_tiny](./text_sla_tiny.parquet)     |  7,500 |
| [text_sla_micro](./text_sla_micro.parquet)   |  3,750 |

## Math & Code calibration datasets

This dataset combines math and code prompts into single calibration files.

| File                                                             |   Lines |
| ---------------------------------------------------------------- | ------: |
| [combined_math_code_huge](./combined_math_code_huge.parquet)     | 199,999 |
| [combined_math_code_large](./combined_math_code_large.parquet)   | 100,000 |
| [combined_math_code_medium](./combined_math_code_medium.parquet) |  49,998 |
| [combined_math_code_micro](./combined_math_code_micro.parquet)   |   6,250 |
| [combined_math_code_small](./combined_math_code_small.parquet)   |  25,000 |
| [combined_math_code_tiny](./combined_math_code_tiny.parquet)     |  12,500 |

## Tool, Math, Code and Language calibration datasets

This dataset combines tool, math, code and language prompts into single calibration files.

| File                                               | Language   |   Lines |
| -------------------------------------------------- | ---------- | ------: |
| [combined_ar_huge](./combined_ar_huge.parquet)     | Arabic     | 100,000 |
| [combined_ar_large](./combined_ar_large.parquet)   | Arabic     |  50,000 |
| [combined_ar_medium](./combined_ar_medium.parquet) | Arabic     |  25,000 |
| [combined_ar_small](./combined_ar_small.parquet)   | Arabic     |  12,500 |
| [combined_ar_tiny](./combined_ar_tiny.parquet)     | Arabic     |   6,248 |
| [combined_ar_micro](./combined_ar_micro.parquet)   | Arabic     |   3,124 |
| [combined_cn_huge](./combined_cn_huge.parquet)     | Chinese    | 100,000 |
| [combined_cn_large](./combined_cn_large.parquet)   | Chinese    |  50,000 |
| [combined_cn_medium](./combined_cn_medium.parquet) | Chinese    |  25,000 |
| [combined_cn_small](./combined_cn_small.parquet)   | Chinese    |  12,500 |
| [combined_cn_tiny](./combined_cn_tiny.parquet)     | Chinese    |   6,248 |
| [combined_cn_micro](./combined_cn_micro.parquet)   | Chinese    |   3,124 |
| [combined_de_huge](./combined_de_huge.parquet)     | German     | 100,000 |
| [combined_de_large](./combined_de_large.parquet)   | German     |  50,000 |
| [combined_de_medium](./combined_de_medium.parquet) | German     |  25,000 |
| [combined_de_small](./combined_de_small.parquet)   | German     |  12,500 |
| [combined_de_tiny](./combined_de_tiny.parquet)     | German     |   6,248 |
| [combined_de_micro](./combined_de_micro.parquet)   | German     |   3,124 |
| [combined_en_huge](./combined_en_huge.parquet)     | English    |  99,999 |
| [combined_en_large](./combined_en_large.parquet)   | English    |  50,000 |
| [combined_en_medium](./combined_en_medium.parquet) | English    |  25,000 |
| [combined_en_small](./combined_en_small.parquet)   | English    |  12,500 |
| [combined_en_tiny](./combined_en_tiny.parquet)     | English    |   6,248 |
| [combined_en_micro](./combined_en_micro.parquet)   | English    |   3,124 |
| [combined_es_huge](./combined_es_huge.parquet)     | Spanish    | 100,000 |
| [combined_es_large](./combined_es_large.parquet)   | Spanish    |  50,000 |
| [combined_es_medium](./combined_es_medium.parquet) | Spanish    |  25,000 |
| [combined_es_small](./combined_es_small.parquet)   | Spanish    |  12,500 |
| [combined_es_tiny](./combined_es_tiny.parquet)     | Spanish    |   6,248 |
| [combined_es_micro](./combined_es_micro.parquet)   | Spanish    |   3,124 |
| [combined_fr_huge](./combined_fr_huge.parquet)     | French     | 100,000 |
| [combined_fr_large](./combined_fr_large.parquet)   | French     |  50,000 |
| [combined_fr_medium](./combined_fr_medium.parquet) | French     |  25,000 |
| [combined_fr_small](./combined_fr_small.parquet)   | French     |  12,500 |
| [combined_fr_tiny](./combined_fr_tiny.parquet)     | French     |   6,248 |
| [combined_fr_micro](./combined_fr_micro.parquet)   | French     |   3,124 |
| [combined_hi_huge](./combined_hi_huge.parquet)     | Hindi      | 100,000 |
| [combined_hi_large](./combined_hi_large.parquet)   | Hindi      |  50,000 |
| [combined_hi_medium](./combined_hi_medium.parquet) | Hindi      |  25,000 |
| [combined_hi_small](./combined_hi_small.parquet)   | Hindi      |  12,500 |
| [combined_hi_tiny](./combined_hi_tiny.parquet)     | Hindi      |   6,248 |
| [combined_hi_micro](./combined_hi_micro.parquet)   | Hindi      |   3,124 |
| [combined_id_huge](./combined_id_huge.parquet)     | Indonesian |  99,999 |
| [combined_id_large](./combined_id_large.parquet)   | Indonesian |  50,000 |
| [combined_id_medium](./combined_id_medium.parquet) | Indonesian |  25,000 |
| [combined_id_small](./combined_id_small.parquet)   | Indonesian |  12,500 |
| [combined_id_tiny](./combined_id_tiny.parquet)     | Indonesian |   6,248 |
| [combined_id_micro](./combined_id_micro.parquet)   | Indonesian |   3,124 |
| [combined_it_huge](./combined_it_huge.parquet)     | Italian    | 100,000 |
| [combined_it_large](./combined_it_large.parquet)   | Italian    |  50,000 |
| [combined_it_medium](./combined_it_medium.parquet) | Italian    |  25,000 |
| [combined_it_small](./combined_it_small.parquet)   | Italian    |  12,500 |
| [combined_it_tiny](./combined_it_tiny.parquet)     | Italian    |   6,248 |
| [combined_it_micro](./combined_it_micro.parquet)   | Italian    |   3,124 |
| [combined_jp_huge](./combined_jp_huge.parquet)     | Japanese   | 100,000 |
| [combined_jp_large](./combined_jp_large.parquet)   | Japanese   |  50,000 |
| [combined_jp_medium](./combined_jp_medium.parquet) | Japanese   |  25,000 |
| [combined_jp_small](./combined_jp_small.parquet)   | Japanese   |  12,500 |
| [combined_jp_tiny](./combined_jp_tiny.parquet)     | Japanese   |   6,248 |
| [combined_jp_micro](./combined_jp_micro.parquet)   | Japanese   |   3,124 |
| [combined_mm_huge](./combined_mm_huge.parquet)     | Burmese    | 100,000 |
| [combined_mm_large](./combined_mm_large.parquet)   | Burmese    |  50,000 |
| [combined_mm_medium](./combined_mm_medium.parquet) | Burmese    |  25,000 |
| [combined_mm_small](./combined_mm_small.parquet)   | Burmese    |  12,500 |
| [combined_mm_tiny](./combined_mm_tiny.parquet)     | Burmese    |   6,248 |
| [combined_mm_micro](./combined_mm_micro.parquet)   | Burmese    |   3,124 |
| [combined_nl_huge](./combined_nl_huge.parquet)     | Dutch      | 100,000 |
| [combined_nl_large](./combined_nl_large.parquet)   | Dutch      |  50,000 |
| [combined_nl_medium](./combined_nl_medium.parquet) | Dutch      |  25,000 |
| [combined_nl_small](./combined_nl_small.parquet)   | Dutch      |  12,500 |
| [combined_nl_tiny](./combined_nl_tiny.parquet)     | Dutch      |   6,248 |
| [combined_nl_micro](./combined_nl_micro.parquet)   | Dutch      |   3,124 |
| [combined_ph_huge](./combined_ph_huge.parquet)     | Filipino   | 100,000 |
| [combined_ph_large](./combined_ph_large.parquet)   | Filipino   |  49,999 |
| [combined_ph_medium](./combined_ph_medium.parquet) | Filipino   |  25,000 |
| [combined_ph_small](./combined_ph_small.parquet)   | Filipino   |  12,500 |
| [combined_ph_tiny](./combined_ph_tiny.parquet)     | Filipino   |   6,248 |
| [combined_ph_micro](./combined_ph_micro.parquet)   | Filipino   |   3,124 |
| [combined_pl_huge](./combined_pl_huge.parquet)     | Polish     | 100,000 |
| [combined_pl_large](./combined_pl_large.parquet)   | Polish     |  50,000 |
| [combined_pl_medium](./combined_pl_medium.parquet) | Polish     |  25,000 |
| [combined_pl_small](./combined_pl_small.parquet)   | Polish     |  12,500 |
| [combined_pl_tiny](./combined_pl_tiny.parquet)     | Polish     |   6,248 |
| [combined_pl_micro](./combined_pl_micro.parquet)   | Polish     |   3,124 |
| [combined_pt_huge](./combined_pt_huge.parquet)     | Portuguese | 100,000 |
| [combined_pt_large](./combined_pt_large.parquet)   | Portuguese |  50,000 |
| [combined_pt_medium](./combined_pt_medium.parquet) | Portuguese |  25,000 |
| [combined_pt_small](./combined_pt_small.parquet)   | Portuguese |  12,500 |
| [combined_pt_tiny](./combined_pt_tiny.parquet)     | Portuguese |   6,248 |
| [combined_pt_micro](./combined_pt_micro.parquet)   | Portuguese |   3,124 |
| [combined_ru_huge](./combined_ru_huge.parquet)     | Russian    |  99,999 |
| [combined_ru_large](./combined_ru_large.parquet)   | Russian    |  50,000 |
| [combined_ru_medium](./combined_ru_medium.parquet) | Russian    |  25,000 |
| [combined_ru_small](./combined_ru_small.parquet)   | Russian    |  12,500 |
| [combined_ru_tiny](./combined_ru_tiny.parquet)     | Russian    |   6,248 |
| [combined_ru_micro](./combined_ru_micro.parquet)   | Russian    |   3,124 |
| [combined_th_huge](./combined_th_huge.parquet)     | Thai       | 100,000 |
| [combined_th_large](./combined_th_large.parquet)   | Thai       |  50,000 |
| [combined_th_medium](./combined_th_medium.parquet) | Thai       |  25,000 |
| [combined_th_small](./combined_th_small.parquet)   | Thai       |  12,500 |
| [combined_th_tiny](./combined_th_tiny.parquet)     | Thai       |   6,248 |
| [combined_th_micro](./combined_th_micro.parquet)   | Thai       |   3,124 |
| [combined_vn_huge](./combined_vn_huge.parquet)     | Vietnamese |  99,999 |
| [combined_vn_large](./combined_vn_large.parquet)   | Vietnamese |  50,000 |
| [combined_vn_medium](./combined_vn_medium.parquet) | Vietnamese |  25,000 |
| [combined_vn_small](./combined_vn_small.parquet)   | Vietnamese |  12,499 |
| [combined_vn_tiny](./combined_vn_tiny.parquet)     | Vietnamese |   6,248 |
| [combined_vn_micro](./combined_vn_micro.parquet)   | Vietnamese |   3,124 |

## Tool, Math, Code and Language groups calibration datasets

In addition to single tool, math, code and language files, the dataset includes combined and randomized files by `language family/region` and `all languages in dataset`

### All languages (all)

| File                                                 |   Lines |
| ---------------------------------------------------- | ------: |
| [combined_all_huge](./combined_all_huge.parquet)     | 100,001 |
| [combined_all_large](./combined_all_large.parquet)   |  50,001 |
| [combined_all_medium](./combined_all_medium.parquet) |  24,990 |
| [combined_all_small](./combined_all_small.parquet)   |  12,495 |
| [combined_all_tiny](./combined_all_tiny.parquet)     |   6,258 |
| [combined_all_micro](./combined_all_micro.parquet)   |   3,129 |

### European languages: English, French, German, Italian, Portuguese & Spanish (eur)

| File                                                 |  Lines |
| ---------------------------------------------------- | -----: |
| [combined_eur_huge](./combined_eur_huge.parquet)     | 99,999 |
| [combined_eur_large](./combined_eur_large.parquet)   | 50,004 |
| [combined_eur_medium](./combined_eur_medium.parquet) | 25,002 |
| [combined_eur_small](./combined_eur_small.parquet)   | 12,501 |
| [combined_eur_tiny](./combined_eur_tiny.parquet)     |  6,246 |
| [combined_eur_micro](./combined_eur_micro.parquet)   |  3,123 |

### Germanic languages: Dutch, English & German (gem)

| File                                                 |   Lines |
| ---------------------------------------------------- | ------: |
| [combined_gem_huge](./combined_gem_huge.parquet)     | 100,002 |
| [combined_gem_large](./combined_gem_large.parquet)   |  49,998 |
| [combined_gem_medium](./combined_gem_medium.parquet) |  25,002 |
| [combined_gem_small](./combined_gem_small.parquet)   |  12,498 |
| [combined_gem_tiny](./combined_gem_tiny.parquet)     |   6,252 |
| [combined_gem_micro](./combined_gem_micro.parquet)   |   3,126 |

### Romance languages: French, Italian, Portuguese & Spanish (roa)

| File                                                 |   Lines |
| ---------------------------------------------------- | ------: |
| [combined_roa_huge](./combined_roa_huge.parquet)     | 100,001 |
| [combined_roa_large](./combined_roa_large.parquet)   |  50,001 |
| [combined_roa_medium](./combined_roa_medium.parquet) |  24,997 |
| [combined_roa_small](./combined_roa_small.parquet)   |  12,502 |
| [combined_roa_tiny](./combined_roa_tiny.parquet)     |   6,251 |
| [combined_roa_micro](./combined_roa_micro.parquet)   |   3,122 |

### Rest of World: Arabic, Chinese, Hindi & Japanese (row)

| File                                                 |   Lines |
| ---------------------------------------------------- | ------: |
| [combined_row_huge](./combined_row_huge.parquet)     | 100,002 |
| [combined_row_large](./combined_row_large.parquet)   |  50,001 |
| [combined_row_medium](./combined_row_medium.parquet) |  24,997 |
| [combined_row_small](./combined_row_small.parquet)   |  12,502 |
| [combined_row_tiny](./combined_row_tiny.parquet)     |   6,251 |
| [combined_row_micro](./combined_row_micro.parquet)   |   3,122 |

### Southeast Asia languages: Burmese, Filipino, Indonesian, Thai & Vietnamese (sea)

| File                                                 |  Lines |
| ---------------------------------------------------- | -----: |
| [combined_sea_huge](./combined_sea_huge.parquet)     | 99,999 |
| [combined_sea_large](./combined_sea_large.parquet)   | 50,000 |
| [combined_sea_medium](./combined_sea_medium.parquet) | 25,000 |
| [combined_sea_small](./combined_sea_small.parquet)   | 12,496 |
| [combined_sea_tiny](./combined_sea_tiny.parquet)     |  6,248 |
| [combined_sea_micro](./combined_sea_micro.parquet)   |  3,128 |

### Slavic languages: Polish & Russian (sla)

| File                                                 |   Lines |
| ---------------------------------------------------- | ------: |
| [combined_sla_huge](./combined_sla_huge.parquet)     | 100,000 |
| [combined_sla_large](./combined_sla_large.parquet)   |  49,999 |
| [combined_sla_medium](./combined_sla_medium.parquet) |  25,000 |
| [combined_sla_small](./combined_sla_small.parquet)   |  12,500 |
| [combined_sla_tiny](./combined_sla_tiny.parquet)     |   6,250 |
| [combined_sla_micro](./combined_sla_micro.parquet)   |   3,125 |
