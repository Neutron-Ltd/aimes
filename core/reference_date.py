"""Calendar 'today' for intent parsing, param defaults, and dashboard windows."""

from __future__ import annotations

import calendar
import re
from datetime import date

from models.schemas import IntentSchema, IntentType

_BARE_DAY_ZH_RE = re.compile(r"(?<![0-9月])(\d{1,2})[号日]")
_BARE_DAY_EN_RE = re.compile(
    r"\b(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)\b",
    re.IGNORECASE,
)
_EXPLICIT_MONTH_ZH_RE = re.compile(r"\d{1,2}月\d{1,2}[号日]")
_EXPLICIT_MONTH_EN_RE = re.compile(
    r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)"
    r"\s+\d{1,2}",
    re.IGNORECASE,
)
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_RANGE_CONNECTOR_RE = re.compile(r"到|至|~|—|-|to", re.IGNORECASE)
_RELATIVE_DAY_SKIP_RE = re.compile(
    r"今日|昨天|明天|前天|后天|today|yesterday|tomorrow",
    re.IGNORECASE,
)


def get_reference_today() -> date:
    """Return the server local calendar date for intent parsing and param defaults."""
    return date.today()


def _safe_date(year: int, month: int, day: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last_day))


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def resolve_day_of_month(day: int, ref: date | None = None) -> date:
    """Resolve bare 'N号' / 'the Nth' to the most recent calendar occurrence."""
    if day < 1 or day > 31:
        raise ValueError(f"day must be 1-31, got {day}")
    ref = ref or get_reference_today()
    if day <= ref.day:
        return _safe_date(ref.year, ref.month, day)
    year, month = _previous_month(ref.year, ref.month)
    return _safe_date(year, month, day)


def _has_explicit_month(query: str) -> bool:
    return bool(
        _EXPLICIT_MONTH_ZH_RE.search(query)
        or _EXPLICIT_MONTH_EN_RE.search(query)
        or _ISO_DATE_RE.search(query)
    )


def extract_bare_days_from_query(query: str) -> list[int]:
    """Return day numbers from bare-day phrases only (no explicit month)."""
    if _RELATIVE_DAY_SKIP_RE.search(query) or _has_explicit_month(query):
        return []

    days: list[int] = []
    for pattern in (_BARE_DAY_ZH_RE, _BARE_DAY_EN_RE):
        for match in pattern.finditer(query):
            day = int(match.group(1))
            if 1 <= day <= 31:
                days.append(day)
    return days


def apply_colloquial_day_dates(intent: IntentSchema) -> IntentSchema:
    """Override intent dates when the user used bare day-of-month phrases."""
    query = intent.raw_query or ""
    bare_days = extract_bare_days_from_query(query)
    ref = get_reference_today()
    updates: dict[str, date] = {}

    if bare_days:
        if len(bare_days) >= 2 and _RANGE_CONNECTOR_RE.search(query):
            updates["start_date"] = resolve_day_of_month(bare_days[0], ref)
            updates["end_date"] = resolve_day_of_month(bare_days[1], ref)
        else:
            resolved = resolve_day_of_month(bare_days[0], ref)
            updates["start_date"] = resolved
            updates["end_date"] = resolved
    elif intent.start_date and intent.start_date > ref and not _has_explicit_month(query):
        day = intent.start_date.day
        zh_hit = re.search(rf"(?<![0-9月]){day}[号日]", query)
        en_hit = re.search(rf"\b(?:the\s+)?{day}(?:st|nd|rd|th)\b", query, re.IGNORECASE)
        if zh_hit or en_hit:
            resolved = resolve_day_of_month(day, ref)
            updates["start_date"] = resolved
            if intent.end_date is None or intent.end_date == intent.start_date:
                updates["end_date"] = resolved
            elif intent.end_date > ref and intent.end_date.day == day:
                updates["end_date"] = resolved

    if updates:
        intent = intent.model_copy(update=updates)

    if (
        intent.intent == IntentType.PRODUCTION_PLAN_ACHIEVEMENT
        and intent.start_date
        and intent.end_date
        and intent.start_date == intent.end_date
        and not intent.group_by
    ):
        intent = intent.model_copy(update={"group_by": "daily"})

    return intent


def get_system_time_context_block(locale: str) -> str:
    """Hard-rule paragraph injected into Bailian intent prompts."""
    ref = get_reference_today()
    ref_iso = ref.isoformat()
    year = ref.year

    if locale == "zh-CN":
        return (
            f"\n当前系统时间上下文：年份为 {year}，今天日期为 {ref_iso}。"
            f"所有相对表达如「今天」「昨天」「上周」「上个月」或「20号」等，"
            f"必须相对 {ref_iso} 计算日期范围。"
            f"仅写「N号」未写月份时：若 N ≤ 今天的日（{ref.day}），指本月 N 号；"
            f"若 N > 今天的日，指上月 N 号。"
            f"例：今天 {ref_iso} 时「20号」="
            f"{resolve_day_of_month(20, ref).isoformat()}；"
            f"若今天为当月 21 日则「20号」指本月 20 日。"
        )

    resolved_20 = resolve_day_of_month(20, ref).isoformat()
    return (
        f"\nCurrent System Time Context: The year is {year}. "
        f"Today's date is {ref_iso}. "
        f"All relative expressions such as 'today', 'yesterday', 'last week', "
        f"'last month', or specific dates like 'the 20th' must calculate their "
        f"date ranges relative to {ref_iso}. "
        f"For bare day-of-month only (no month stated): if N <= today's day ({ref.day}), "
        f"use day N of the current month; if N > today's day, use day N of the previous month. "
        f"Example: on {ref_iso}, 'the 20th' = {resolved_20}."
    )
