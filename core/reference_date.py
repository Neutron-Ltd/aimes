"""Calendar 'today' for intent parsing, param defaults, and dashboard windows."""

from __future__ import annotations

from datetime import date


def get_reference_today() -> date:
    """Return the server local calendar date for intent parsing and param defaults."""
    return date.today()


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
        )

    return (
        f"\nCurrent System Time Context: The year is {year}. "
        f"Today's date is {ref_iso}. "
        f"All relative expressions such as 'today', 'yesterday', 'last week', "
        f"'last month', or specific dates like 'the 20th' must calculate their "
        f"date ranges relative to {ref_iso}."
    )
