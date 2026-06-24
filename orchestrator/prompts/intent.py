"""Locale-aware intent extraction prompts for Bailian."""

from __future__ import annotations

from datetime import datetime

from models.schemas import IntentType, MCPContext

_SUPPORTED_LOCALES = frozenset({"zh-CN", "en-US"})

_JSON_SCHEMA_BLOCK = """{{
  "intent": "{intents}",
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
}}"""

_INTENT_ENUMS = """Production intents: YIELD_AGGREGATION, YIELD_ANOMALIES, YIELD_COMPARISON,
  PRODUCTION_ROOT_CAUSE, PRODUCTION_SCHEDULING_OPT, PRODUCTION_CAPACITY_FORECAST,
  PRODUCTION_PRODUCT_YIELD, PRODUCTION_DEVICE_RATE, PRODUCTION_STANDARD_TIME
Quality intents: QUALITY_DEFECT_ANALYSIS, QUALITY_ROOT_CAUSE,
  QUALITY_ERROR_PREVENTION, QUALITY_EFFECTIVENESS_VERIFY
Warehouse intents: WAREHOUSE_INVENTORY_MONITOR, WAREHOUSE_INBOUND_OUTBOUND,
  WAREHOUSE_OBSOLETE_PROFILE, WAREHOUSE_TRACE_FORWARD, WAREHOUSE_TRACE_REVERSE
System intents: EXPORT_REPORT, CROSS_MODULE_ANALYSIS, UNKNOWN"""


def _normalize_locale(locale: str) -> str:
    return locale if locale in _SUPPORTED_LOCALES else "zh-CN"


def build_intent_prompt(
    query: str,
    context: MCPContext,
    locale: str = "zh-CN",
) -> str:
    """Build the Bailian intent-extraction prompt in the requested locale."""
    _ = context  # reserved for future workshop-scoped hints
    locale = _normalize_locale(locale)
    now = datetime.now().isoformat()
    intents = " | ".join([e.name for e in IntentType if e != IntentType.VOICE_QUERY])
    schema = _JSON_SCHEMA_BLOCK.format(intents=intents)

    if locale == "zh-CN":
        return f"""你是 MES 系统（生产、质量、仓储）的严格意图提取路由器。
你的唯一任务是对用户查询进行分类并提取结构化参数。
不要输出对话式文本。不要生成 SQL。
不要在输出中包含 workshop_id 或任何 RBAC 字段。

JSON 属性名必须保持英文，与下方规范完全一致。

关键 — 实体提取规则：
- 切勿臆造、假设或使用占位符填充标识符（例如：用户未明确说明产线时，不要使用 "L-01"、"L-03" 等）。
- 若无法从用户文本中明确提取某字段，请在 JSON 中将其设为 null。
- 仅当用户明确提及时，才填充 line_id、product_code、model_code、device_sn、batch_lot、material_batch、finished_lot、process_code、wh_code、item_code。

仅输出一个有效的 JSON 对象（未知实体字段使用 null）：
{schema}
{_INTENT_ENUMS}
当前时间：{now}
用户问题：{query}
"""

    return f"""You are a strict Intent Extraction Router for an MES system (Production, Quality, Warehouse).
Your ONLY job is to classify the user query and extract structured parameters.
DO NOT output conversational text. DO NOT generate SQL.
DO NOT include workshop_id or any RBAC fields in your output.

JSON property names must remain in English exactly as specified below.

CRITICAL — entity extraction rules:
- NEVER invent, assume, or default placeholder values for identifiers (e.g. do NOT use "L-01", "L-03", or any line unless the user explicitly stated it).
- If a field cannot be explicitly extracted from the user's text, set it to null in JSON.
- Only populate line_id, product_code, model_code, device_sn, batch_lot, material_batch, finished_lot, process_code, wh_code, and item_code when the user clearly mentions them.

Output ONLY a valid JSON object with these fields (use null for unknown entity fields):
{schema}
{_INTENT_ENUMS}
Current datetime: {now}
User Query: {query}
"""
