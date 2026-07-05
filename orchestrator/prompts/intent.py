"""Locale-aware intent extraction prompts for Bailian."""

from __future__ import annotations

from core.reference_date import get_reference_today, get_system_time_context_block
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
  PRODUCTION_PRODUCT_YIELD, PRODUCTION_DEVICE_RATE, PRODUCTION_STANDARD_TIME,
  FACTORY_METADATA_LOOKUP
Quality intents: QUALITY_DEFECT_ANALYSIS, QUALITY_ROOT_CAUSE,
  QUALITY_ERROR_PREVENTION, QUALITY_EFFECTIVENESS_VERIFY
Warehouse intents: WAREHOUSE_INVENTORY_MONITOR, WAREHOUSE_INBOUND_OUTBOUND,
  WAREHOUSE_OBSOLETE_PROFILE, WAREHOUSE_TRACE_FORWARD, WAREHOUSE_TRACE_REVERSE
System intents: EXPORT_REPORT, CROSS_MODULE_ANALYSIS, UNKNOWN"""

_ROUTING_RULES_ZH = """
关键 — 意图路由规则：
- 仅询问某产线产量/产出/达成率，未提及具体产品型号或物料编码 → YIELD_AGGREGATION
- 同时提及产线 + 产品型号/物料编码 → PRODUCTION_PRODUCT_YIELD
- 询问全厂总产量或未指定产线（如「20号的产量」）→ YIELD_AGGREGATION，line_id 设为 null
- 询问各产线对比或所有产线 → YIELD_AGGREGATION，line_id 设为 "all"
- 询问有几条产线、产线列表、工厂结构 → FACTORY_METADATA_LOOKUP
- 口语产线指代（如「一线」「六线」）可填入 line_id 为对应中文产线名，勿使用占位符编码
- line_id 可使用全局令牌 "all" 表示所有产线汇总对比
"""

_ROUTING_RULES_EN = """
CRITICAL — intent routing rules:
- Line output/yield/attainment without a specific product or model code → YIELD_AGGREGATION
- Line AND product/model code mentioned together → PRODUCTION_PRODUCT_YIELD
- Plant-wide output with no line specified (e.g. "output on the 20th") → YIELD_AGGREGATION, line_id null
- Compare all lines or every production line → YIELD_AGGREGATION, line_id "all"
- How many lines, line list, factory structure → FACTORY_METADATA_LOOKUP
- Colloquial line references (e.g. "line six") may map to Chinese line names in line_id
- line_id may be the global token "all" for all-line comparative aggregation
"""


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
    ref = get_reference_today().isoformat()
    time_context = get_system_time_context_block(locale)
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
- 口语产线指代（如「一线」「防盗器贴片六线」）可填入 line_id；全厂/各产线对比时 line_id 设为 null 或 "all"。
{_ROUTING_RULES_ZH}
仅输出一个有效的 JSON 对象（未知实体字段使用 null）：
{schema}
{_INTENT_ENUMS}
当前时间：{ref}{time_context}
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
- Colloquial line names may populate line_id; use null or "all" for plant-wide or all-line queries.
{_ROUTING_RULES_EN}
Output ONLY a valid JSON object with these fields (use null for unknown entity fields):
{schema}
{_INTENT_ENUMS}
Current datetime: {ref}{time_context}
User Query: {query}
"""
