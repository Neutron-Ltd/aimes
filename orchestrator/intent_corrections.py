"""Deterministic intent fixes after Bailian extraction, before validation."""

from __future__ import annotations

import re

from models.schemas import IntentSchema, IntentType

_PLAN_ACHIEVEMENT_ZH_RE = re.compile(r"达成率|完成率|计划达成|计划完成")
_PLAN_ACHIEVEMENT_EN_RE = re.compile(
    r"plan\s+attainment|achievement\s+rate|completion\s+rate",
    re.IGNORECASE,
)
_STANDARD_TIME_RE = re.compile(r"标准工时|standard\s+time", re.IGNORECASE)
_ALL_LINES_ZH_RE = re.compile(r"各产线|每条产线|所有产线|全厂各")
_ALL_LINES_EN_RE = re.compile(r"all\s+lines?|each\s+line|every\s+line", re.IGNORECASE)
_PRODUCT_CODE_RE = re.compile(r"\d{10,}")

_WRONG_PLAN_INTENTS = frozenset(
    {
        IntentType.PRODUCTION_PRODUCT_YIELD,
        IntentType.YIELD_AGGREGATION,
    }
)


def _is_plan_achievement_query(query: str) -> bool:
    if _STANDARD_TIME_RE.search(query):
        return False
    return bool(_PLAN_ACHIEVEMENT_ZH_RE.search(query) or _PLAN_ACHIEVEMENT_EN_RE.search(query))


def _is_all_lines_query(query: str) -> bool:
    return bool(_ALL_LINES_ZH_RE.search(query) or _ALL_LINES_EN_RE.search(query))


def _should_skip_plan_reroute(intent: IntentSchema) -> bool:
    query = intent.raw_query or ""
    if _PRODUCT_CODE_RE.search(query) and intent.line_id and not _is_all_lines_query(query):
        return True
    return False


def apply_intent_corrections(intent: IntentSchema) -> IntentSchema:
    """Reroute misclassified plan-attainment queries and set all-lines scope."""
    updates: dict[str, object] = {}
    query = intent.raw_query or ""

    if _is_plan_achievement_query(query) and not _should_skip_plan_reroute(intent):
        if intent.intent in _WRONG_PLAN_INTENTS or (
            intent.intent == IntentType.YIELD_AGGREGATION
            and intent.metric == "achievement_rate"
        ):
            updates["intent"] = IntentType.PRODUCTION_PLAN_ACHIEVEMENT
            updates["metric"] = "achievement_rate"

    plan_intent = updates.get("intent", intent.intent)
    if _is_plan_achievement_query(query) and plan_intent == IntentType.PRODUCTION_PLAN_ACHIEVEMENT:
        if _is_all_lines_query(query):
            updates["line_id"] = "all"

    if updates:
        intent = intent.model_copy(update=updates)
    return intent
