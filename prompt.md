# MES AI — Hardcoded Prompts & Instructions

This document lists every instruction string the backend sends to an LLM (Alibaba Bailian / DashScope), plus related static copy that shapes user-facing responses without an API call.

**Source files:** `orchestrator/prompts/intent.py`, `orchestrator/prompts/synthesis.py`, `orchestrator/intent_utils.py`, `orchestrator/report_generator.py`, `core/voice/transcribe.py`

---

## Pipeline overview

When a user sends a text query via `POST /api/v1/query`, the backend runs a **two-pass** flow:

| Pass | Purpose | LLM called? | Prompt language | Output language |
|------|---------|-------------|-----------------|-----------------|
| **1 — Intent extraction** | Classify intent + extract parameters (JSON) | Yes (Bailian) | **zh-CN or en-US** (matches `locale`) | JSON (English field names always) |
| **2 — Report synthesis** | Turn MCP tool `result` into Markdown report | Yes (Bailian) | **zh-CN or en-US** (matches `locale`) | **zh-CN or en-US** Markdown |

The frontend sends `locale` (`zh-CN` default, or `en-US`) on each query. Both LLM passes receive that value and use a **fully localized instruction template**. JSON property names in the intent pass remain **English** for parser compatibility.

Voice queries (`POST /api/v1/query/voice`) transcribe audio first, then use the same two-pass pipeline on the transcript.

---

## Pass 1 — Intent extraction prompt

**Function:** `build_intent_prompt()` in `orchestrator/prompts/intent.py`  
**Called from:** `parse_intent(query, context, locale)` in `orchestrator/intent_utils.py`  
**API:** `dashscope.Application.call(app_id=..., prompt=prompt_text, ...)`  
**Instruction language:** **zh-CN or en-US** (full template per locale)  
**Expected model output:** JSON only (English property names; enum values like `YIELD_AGGREGATION` unchanged)

### Chinese template opening (`locale == "zh-CN"`)

```
你是 MES 系统（生产、质量、仓储）的严格意图提取路由器。
你的唯一任务是对用户查询进行分类并提取结构化参数。
...
JSON 属性名必须保持英文，与下方规范完全一致。
...
当前时间：<ISO_TIMESTAMP>
用户问题：<USER_QUERY>
```

### English template opening (`locale == "en-US"`)

```
You are a strict Intent Extraction Router for an MES system (Production, Quality, Warehouse).
Your ONLY job is to classify the user query and extract structured parameters.
...
JSON property names must remain in English exactly as specified below.
...
Current datetime: <ISO_TIMESTAMP>
User Query: <USER_QUERY>
```

### Shared JSON schema (both locales — keys always English)

```
You are a strict Intent Extraction Router for an MES system (Production, Quality, Warehouse).
Your ONLY job is to classify the user query and extract structured parameters.
DO NOT output conversational text. DO NOT generate SQL.
DO NOT include workshop_id or any RBAC fields in your output.

CRITICAL — entity extraction rules:
- NEVER invent, assume, or default placeholder values for identifiers (e.g. do NOT use "L-01", "L-03", or any line unless the user explicitly stated it).
- If a field cannot be explicitly extracted from the user's text, set it to null in JSON.
- Only populate line_id, product_code, model_code, device_sn, batch_lot, material_batch, finished_lot, process_code, wh_code, and item_code when the user clearly mentions them.

Output ONLY a valid JSON object with these fields (use null for unknown entity fields):
{
  "intent": "<ENUM_LIST>",
  "yield_type": "equipment" | "reported" | null,
  "line_id": "string or null",
  "start_date": "YYYY-MM-DDTHH:MM:SS or null",
  "end_date": "YYYY-MM-DDTHH:MM:SS or null",
  "group_by": "daily" | "hourly" | "total" | null,
  "metric": "sum" | "average" | "achievement_rate" | null,
  "analysis_type": "volatility" | "below_standard" | "peak_hourly" | null,
  "threshold_percentage": number or null,
  "period_1_start": "YYYY-MM-DDTHH:MM:SS or null",
  "period_1_end": "YYYY-MM-DDTHH:MM:SS or null",
  "period_2_start": "YYYY-MM-DDTHH:MM:SS or null",
  "period_2_end": "YYYY-MM-DDTHH:MM:SS or null",
  "product_code": "string or null",
  "model_code": "string or null",
  "device_sn": "string or null",
  "batch_lot": "string or null",
  "material_batch": "string or null",
  "finished_lot": "string or null",
  "process_code": "string or null",
  "wh_code": "string or null",
  "item_code": "string or null",
  "export_format": "xlsx" | "pdf" | null,
  "doc_type": "sop" | "anomaly" | "solution" | null
}
Production intents: YIELD_AGGREGATION, YIELD_ANOMALIES, YIELD_COMPARISON,
  PRODUCTION_ROOT_CAUSE, PRODUCTION_SCHEDULING_OPT, PRODUCTION_CAPACITY_FORECAST,
  PRODUCTION_PRODUCT_YIELD, PRODUCTION_DEVICE_RATE, PRODUCTION_STANDARD_TIME
Quality intents: QUALITY_DEFECT_ANALYSIS, QUALITY_ROOT_CAUSE,
  QUALITY_ERROR_PREVENTION, QUALITY_EFFECTIVENESS_VERIFY
Warehouse intents: WAREHOUSE_INVENTORY_MONITOR, WAREHOUSE_INBOUND_OUTBOUND,
  WAREHOUSE_OBSOLETE_PROFILE, WAREHOUSE_TRACE_FORWARD, WAREHOUSE_TRACE_REVERSE
System intents: EXPORT_REPORT, CROSS_MODULE_ANALYSIS, UNKNOWN
Current datetime: <ISO_TIMESTAMP>
User Query: <USER_QUERY>
```

**Notes:**
- The user's natural-language query is appended as-is (any language the user typed).
- `MCPContext` is passed into the builder but **not** injected into the prompt text today.

---

## Pass 2 — Report synthesis prompt

**Function:** `build_synthesis_prompt()` in `orchestrator/prompts/synthesis.py`  
**Called from:** `generate_ai_analysis()` in `orchestrator/report_generator.py`  
**API:** `dashscope.Application.call(app_id=..., prompt=prompt_text, ...)`  
**Instruction language:** **Full zh-CN or en-US template** (not a mixed-language prompt)  
**Expected model output:** Markdown report in the same language as the instructions

### Chinese template (`locale == "zh-CN"`)

- Role and all 12 rules in Simplified Chinese
- Section headers: `## 用户问题`, `## 结构化数据库结果（JSON）`, `## 背景知识（RAG）`, `## 撰写要求`
- RAG empty placeholder: `（无补充知识库上下文。）`
- Closing: `请现在撰写 Markdown 报告：`

### English template (`locale == "en-US"`)

- Role and all 12 rules in English
- Section headers: `## User question`, `## Structured database result (JSON)`, etc.
- RAG empty placeholder: `(No supplementary knowledge-base context available.)`
- Closing: `Write the Markdown report now:`

### Example structure (dynamic parts: `{query}`, `{result_json}`, `{rag_block}`)

```
You are a Senior Manufacturing Data Analyst for an enterprise MES (Manufacturing Execution System).

Your task is to interpret structured database query results and write a clear, professional Markdown report for production, quality, or warehouse stakeholders.

## User question
<USER_QUERY>

## Structured database result (JSON)
```json
<MCP_TOOL_RESULT_JSON>
```

## Background knowledge (RAG)
<RAG_CONTEXT_OR_PLACEHOLDER>

## Instructions
1. Act as an expert analyst — explain what the numbers mean in plain language, not just restate them.
2. Highlight actionable insights: unusual drops, peak periods, threshold breaches, empty inventory, defect spikes, scheduling risks, traceability gaps, etc.
3. Use professional Markdown: a concise title (`##`), short executive summary, bullet points for key findings, and a brief recommendations section when appropriate.
4. Reference specific values from the JSON (dates, line IDs, quantities, rates, device serials) when they support your conclusions.
5. If the result is empty, zero, or contains no matching records, politely explain that no transaction records match that combination in the database log history. Suggest what the user might adjust (date range, line ID, device serial, product code).
6. Do NOT invent data that is not present in the JSON or RAG context.
7. Do NOT echo the user's raw question back at the top of the report.
8. Do NOT expose raw JSON keys or snake_case field names — use plain manufacturing language (e.g. "Target Equipment" not "device_sn").
9. Do NOT output raw JSON blocks in your final answer — only human-readable Markdown.
10. Format time-series breakdowns as Markdown tables when present.
11. Keep the report focused (roughly 150–400 words unless the dataset is large).
12. [Localized output-language rule — full sentence in zh-CN or en-US template]

[Localized closing line]
```

**RAG placeholder when no context retrieved:**

- zh-CN: `（无补充知识库上下文。）`
- en-US: `(No supplementary knowledge-base context available.)`

---

## Not sent to the LLM (static / fallback copy)

These strings are returned to the user directly or used when Bailian is unavailable. They are **not** passed as `prompt=` to DashScope.

### Companion greeting (`UNKNOWN` intent)

Returned when the router cannot map a useful tool intent. Selected by `get_companion_greeting(locale)` — **no LLM call**.

**English (`en-US`):** `COMPANION_GREETING_EN` in `orchestrator/report_generator.py`

**Chinese (`zh-CN`):** `COMPANION_GREETING_ZH` in `orchestrator/report_generator.py`

### Deterministic fallback report

**Function:** `_fallback_markdown_report()` in `orchestrator/report_generator.py`  
Used when: missing API keys, Bailian errors, timeout, or empty synthesis response.  
**Language:** Bilingual templates chosen by `locale` (`zh-CN` vs `en-US`). Field labels in the English path still use English `_FIELD_LABELS` (e.g. "Production Line", "Defect Rate").

### Validation / tool error messages

Examples returned in `message` without synthesis (English, hardcoded in Python):

- `"MCP tool execution failed"` — `orchestrator/router.py`
- `"No tool registered for intent: ..."` — `orchestrator/router.py`
- Parameter validation messages — `orchestrator/param_validation.py`

---

## Voice transcription

**File:** `core/voice/transcribe.py`  
**LLM prompt:** None — uses DashScope ASR (`Recognition`), not a text prompt.

**Mock mode** (`VOICE_MOCK=true`): returns a fixed English string (not sent to an LLM):

```
Show total equipment yield on my production line for today
```

That string then enters the same two-pass intent + synthesis pipeline as a normal text query.

---

## Frontend → backend locale signaling

The Vue app sends:

- Request body: `{ "query": "...", "enrich_response": true, "locale": "zh-CN" }`
- Header: `Accept-Language: zh-CN` (or `en-US`)

Both LLM passes use the request `locale` for **instruction language**. UI strings are handled separately via `vue-i18n`.

---

## Summary

| Component | Sent to AI? | Prompt / copy language |
|-----------|-------------|-------------------------|
| Intent extraction | Yes | Instructions: **zh-CN or en-US**; JSON keys: **English** |
| Report synthesis | Yes | Instructions + output: **zh-CN or en-US** |
| Companion greeting | No | **zh-CN or en-US** (static) |
| Fallback report | No | **zh-CN or en-US** (template) |
| Voice mock transcript | No (then piped to intent pass) | **English** |
| Chat history API | No | N/A |
