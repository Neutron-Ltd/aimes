"""Locale-aware report synthesis prompts for Bailian."""

from __future__ import annotations

import json
from typing import Any, Optional

from orchestrator.module_personas import get_analyst_context, resolve_module

_SUPPORTED_LOCALES = frozenset({"zh-CN", "en-US"})


def _normalize_locale(locale: str) -> str:
    return locale if locale in _SUPPORTED_LOCALES else "zh-CN"


def build_synthesis_prompt(
    query: str,
    db_result: dict[str, Any],
    rag_context: Optional[str] = None,
    locale: str = "zh-CN",
    module: Optional[str] = None,
) -> str:
    """Build the second-pass Markdown synthesis prompt in the requested locale."""
    locale = _normalize_locale(locale)
    module_key = resolve_module(module)
    analyst_role, style_block = get_analyst_context(locale, module_key)
    result_json = json.dumps(db_result, indent=2, default=str)

    if locale == "zh-CN":
        rag_block = (
            rag_context.strip()
            if rag_context
            else "（无补充知识库上下文。）"
        )
        return f"""{analyst_role}

你的任务是解读结构化数据库查询结果，为相关制造业务方撰写清晰、专业的 Markdown 分析报告。

## 领域报告风格
{style_block}

## 用户问题
{query}

## 结构化数据库结果（JSON）
```json
{result_json}
```

## 背景知识（RAG）
{rag_block}

## 撰写要求
1. 以专家分析师视角 — 用通俗语言解释数字含义，而非简单复述。
2. 突出可执行的洞察：异常下降、峰值时段、阈值突破、库存为空、缺陷激增、排程风险、追溯缺口等（按领域风格选取）。
3. 使用专业 Markdown：简洁标题（`##`）、简短执行摘要、要点列表，必要时附简要建议。
4. 引用 JSON 中的具体数值（日期、产线 ID、数量、比率、设备序列号）以支撑结论。
5. 若结果为空、为零或无匹配记录，请礼貌说明数据库日志中无匹配交易记录，并建议用户调整（日期范围、产线 ID、设备序列号、产品编码）。
6. 不得编造 JSON 或 RAG 上下文中不存在的数据。
7. 不要在报告开头复述用户的原始问题。
8. 不要暴露原始 JSON 键名或 snake_case 字段名 — 使用制造业通用表述（例如用「目标设备」而非 device_sn）。
9. 最终回答中不要输出原始 JSON 代码块 — 仅输出可读的 Markdown。
10. 若存在时间序列 breakdown，请格式化为 Markdown 表格。
11. 报告保持精炼（约 150–400 字，数据集较大时可适当延长）。
12. 全文使用简体中文撰写，包括标题、要点和建议。
13. 当结果为全厂汇总且 JSON 中 `refinement_suggested` 为 true 时，在报告末尾用自然中文引导用户指定产线或产品型号以进一步拆分；若存在 `line_breakdown` 数组，请格式化为各产线对比表格。
14. 计划达成率（`achievement_rate`）表示 SUM(output_qty)/SUM(plan_qty)×100，范围通常 0–150%；说明 `actual_qty`（实际产出）与 `planned_qty`（计划数量）的含义，勿与设备日志 finish_qty 混淆。
15. **名称与编码必须原样复制**：JSON 中的 `area_name`、`area_sn`、`device_sn`、`model_code`、`mo_number`、`product_code` 等字段，在表格和正文中必须与 JSON **逐字一致**，不得改写、翻译、同义替换或替换为读音/字形相近的字（例如 JSON 为「鸿志贴片六线」时不得写成「荣志贴片六线」）；`line_breakdown`、`lines`、`devices` 等数组表格中的产线名称列必须直接使用 JSON 里的 `area_name` 原值。

请现在撰写 Markdown 报告：
"""

    rag_block = (
        rag_context.strip()
        if rag_context
        else "(No supplementary knowledge-base context available.)"
    )
    return f"""{analyst_role}

Your task is to interpret structured database query results and write a clear, professional Markdown report for the relevant manufacturing stakeholders.

## Domain report style
{style_block}

## User question
{query}

## Structured database result (JSON)
```json
{result_json}
```

## Background knowledge (RAG)
{rag_block}

## Instructions
1. Act as an expert analyst — explain what the numbers mean in plain language, not just restate them.
2. Highlight actionable insights appropriate to this domain: unusual drops, peak periods, threshold breaches, empty inventory, defect spikes, scheduling risks, traceability gaps, etc.
3. Use professional Markdown: a concise title (`##`), short executive summary, bullet points for key findings, and a brief recommendations section when appropriate.
4. Reference specific values from the JSON (dates, line IDs, quantities, rates, device serials) when they support your conclusions.
5. If the result is empty, zero, or contains no matching records, politely explain that no transaction records match that combination in the database log history. Suggest what the user might adjust (date range, line ID, device serial, product code).
6. Do NOT invent data that is not present in the JSON or RAG context.
7. Do NOT echo the user's raw question back at the top of the report.
8. Do NOT expose raw JSON keys or snake_case field names — use plain manufacturing language (e.g. "Target Equipment" not "device_sn").
9. Do NOT output raw JSON blocks in your final answer — only human-readable Markdown.
10. Format time-series breakdowns as Markdown tables when present.
11. Keep the report focused (roughly 150–400 words unless the dataset is large).
12. Write the entire report in English, including headings, bullets, and recommendations.
13. When the result is a plant-wide summary and `refinement_suggested` is true in the JSON, end with a natural prompt asking which line or product to drill into; format `line_breakdown` as a comparative table when present.
14. Plan `achievement_rate` is SUM(output_qty)/SUM(plan_qty)×100 (typically 0–150%); explain `actual_qty` vs `planned_qty`; do not confuse with equipment-log finish_qty.
15. **Copy names and codes exactly**: fields such as `area_name`, `area_sn`, `device_sn`, `model_code`, `mo_number`, and `product_code` in tables and prose must match the JSON **character-for-character** — do not paraphrase, translate, substitute synonyms, or swap visually or phonetically similar characters (e.g. if JSON says 「鸿志贴片六线」, never write 「荣志贴片六线」); line-name columns in `line_breakdown`, `lines`, `devices`, and similar arrays must use the exact `area_name` value from JSON.

Write the Markdown report now:
"""
