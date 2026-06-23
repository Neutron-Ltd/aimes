"""Bailian intent extraction prompt builder."""

from __future__ import annotations

from datetime import datetime

from models.schemas import IntentType, MCPContext


def build_intent_prompt(query: str, context: MCPContext) -> str:
    now = datetime.now().isoformat()
    intents = " | ".join([e.name for e in IntentType if e != IntentType.VOICE_QUERY])
    return f"""You are a strict Intent Extraction Router for an MES system (Production, Quality, Warehouse).
Your ONLY job is to classify the user query and extract structured parameters.
DO NOT output conversational text. DO NOT generate SQL.
DO NOT include workshop_id or any RBAC fields in your output.
Output ONLY a valid JSON object with these fields (omit unused):
{{
  "intent": "{intents}",
  "yield_type": "equipment" | "reported",
  "line_id": "string",
  "start_date": "YYYY-MM-DDTHH:MM:SS",
  "end_date": "YYYY-MM-DDTHH:MM:SS",
  "group_by": "daily" | "hourly" | "total",
  "metric": "sum" | "average" | "achievement_rate",
  "analysis_type": "volatility" | "below_standard" | "peak_hourly",
  "threshold_percentage": 90.0,
  "period_1_start": "YYYY-MM-DDTHH:MM:SS",
  "period_1_end": "YYYY-MM-DDTHH:MM:SS",
  "period_2_start": "YYYY-MM-DDTHH:MM:SS",
  "period_2_end": "YYYY-MM-DDTHH:MM:SS",
  "product_code": "string",
  "model_code": "string",
  "device_sn": "string",
  "batch_lot": "string",
  "material_batch": "string",
  "finished_lot": "string",
  "process_code": "string",
  "wh_code": "string",
  "item_code": "string",
  "export_format": "xlsx" | "pdf",
  "doc_type": "sop" | "anomaly" | "solution"
}}
Production intents: YIELD_AGGREGATION, YIELD_ANOMALIES, YIELD_COMPARISON,
  PRODUCTION_ROOT_CAUSE, PRODUCTION_SCHEDULING_OPT, PRODUCTION_CAPACITY_FORECAST,
  PRODUCTION_PRODUCT_YIELD, PRODUCTION_DEVICE_RATE
Quality intents: QUALITY_DEFECT_ANALYSIS, QUALITY_ROOT_CAUSE,
  QUALITY_ERROR_PREVENTION, QUALITY_EFFECTIVENESS_VERIFY
Warehouse intents: WAREHOUSE_INVENTORY_MONITOR, WAREHOUSE_INBOUND_OUTBOUND,
  WAREHOUSE_OBSOLETE_PROFILE, WAREHOUSE_TRACE_FORWARD, WAREHOUSE_TRACE_REVERSE
System intents: EXPORT_REPORT, CROSS_MODULE_ANALYSIS, UNKNOWN
Current datetime: {now}
Workshop context (reference only — do NOT include in JSON): {context.workshop_id}
User Query: {query}
"""
