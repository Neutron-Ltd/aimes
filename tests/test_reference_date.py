"""Tests for colloquial day-of-month resolution and intent post-correction."""

from __future__ import annotations

import unittest
from datetime import date

from core.reference_date import (
    apply_colloquial_day_dates,
    extract_bare_days_from_query,
    resolve_day_of_month,
)
from models.schemas import IntentSchema, IntentType
from orchestrator.intent_corrections import apply_intent_corrections


class ResolveDayOfMonthTests(unittest.TestCase):
    def test_early_in_month_uses_previous_month(self) -> None:
        self.assertEqual(
            resolve_day_of_month(20, date(2026, 7, 6)),
            date(2026, 6, 20),
        )

    def test_after_day_uses_current_month(self) -> None:
        self.assertEqual(
            resolve_day_of_month(20, date(2026, 7, 21)),
            date(2026, 7, 20),
        )

    def test_same_day_uses_current_month(self) -> None:
        self.assertEqual(
            resolve_day_of_month(20, date(2026, 7, 20)),
            date(2026, 7, 20),
        )

    def test_year_rollover(self) -> None:
        self.assertEqual(
            resolve_day_of_month(20, date(2026, 1, 5)),
            date(2025, 12, 20),
        )


class ExtractBareDaysTests(unittest.TestCase):
    def test_chinese_bare_day(self) -> None:
        self.assertEqual(extract_bare_days_from_query("我要看20号各产线的达成率"), [20])

    def test_explicit_month_skipped(self) -> None:
        self.assertEqual(extract_bare_days_from_query("6月20号各产线达成率"), [])

    def test_english_ordinal(self) -> None:
        self.assertEqual(extract_bare_days_from_query("show the 20th for all lines"), [20])


class ApplyColloquialDayDatesTests(unittest.TestCase):
    def test_overrides_future_llm_date(self) -> None:
        intent = IntentSchema(
            intent=IntentType.PRODUCTION_PLAN_ACHIEVEMENT,
            start_date=date(2026, 7, 20),
            end_date=date(2026, 7, 20),
            raw_query="我要看20号各产线的达成率",
        )
        fixed = apply_colloquial_day_dates(intent)
        self.assertEqual(fixed.start_date, date(2026, 6, 20))
        self.assertEqual(fixed.end_date, date(2026, 6, 20))

    def test_explicit_month_not_overridden(self) -> None:
        intent = IntentSchema(
            intent=IntentType.PRODUCTION_PLAN_ACHIEVEMENT,
            start_date=date(2026, 6, 20),
            end_date=date(2026, 6, 20),
            raw_query="6月20号各产线达成率",
        )
        fixed = apply_colloquial_day_dates(intent)
        self.assertEqual(fixed.start_date, date(2026, 6, 20))


class IntentCorrectionTests(unittest.TestCase):
    def test_plan_achievement_all_lines_reroute(self) -> None:
        intent = IntentSchema(
            intent=IntentType.PRODUCTION_PRODUCT_YIELD,
            metric="achievement_rate",
            raw_query="我要看20号各产线的达成率",
        )
        fixed = apply_intent_corrections(intent)
        self.assertEqual(fixed.intent, IntentType.PRODUCTION_PLAN_ACHIEVEMENT)
        self.assertEqual(fixed.line_id, "all")

    def test_standard_time_not_rerouted(self) -> None:
        intent = IntentSchema(
            intent=IntentType.PRODUCTION_STANDARD_TIME,
            raw_query="防盗器贴片六线标准工时达成率",
        )
        fixed = apply_intent_corrections(intent)
        self.assertEqual(fixed.intent, IntentType.PRODUCTION_STANDARD_TIME)


if __name__ == "__main__":
    unittest.main()
