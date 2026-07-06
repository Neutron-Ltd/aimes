"""
Feature 5.2 — Mathematical Safeguard Layer.

All statistics are computed in Python before JSON reaches the LLM.
Prevents hallucinated math on large or complex datasets.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Optional


def population_std_dev(values: Sequence[float]) -> float:
    """
    Population standard deviation: σ = sqrt(Σ(x - μ)² / N).

    Uses the population formula (divide by N, not N-1). Returns 0.0 for
    empty or single-element sequences.
    """
    if len(values) < 2:
        return 0.0

    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def plan_achievement_rate(actual: float, planned: float) -> float:
    """
    Plan attainment: (actual / planned) * 100.

    Returns 0.0 when planned quantity is zero. Values above 100% are allowed
    when actual output exceeds plan.
    """
    if planned == 0:
        return 0.0
    return (actual / planned) * 100.0


def period_over_period_growth_rate(
    current: float, past: float
) -> Optional[float]:
    """
    Period-over-period growth rate: ((current - past) / past) * 100.

    Returns None when the past period total is zero (undefined growth).
    """
    if past == 0:
        return None

    return ((current - past) / past) * 100.0
