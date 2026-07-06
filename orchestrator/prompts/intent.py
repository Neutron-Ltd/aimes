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
  "group_by": "daily" | "hourly" | "weekly" | "monthly" | "total" | null,
  "metric": "sum" | "average" | "achievement_rate" | null,
  "analysis_type": "volatility" | "below_standard" | "peak_hourly" | null,
  "threshold_percentage": number or null,
  "period_1_start": "YYYY-MM-DDTHH:MM:SS or null",
  "period_1_end": "YYYY-MM-DDTHH:MM:SS or null",
  "period_2_start": "YYYY-MM-DDTHH:MM:SS or null",
  "period_2_end": "YYYY-MM-DDTHH:MM:SS or null",
  "product_code": "string or null",
  "model_code": "string or null",
  "mo_number": "string or null",
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
  PRODUCTION_PLAN_ACHIEVEMENT, FACTORY_METADATA_LOOKUP
Quality intents: QUALITY_DEFECT_ANALYSIS, QUALITY_ROOT_CAUSE,
  QUALITY_ERROR_PREVENTION, QUALITY_EFFECTIVENESS_VERIFY
Warehouse intents: WAREHOUSE_INVENTORY_MONITOR, WAREHOUSE_INBOUND_OUTBOUND,
  WAREHOUSE_OBSOLETE_PROFILE, WAREHOUSE_TRACE_FORWARD, WAREHOUSE_TRACE_REVERSE
System intents: EXPORT_REPORT, CROSS_MODULE_ANALYSIS, UNKNOWN"""

_ROUTING_RULES_ZH = """
关键 — 意图路由规则：
- 计划达成率 / 达成率 / 完成率 / 工单进度 / 计划完成 → PRODUCTION_PLAN_ACHIEVEMENT（非 YIELD_AGGREGATION）
- 设备产量、finish_qty、设备日志产出总量 → YIELD_AGGREGATION，metric 用 sum 或 average，勿用 achievement_rate
- 仅询问某产线产量/产出（非计划达成率）→ YIELD_AGGREGATION，metric=sum
- 同时提及产线 + 产品型号/物料编码（产量，非达成率）→ PRODUCTION_PRODUCT_YIELD
- 询问全厂总产量或未指定产线（如「20号的产量」）→ YIELD_AGGREGATION，line_id 设为 null
- 各产线计划达成率对比 / 达成率 + 各产线 → PRODUCTION_PLAN_ACHIEVEMENT，line_id="all"（无产品编码时切勿使用 PRODUCTION_PRODUCT_YIELD）
- YIELD_AGGREGATION 禁止使用 metric=achievement_rate；计划达成率一律用 PRODUCTION_PLAN_ACHIEVEMENT
- 询问有几条产线、产线列表、工厂结构 → FACTORY_METADATA_LOOKUP
- 提及工单号/MO/项目号 → PRODUCTION_PLAN_ACHIEVEMENT，mo_number 填入工单号
- 一周/一个月 → group_by 设为 weekly 或 monthly；单日 → daily 或 total
- 口语产线指代（如「一线」「六线」）可填入 line_id 为对应中文产线名，勿使用占位符编码
- line_id 可使用全局令牌 "all" 表示所有产线汇总对比
"""

_ROUTING_RULES_EN = """
CRITICAL — intent routing rules:
- Plan attainment / achievement rate / completion rate / work-order progress → PRODUCTION_PLAN_ACHIEVEMENT (not YIELD_AGGREGATION)
- Equipment output volume, finish_qty, machine-log totals → YIELD_AGGREGATION with metric sum or average; do NOT use achievement_rate
- Line output volume only (not plan attainment) → YIELD_AGGREGATION, metric=sum
- Line AND product/model code (output volume, not attainment) → PRODUCTION_PRODUCT_YIELD
- Plant-wide output with no line specified → YIELD_AGGREGATION, line_id null
- All-line plan attainment / achievement rate + all lines → PRODUCTION_PLAN_ACHIEVEMENT, line_id "all" (never PRODUCTION_PRODUCT_YIELD without product code)
- metric=achievement_rate on YIELD_AGGREGATION is invalid; plan attainment always uses PRODUCTION_PLAN_ACHIEVEMENT
- How many lines, line list, factory structure → FACTORY_METADATA_LOOKUP
- Work order / MO / project number mentioned → PRODUCTION_PLAN_ACHIEVEMENT, set mo_number
- Week or month time frame → group_by weekly or monthly; single day → daily or total
- Colloquial line references may map to Chinese line names in line_id
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
- 仅当用户明确提及时，才填充 line_id、product_code、model_code、mo_number、device_sn、batch_lot、material_batch、finished_lot、process_code、wh_code、item_code。
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
- Only populate line_id, product_code, model_code, mo_number, device_sn, batch_lot, material_batch, finished_lot, process_code, wh_code, and item_code when the user clearly mentions them.
- Colloquial line names may populate line_id; use null or "all" for plant-wide or all-line queries.
{_ROUTING_RULES_EN}
Output ONLY a valid JSON object with these fields (use null for unknown entity fields):
{schema}
{_INTENT_ENUMS}
Current datetime: {ref}{time_context}
User Query: {query}
"""
