"""Unit tests for hybrid report generation (deterministic block + narrative assembly)."""

from __future__ import annotations

from orchestrator.report_generator import (
    QUANTITY_UNIT,
    _assemble_hybrid_report,
    _build_full_line_breakdown_table,
    _build_system_deterministic_block,
    _compute_table_aggregates,
    _generate_mermaid_attainment_chart,
    _sanitize_narrative_names,
    _strip_llm_data_duplicates,
)


def _sample_line_breakdown(count: int = 28) -> list[dict]:
    """Fixture based on 2026-06-20 plan attainment data (subset + padding)."""
    rows = [
        {
            "area_sn": "HZ-SMT-7",
            "area_name": "鸿志贴片七线",
            "achievement_rate": 24.1708,
            "actual_qty": 73252.0,
            "planned_qty": 303060.0,
        },
        {
            "area_sn": "HZ-SMT-4",
            "area_name": "鸿志贴片四线",
            "achievement_rate": 82.5581,
            "actual_qty": 3550.0,
            "planned_qty": 4300.0,
        },
        {
            "area_sn": "LED-SMT-5",
            "area_name": "LED贴片车间五线",
            "achievement_rate": 0.0,
            "actual_qty": 0.0,
            "planned_qty": 23236.0,
        },
        {
            "area_sn": "FDQ-SMT-2",
            "area_name": "防盗器贴片二线",
            "achievement_rate": 0.0,
            "actual_qty": 0.0,
            "planned_qty": 23968.0,
        },
    ]
    if count <= len(rows):
        return rows[:count]
    extra = []
    for i in range(count - len(rows)):
        extra.append(
            {
                "area_sn": f"LED-SMT-{i + 6}",
                "area_name": f"LED贴片车间{['六', '七', '八', '九', '十'][i % 5]}线",
                "achievement_rate": 0.0,
                "actual_qty": 0.0,
                "planned_qty": 1000.0 * (i + 1),
            }
        )
    return rows + extra


def _full_zero_output_fixture() -> list[dict]:
    """15 zero-output lines summing to 192,274 planned PCS."""
    led_planned = [3000, 4900, 9450, 6750, 23236, 17220, 4200, 17890, 12100, 4800]
    rows = [
        {"area_sn": "FDQ-SMT-2", "area_name": "防盗器贴片二线", "achievement_rate": 0.0, "actual_qty": 0.0, "planned_qty": 23968.0},
        {"area_sn": "FDQ-SMT-3", "area_name": "防盗器贴片三线", "achievement_rate": 0.0, "actual_qty": 0.0, "planned_qty": 28760.0},
        {"area_sn": "FDQ-SMT-8", "area_name": "防盗器贴片八线", "achievement_rate": 0.0, "actual_qty": 0.0, "planned_qty": 3000.0},
        {"area_sn": "FDQ-SMT-9", "area_name": "防盗器贴片九线", "achievement_rate": 0.0, "actual_qty": 0.0, "planned_qty": 3000.0},
        {"area_sn": "HZ-SMT-5", "area_name": "鸿志贴片五线", "achievement_rate": 0.0, "actual_qty": 0.0, "planned_qty": 30000.0},
    ]
    for i, planned in enumerate(led_planned, start=1):
        rows.append(
            {
                "area_sn": f"LED-SMT-{i}",
                "area_name": f"LED贴片车间{i}线",
                "achievement_rate": 0.0,
                "actual_qty": 0.0,
                "planned_qty": float(planned),
            }
        )
    return rows


def test_line_breakdown_table_all_rows():
    items = _sample_line_breakdown(28)
    table = _build_full_line_breakdown_table(items, "zh-CN")
    data_rows = [line for line in table.splitlines() if line.startswith("|") and "---" not in line]
    assert len(data_rows) == 29  # header + 28 data rows
    assert "其余产线" not in table
    assert "*其余产线*" not in table


def test_line_breakdown_verbatim_names():
    items = _sample_line_breakdown(4)
    table = _build_full_line_breakdown_table(items, "zh-CN")
    assert "鸿志贴片七线" in table
    assert "荣志" not in table


def test_quantities_use_pcs():
    items = _sample_line_breakdown(2)
    table = _build_full_line_breakdown_table(items, "zh-CN")
    assert QUANTITY_UNIT in table
    assert "台" not in table
    assert "件" not in table


def test_mermaid_chart_syntax():
    items = _sample_line_breakdown(3)
    chart = _generate_mermaid_attainment_chart(items)
    assert "```mermaid" in chart
    assert "xychart-beta" in chart
    assert "HZ-SMT-4" in chart
    assert "HZ-SMT-7" in chart
    assert chart.count(",") >= 2  # bar values present


def test_aggregates_zero_output():
    db_result = {"line_breakdown": _full_zero_output_fixture()}
    aggregates = _compute_table_aggregates(db_result)
    assert aggregates["zero_output_line_count"] == 15
    assert aggregates["zero_output_planned_sum"] == 192274.0


def test_strip_llm_duplicates():
    narrative = """## 执行摘要
一些文字

| 产线 | 达成率 |
| --- | --- |
| HZ-SMT-7 | 24% |

```mermaid
xychart-beta
    bar [1, 2]
```

*其余产线* 占位
"""
    cleaned = _strip_llm_data_duplicates(narrative)
    assert "| ---" not in cleaned
    assert "mermaid" not in cleaned
    assert "其余产线" not in cleaned
    assert "执行摘要" in cleaned


def test_hybrid_assembly_order():
    block = "## 数据概览\n\n- **计划达成率:** 28.22%"
    narrative = "## 执行摘要\n分析内容"
    result = _assemble_hybrid_report(block, narrative)
    assert result.index("数据概览") < result.index("执行摘要")


def test_devices_table_no_truncation():
    devices = [
        {"device_sn": f"BB-SMT-{i:03d}", "avg_rate": 100 + i, "total_qty": 1000 * i}
        for i in range(5)
    ]
    db_result = {"devices": devices, "value": 5000}
    block, active = _build_system_deterministic_block(db_result, "zh-CN")
    assert active is True
    for i in range(5):
        assert f"BB-SMT-{i:03d}" in block


def test_sanitize_narrative_names():
    db_result = {"line_breakdown": _sample_line_breakdown(2)}
    narrative = "荣志贴片七线达成率偏低"
    fixed = _sanitize_narrative_names(narrative, db_result)
    assert "鸿志贴片七线" in fixed
    assert "荣志" not in fixed


def test_hybrid_block_includes_overview_and_chart():
    db_result = {
        "achievement_rate": 28.2168,
        "actual_qty": 169123.0,
        "planned_qty": 599370.0,
        "line_breakdown": _sample_line_breakdown(4),
    }
    block, active = _build_system_deterministic_block(db_result, "zh-CN")
    assert active is True
    assert "数据概览" in block
    assert "产线达成率图表" in block
    assert "各产线达成率对比" in block
    assert "169,123 PCS" in block
    assert "```mermaid" in block
