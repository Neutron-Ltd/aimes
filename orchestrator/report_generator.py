"""Second-pass LLM synthesis — structured MCP results → Markdown analysis report."""

from __future__ import annotations

import asyncio
import json
import re
from http import HTTPStatus
from typing import Any, Callable, Optional

import dashscope

from orchestrator.module_personas import get_module_greeting
from orchestrator.prompts.synthesis import build_synthesis_prompt
from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)

SYNTHESIS_TIMEOUT_SECONDS = 120

# ---------------------------------------------------------------------------
# Companion / greeting copy — delegated to module_personas (see messages.js)
# ---------------------------------------------------------------------------


def get_companion_greeting(locale: str = "zh-CN", module: Optional[str] = None) -> str:
    return get_module_greeting(locale, module)


def get_intent_failure_message(locale: str, reason: str) -> str:
    """User-visible message when Bailian intent extraction fails."""
    if locale == "zh-CN":
        return (
            f"意图识别服务不可用：{reason}。"
            "请检查服务器 .env 中的 DASHSCOPE_API_KEY 与 BAILIAN_APP_ID，"
            "并确认容器可访问 DashScope 网络。"
        )
    return (
        f"Intent routing is unavailable: {reason}. "
        "Check DASHSCOPE_API_KEY and BAILIAN_APP_ID in the server .env, "
        "and ensure the container can reach DashScope."
    )


# ---------------------------------------------------------------------------
# Human-readable field mapping for fallback reports
# ---------------------------------------------------------------------------

_YIELD_TYPE_LABELS = {
    "equipment": "Automated Machine Logs",
    "reported": "Work-in-Process Shift Logs",
}

_METRIC_LABELS = {
    "sum": "Total Output",
    "average": "Average Output",
    "achievement_rate": "Achievement Rate",
}

_GROUP_BY_LABELS = {
    "daily": "By Day",
    "hourly": "By Hour",
    "total": "Full Period Total",
}

_ANALYSIS_TYPE_LABELS = {
    "volatility": "Yield Volatility",
    "below_standard": "Below-Standard Periods",
    "peak_hourly": "Peak Hourly Throughput",
}

_FIELD_LABELS: dict[str, str] = {
    "yield_type": "Data Source",
    "line_id": "Production Line",
    "device_sn": "Target Equipment",
    "metric": "Measurement Type",
    "group_by": "Time Grouping",
    "value": "Accumulated Production Output",
    "analysis_type": "Analysis Mode",
    "product_code": "Product Code",
    "model_code": "Model Code",
    "period_1_total": "Period 1 Total",
    "period_2_total": "Period 2 Total",
    "growth_rate": "Period-over-Period Change",
    "defect_rate": "Defect Rate",
    "total_inspected": "Units Inspected",
    "total_defects": "Defective Units",
    "achievement_pct": "Standard Time Achievement",
    "actual_qty": "Actual Output",
    "standard_time": "Standard Time Target",
    "elapsed_hours": "Elapsed Production Hours",
    "capacity_utilization": "Capacity Utilization",
    "overtime_hours_estimate": "Estimated Overtime Hours",
    "personnel_gap": "Personnel Gap Estimate",
    "before_defect_rate": "Defect Rate (Before)",
    "after_defect_rate": "Defect Rate (After)",
    "process_code": "Process Step",
    "recommended_bay": "Recommended Bay",
    "summary": "Executive Summary",
    "scope": "Query Scope",
    "line_count": "Production Line Count",
    "refinement_suggested": "Drill-Down Suggested",
}

_FIELD_LABELS_ZH: dict[str, str] = {
    "yield_type": "数据来源",
    "line_id": "产线",
    "device_sn": "目标设备",
    "metric": "计量方式",
    "group_by": "时间分组",
    "value": "累计产量",
    "analysis_type": "分析模式",
    "product_code": "产品编码",
    "model_code": "型号编码",
    "period_1_total": "时段一合计",
    "period_2_total": "时段二合计",
    "growth_rate": "环比变化",
    "defect_rate": "不良率",
    "total_inspected": "检验数量",
    "total_defects": "不良数量",
    "achievement_pct": "标准工时达成率",
    "actual_qty": "实际产量",
    "standard_time": "标准工时目标",
    "elapsed_hours": "生产耗时（小时）",
    "capacity_utilization": "产能利用率",
    "overtime_hours_estimate": "预计加班时长",
    "personnel_gap": "人员缺口估计",
    "before_defect_rate": "改善前不良率",
    "after_defect_rate": "改善后不良率",
    "process_code": "工序",
    "recommended_bay": "推荐库位",
    "summary": "执行摘要",
    "scope": "查询范围",
    "line_count": "产线数量",
    "refinement_suggested": "建议进一步拆分",
}

_YIELD_TYPE_LABELS_ZH = {
    "equipment": "设备自动采集日志",
    "reported": "在制品报工日志",
}

_METRIC_LABELS_ZH = {
    "sum": "总产量",
    "average": "平均产量",
    "achievement_rate": "达成率",
}

_GROUP_BY_LABELS_ZH = {
    "daily": "按日",
    "hourly": "按小时",
    "total": "全时段合计",
}

_SCOPE_LABELS_ZH = {
    "line": "单产线",
    "plant": "全厂汇总",
    "all_lines": "各产线对比",
}

_TABLE_FIELD_LABELS: dict[str, tuple[str, str]] = {
    "breakdown": ("Production Period", "Calculated Output Volume"),
    "devices": ("Equipment", "Average Rate / Total Output"),
    "hypotheses": ("Problem", "Likely Cause"),
    "low_stock": ("Item Code", "Status"),
    "expiring": ("Item Code", "Expiry"),
    "stagnant_items": ("Item Code", "Stagnant Quantity"),
    "fifo_lots": ("Lot Number", "Quantity / Instock Date"),
    "adjusted_schedule": ("Work Order", "Priority / Plan"),
}

_TABLE_FIELD_LABELS_ZH: dict[str, tuple[str, str]] = {
    "breakdown": ("生产时段", "产量"),
    "devices": ("设备", "平均速率 / 总产量"),
    "hypotheses": ("问题", "可能原因"),
    "low_stock": ("物料编码", "状态"),
    "expiring": ("物料编码", "到期日"),
    "stagnant_items": ("物料编码", "呆滞数量"),
    "fifo_lots": ("批次号", "数量 / 入库日期"),
    "adjusted_schedule": ("工单", "优先级 / 计划"),
    "line_breakdown": ("产线", "产量"),
    "lines": ("产线编码", "产线名称"),
}


def _field_labels(locale: str) -> dict[str, str]:
    return _FIELD_LABELS_ZH if locale == "zh-CN" else _FIELD_LABELS


def _table_field_labels(locale: str) -> dict[str, tuple[str, str]]:
    return _TABLE_FIELD_LABELS_ZH if locale == "zh-CN" else _TABLE_FIELD_LABELS


def _unit_suffix(locale: str) -> str:
    return "件" if locale == "zh-CN" else "units"


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def _format_number(value: Any, locale: str = "en-US") -> str:
    if isinstance(value, bool):
        if locale == "zh-CN":
            return "是" if value else "否"
        return "Yes" if value else "No"
    if isinstance(value, float):
        if value == int(value):
            return f"{int(value):,}"
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _format_period_label(raw: Any) -> str:
    text = str(raw)
    if "T" in text:
        return text.split("T")[0]
    return text[:10] if len(text) >= 10 else text


def _translate_scalar(
    key: str, value: Any, context: dict[str, Any], locale: str = "zh-CN"
) -> str:
    zh = locale == "zh-CN"
    if key == "yield_type" and isinstance(value, str):
        labels = _YIELD_TYPE_LABELS_ZH if zh else _YIELD_TYPE_LABELS
        return labels.get(value.lower(), value.replace("_", " ").title())
    if key == "metric" and isinstance(value, str):
        labels = _METRIC_LABELS_ZH if zh else _METRIC_LABELS
        return labels.get(value.lower(), value.replace("_", " ").title())
    if key == "group_by" and isinstance(value, str):
        labels = _GROUP_BY_LABELS_ZH if zh else _GROUP_BY_LABELS
        return labels.get(value.lower(), value.replace("_", " ").title())
    if key == "scope" and isinstance(value, str):
        if zh:
            return _SCOPE_LABELS_ZH.get(value.lower(), value)
        return value.replace("_", " ").title()
    if key == "analysis_type" and isinstance(value, str):
        return _ANALYSIS_TYPE_LABELS.get(value.lower(), value.replace("_", " ").title())
    if key == "device_sn" and value:
        return f"设备 {value}" if zh else f"Machine {value}"
    if key in ("growth_rate", "defect_rate", "achievement_pct", "capacity_utilization"):
        if isinstance(value, (int, float)):
            return f"{value:,.2f}%"
    if key == "value":
        metric = str(context.get("metric", "")).lower()
        formatted = _format_number(value, locale)
        if metric == "achievement_rate":
            return f"{formatted}%"
        if metric in ("sum", "average", ""):
            return f"{formatted} {_unit_suffix(locale)}"
        return formatted
    if isinstance(value, (int, float)) and key not in ("line_id", "process_code"):
        return _format_number(value, locale)
    if isinstance(value, bool):
        return _format_number(value, locale)
    return str(value)


def _markdown_table(headers: tuple[str, str], rows: list[tuple[str, str]]) -> str:
    if not rows:
        return ""
    lines = [
        f"| {headers[0]} | {headers[1]} |",
        "| --- | --- |",
    ]
    for left, right in rows:
        lines.append(f"| {left} | {right} |")
    return "\n".join(lines)


def _rows_from_breakdown(
    items: list[dict[str, Any]], locale: str = "zh-CN"
) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    unit = _unit_suffix(locale)
    for item in items:
        period = item.get("bucket") or item.get("date") or "—"
        period_label = _format_period_label(period)
        qty = item.get("value")
        if qty is None:
            qty = item.get("good_qty", item.get("qty", "—"))
        if isinstance(qty, (int, float)):
            qty_display = f"{_format_number(qty, locale)} {unit}"
        else:
            qty_display = str(qty)
        rows.append((period_label, qty_display))
    return rows


def _rows_from_line_breakdown(
    items: list[dict[str, Any]], locale: str = "zh-CN"
) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    unit = _unit_suffix(locale)
    for item in items:
        name = item.get("area_name") or item.get("area_sn") or "—"
        value = item.get("value", "—")
        if isinstance(value, (int, float)):
            value = f"{_format_number(value, locale)} {unit}"
        rows.append((str(name), str(value)))
    return rows


def _rows_from_devices(
    items: list[dict[str, Any]], locale: str = "zh-CN"
) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    unit = _unit_suffix(locale)
    for item in items:
        name = item.get("device_sn") or item.get("device_name") or "—"
        rate = item.get("avg_rate")
        total = item.get("total_qty")
        detail_parts = []
        if rate is not None:
            detail_parts.append(
                f"平均 {_format_number(rate, locale)}" if locale == "zh-CN"
                else f"avg {_format_number(rate, locale)}"
            )
        if total is not None:
            detail_parts.append(
                f"合计 {_format_number(total, locale)} {unit}" if locale == "zh-CN"
                else f"total {_format_number(total, locale)} {unit}"
            )
        rows.append((str(name), " / ".join(detail_parts) or "—"))
    return rows


def _rows_from_factory_lines(
    items: list[dict[str, Any]], _locale: str = "zh-CN"
) -> list[tuple[str, str]]:
    return [
        (str(item.get("area_sn") or "—"), str(item.get("area_name") or "—"))
        for item in items
    ]


def _rows_from_hypotheses(items: list[dict[str, Any]]) -> list[tuple[str, str]]:
    return [
        (
            str(item.get("problem") or item.get("reason") or "—"),
            str(item.get("reason") or item.get("score") or "—"),
        )
        for item in items
    ]


def _rows_from_inventory(
    items: list[dict[str, Any]], mode: str, locale: str = "zh-CN"
) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    unit = _unit_suffix(locale)
    for item in items:
        code = str(item.get("item_code") or "—")
        if mode == "low_stock":
            if locale == "zh-CN":
                rows.append((
                    code,
                    f"{_format_number(item.get('qty', 0), locale)} {unit} "
                    f"(最低 {_format_number(item.get('min_stock', 0), locale)})",
                ))
            else:
                rows.append((
                    code,
                    f"{_format_number(item.get('qty', 0), locale)} {unit} "
                    f"(min {_format_number(item.get('min_stock', 0), locale)})",
                ))
        elif mode == "expiring":
            rows.append((code, str(item.get("invalid_date") or "—")))
        else:
            rows.append((code, f"{_format_number(item.get('qty', 0), locale)} {unit}"))
    return rows


def _rows_from_fifo(items: list[dict[str, Any]], locale: str = "zh-CN") -> list[tuple[str, str]]:
    unit = _unit_suffix(locale)
    return [
        (
            str(item.get("item_lot") or "—"),
            f"{_format_number(item.get('qty', 0), locale)} {unit} · "
            f"{item.get('instock_time', '—')}",
        )
        for item in items
    ]


def _rows_from_schedule(items: list[dict[str, Any]], locale: str = "zh-CN") -> list[tuple[str, str]]:
    if locale == "zh-CN":
        return [
            (
                str(item.get("mo_number") or "—"),
                f"优先级 {_format_number(item.get('priority_score', 0), locale)} · "
                f"数量 {_format_number(item.get('plan_qty', 0), locale)}",
            )
            for item in items
        ]
    return [
        (
            str(item.get("mo_number") or "—"),
            f"priority {_format_number(item.get('priority_score', 0), locale)} · "
            f"qty {_format_number(item.get('plan_qty', 0), locale)}",
        )
        for item in items
    ]


def _render_list_table(
    key: str, items: list[Any], locale: str = "zh-CN"
) -> Optional[str]:
    if not items or not isinstance(items, list):
        return None
    if not all(isinstance(item, dict) for item in items):
        return None

    headers = _table_field_labels(locale).get(key)
    row_builder: Optional[Callable[..., list[tuple[str, str]]]] = None

    if key == "breakdown":
        row_builder = lambda items: _rows_from_breakdown(items, locale)
    elif key == "line_breakdown":
        row_builder = lambda items: _rows_from_line_breakdown(items, locale)
    elif key == "lines":
        row_builder = lambda items: _rows_from_factory_lines(items, locale)
    elif key == "devices":
        row_builder = lambda items: _rows_from_devices(items, locale)
    elif key == "hypotheses":
        row_builder = _rows_from_hypotheses
    elif key == "low_stock":
        row_builder = lambda items: _rows_from_inventory(items, "low_stock", locale)
    elif key == "expiring":
        row_builder = lambda items: _rows_from_inventory(items, "expiring", locale)
    elif key == "stagnant_items":
        row_builder = lambda items: _rows_from_inventory(items, "stagnant", locale)
    elif key == "fifo_lots":
        row_builder = lambda items: _rows_from_fifo(items, locale)
    elif key == "adjusted_schedule":
        row_builder = lambda items: _rows_from_schedule(items, locale)
    elif key == "probable_causes":
        headers = (
            ("可能因素", "详情") if locale == "zh-CN" else ("Likely Factor", "Detail")
        )
        return _markdown_table(
            headers,
            [
                (
                    str(item.get("cause", "—")).replace("_", " ").title(),
                    str(item.get("value") or item.get("score") or "—"),
                )
                for item in items
            ],
        )

    if headers and row_builder:
        return _markdown_table(headers, row_builder(items))
    return None


def _result_is_zero_or_empty(db_result: dict[str, Any]) -> bool:
    if not db_result:
        return True
    value = db_result.get("value")
    breakdown = db_result.get("breakdown")
    if value is not None and isinstance(value, (int, float)) and value == 0:
        if not breakdown:
            return True
    return False


def _fallback_markdown_report(
    query: str,
    db_result: dict[str, Any],
    reason: Optional[str] = None,
    locale: str = "zh-CN",
    module: Optional[str] = None,
) -> str:
    """Deterministic executive-style report when Bailian synthesis is unavailable."""
    from orchestrator.module_personas import get_fallback_report_meta

    _ = query  # retained for logging/call-site compatibility; never echoed to users
    zh = locale == "zh-CN"
    report_title, empty_hints = get_fallback_report_meta(locale, module)

    lines = [
        f"### {report_title}",
        "",
        "*MES AI 助手 — 自动摘要*" if zh else "*MES AI Assistant — automated summary*",
        "",
    ]

    if reason:
        lines.extend([
            "> *完整叙述生成暂时不可用。以下结构化发现直接来自实时 MES 记录。*"
            if zh
            else "> *Full narrative generation was temporarily unavailable. "
            "The structured findings below are drawn directly from live MES records.*",
            "",
        ])

    lines.append("---")
    lines.append("")

    if not db_result or _result_is_zero_or_empty(db_result):
        lines.extend([
            "### 发现" if zh else "### Findings",
            "",
            "在数据库日志历史中未找到与所提供参数匹配的交易记录。"
            if zh
            else "No matching transaction records were found in the database log history "
            "for the parameters supplied.",
            "",
            "**建议后续步骤**" if zh else "**Recommended next steps**",
            "",
        ])
        for hint in empty_hints:
            lines.append(f"- {hint}")
        lines.append("")
        return "\n".join(lines)

    lines.extend(["### 关键指标" if zh else "### Key Metrics", ""])

    skip_keys = {
        "breakdown",
        "line_breakdown",
        "lines",
        "devices",
        "hypotheses",
        "low_stock",
        "expiring",
        "stagnant_items",
        "fifo_lots",
        "adjusted_schedule",
        "probable_causes",
        "chain",
        "result",
        "modules",
    }

    labels = _field_labels(locale)

    for key, value in db_result.items():
        if key in skip_keys or _is_empty(value):
            continue
        label = labels.get(key, re.sub(r"_+", " ", key).title())
        display = _translate_scalar(key, value, db_result, locale)
        lines.append(f"- **{label}:** {display}")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Nested anomaly result block
    nested = db_result.get("result")
    if isinstance(nested, dict) and nested:
        lines.extend(["### 分析详情" if zh else "### Analysis Detail", ""])
        for key, value in nested.items():
            if _is_empty(value):
                continue
            label = labels.get(key, re.sub(r"_+", " ", key).title())
            if isinstance(value, list):
                table = _render_list_table(key, value, locale)
                if table:
                    lines.append(table)
                    lines.append("")
                    continue
            lines.append(
                f"- **{label}:** {_translate_scalar(key, value, db_result, locale)}"
            )
        lines.append("---")
        lines.append("")

    section_titles_zh = {
        "breakdown": "产量趋势",
        "line_breakdown": "各产线产量对比",
        "lines": "产线结构",
        "devices": "设备绩效",
        "hypotheses": "质量根因假设",
        "low_stock": "低库存预警",
        "expiring": "临期库存",
        "stagnant_items": "呆滞库存",
        "fifo_lots": "FIFO 批次序列",
        "adjusted_schedule": "排程建议",
        "probable_causes": "可能生产因素",
    }
    section_titles_en = {
        "breakdown": "Production Trend",
        "line_breakdown": "Line Output Comparison",
        "lines": "Factory Line Structure",
        "devices": "Equipment Performance",
        "hypotheses": "Quality Root Cause Hypotheses",
        "low_stock": "Low Stock Alerts",
        "expiring": "Expiring Inventory",
        "stagnant_items": "Stagnant Inventory",
        "fifo_lots": "FIFO Lot Sequence",
        "adjusted_schedule": "Recommended Schedule",
        "probable_causes": "Probable Production Factors",
    }
    section_titles = section_titles_zh if zh else section_titles_en

    for table_key in (
        "breakdown",
        "line_breakdown",
        "lines",
        "devices",
        "hypotheses",
        "low_stock",
        "expiring",
        "stagnant_items",
        "fifo_lots",
        "adjusted_schedule",
        "probable_causes",
    ):
        items = db_result.get(table_key)
        if _is_empty(items) or not isinstance(items, list):
            continue
        section_title = section_titles.get(table_key, "详情" if zh else "Detail")
        lines.extend([f"### {section_title}", ""])
        table = _render_list_table(table_key, items, locale)
        if table:
            lines.append(table)
        lines.append("")
        lines.append("---")
        lines.append("")

    if lines[-1] == "":
        lines.pop()
    if lines and lines[-1] == "---":
        lines.pop()

    return "\n".join(lines)


async def generate_ai_analysis(
    query: str,
    db_result: dict[str, Any],
    rag_context: Optional[str] = None,
    locale: str = "zh-CN",
    module: Optional[str] = None,
) -> str:
    """
    Second-pass Bailian call: convert MCP tool output into a Markdown narrative.

    Falls back to a deterministic summary if credentials are missing or the API fails.
    """
    settings = get_settings()

    if not settings.dashscope_api_key or not settings.bailian_app_id:
        return _fallback_markdown_report(
            query,
            db_result,
            reason="Bailian credentials not configured",
            locale=locale,
            module=module,
        )

    prompt_text = build_synthesis_prompt(query, db_result, rag_context, locale, module)

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                dashscope.Application.call,
                app_id=settings.bailian_app_id,
                prompt=prompt_text,
                api_key=settings.dashscope_api_key,
            ),
            timeout=SYNTHESIS_TIMEOUT_SECONDS,
        )

        if response.status_code != HTTPStatus.OK:
            message = getattr(response, "message", "Unknown Bailian API error")
            logger.warning("Synthesis Bailian error: %s", message)
            return _fallback_markdown_report(query, db_result, reason=message, locale=locale, module=module)

        output_text = (response.output.text or "").strip()
        if not output_text:
            return _fallback_markdown_report(query, db_result, reason="empty response", locale=locale, module=module)

        if settings.debug:
            logger.debug("Bailian synthesis response: %s", output_text[:500])

        return output_text

    except asyncio.TimeoutError:
        logger.warning("Bailian synthesis timed out after %ss", SYNTHESIS_TIMEOUT_SECONDS)
        return _fallback_markdown_report(query, db_result, reason="synthesis timeout", locale=locale, module=module)
    except Exception as exc:
        logger.exception("Unexpected error during Bailian synthesis")
        return _fallback_markdown_report(query, db_result, reason=str(exc), locale=locale, module=module)
