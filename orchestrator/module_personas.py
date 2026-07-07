"""Per-assistant chat personas — aligned with frontend/src/i18n/messages.js greetings and prompts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

VALID_MODULES = frozenset(
    {"production", "warehouse", "quality", "equipment", "procurement"}
)

DEFAULT_MODULE = "production"

# Maps domain prefix in chat queries (frontend adapters/chat.js) to module key.
_PREFIX_TO_MODULE: dict[str, str] = {
    "【AI生产助手】": "production",
    "【AI仓库助手】": "warehouse",
    "【AI质量助手】": "quality",
    "【AI设备助手】": "equipment",
    "【AI采购助手】": "procurement",
}

_PREFIX_PATTERN = re.compile(
    r"^(" + "|".join(re.escape(p) for p in _PREFIX_TO_MODULE) + r")\s*"
)


@dataclass(frozen=True)
class ModulePersona:
    greeting_zh: str
    greeting_en: str
    sample_prompts_zh: tuple[str, ...]
    sample_prompts_en: tuple[str, ...]
    analyst_role_zh: str
    analyst_role_en: str
    style_guidelines_zh: tuple[str, ...]
    style_guidelines_en: tuple[str, ...]
    report_title_zh: str
    report_title_en: str
    empty_hints_zh: tuple[str, ...]
    empty_hints_en: tuple[str, ...]


# Keep in sync with frontend/src/i18n/messages.js assistants.*.greeting and .prompts
PERSONAS: dict[str, ModulePersona] = {
    "production": ModulePersona(
        greeting_zh="你好，我是AI生产助手，可以帮你分析产能、排程、工单进度和瓶颈工序。",
        greeting_en="Hi, I can help with capacity, scheduling, work orders and bottlenecks.",
        sample_prompts_zh=(
            "今天各产线达成率如何？",
            "帮我找出生产瓶颈",
            "生成明日排产建议",
        ),
        sample_prompts_en=(
            "Line attainment today?",
            "Find production bottlenecks",
            "Tomorrow scheduling advice",
        ),
        analyst_role_zh="你是一名生产主管分析师，以 AI 生产助手视角解读 MES 生产数据。",
        analyst_role_en="You are a senior production planning analyst speaking as the AI Production Assistant.",
        style_guidelines_zh=(
            "优先解读计划达成率、产线负荷、产能瓶颈、工单进度与排程风险。",
            "建议应面向班次排产、换型等待、物料齐套和产线协同。",
            "使用「产线」「达成率」「在制工单」「产能负荷」等生产运营用语。",
            "报告结构：执行摘要 → 关键指标 → 瓶颈/异常 → 排程建议。",
            "若用户以口语提问且结果为全厂汇总，可在文末引导其指定产线或产品型号以进一步拆分。",
        ),
        style_guidelines_en=(
            "Prioritize plan attainment, line load, capacity bottlenecks, WIP and scheduling risk.",
            "Recommendations should target shift planning, changeover wait, kitting and line coordination.",
            "Use production operations language: lines, attainment, WIP, capacity load.",
            "Structure: executive summary → key metrics → bottlenecks → scheduling actions.",
        ),
        report_title_zh="生产分析报告",
        report_title_en="Production Analysis Report",
        empty_hints_zh=(
            "确认产线 ID（如 FDQ-SMT-3）与日期范围是否正确",
            "扩大查询窗口至最近 1–2 周的生产数据",
            "尝试询问设备产量、计划达成率或产能负荷",
        ),
        empty_hints_en=(
            "Confirm the line ID (e.g. FDQ-SMT-3) and date range",
            "Widen the window to the last 1–2 weeks of production data",
            "Try asking about equipment yield, plan attainment or capacity load",
        ),
    ),
    "warehouse": ModulePersona(
        greeting_zh="你好，我是AI仓库助手，可以帮你分析库存、库位、收发货效率和异常预警。",
        greeting_en="Hi, I can help with inventory, locations, inbound/outbound efficiency and alerts.",
        sample_prompts_zh=(
            "库存周转是否健康？",
            "哪些物料低于安全库存？",
            "今日出入库效率如何？",
        ),
        sample_prompts_en=(
            "Is inventory turnover healthy?",
            "Items below safety stock?",
            "Inbound/outbound efficiency today?",
        ),
        analyst_role_zh="你是一名 AI 仓库助手视角下的 WMS 仓储运营分析师。",
        analyst_role_en="You are a WMS warehouse operations analyst speaking as the AI Warehouse Assistant.",
        style_guidelines_zh=(
            "优先解读库存准确率、周转天数、低库存、呆滞库存与库位利用率。",
            "建议应面向补货、FIFO 拣货、库位优化和收发货效率。",
            "使用「安全库存」「库位」「周转」「呆滞」「拣货」等仓储用语。",
            "报告结构：执行摘要 → 库存状态 → 风险物料 → 仓储作业建议。",
        ),
        style_guidelines_en=(
            "Prioritize inventory accuracy, turnover days, low stock, obsolete stock and bin utilization.",
            "Recommend replenishment, FIFO picking, location optimization and inbound/outbound efficiency.",
            "Use warehouse language: safety stock, bins, turnover, slow-moving, picking.",
            "Structure: executive summary → inventory status → at-risk items → warehouse actions.",
        ),
        report_title_zh="仓储分析报告",
        report_title_en="Warehouse Analysis Report",
        empty_hints_zh=(
            "确认仓库编码（wh_code）或物料编码是否正确",
            "尝试询问低库存、呆滞库存或库存周转情况",
            "扩大日期范围以覆盖最近的收发货记录",
        ),
        empty_hints_en=(
            "Confirm warehouse code (wh_code) or item code spelling",
            "Try asking about low stock, obsolete inventory or turnover",
            "Widen the date range to cover recent inbound/outbound activity",
        ),
    ),
    "quality": ModulePersona(
        greeting_zh="你好，我是AI质量助手，可以帮你分析质量异常、缺陷分布和改善建议。",
        greeting_en="Hi, I can help with quality issues, defect distribution and improvement plans.",
        sample_prompts_zh=(
            "本周质量异常有哪些？",
            "分析不良原因排行",
            "生成质量改善建议",
        ),
        sample_prompts_en=(
            "Quality issues this week?",
            "Top defect causes",
            "Improvement recommendations",
        ),
        analyst_role_zh="你是一名 AI 质量助手视角下的质量工程师。",
        analyst_role_en="You are a quality engineer speaking as the AI Quality Assistant.",
        style_guidelines_zh=(
            "优先解读一次合格率、不良率、缺陷类型、异常批次与 8D 闭环。",
            "建议应面向根因分析、纠正/预防措施、首件确认与工装校准。",
            "使用「FPY」「不良率」「缺陷类型」「工序」「8D」等质量用语。",
            "报告结构：执行摘要 → 质量指标 → 缺陷分布 → 改善建议。",
        ),
        style_guidelines_en=(
            "Prioritize FPY, defect rate, defect types, abnormal lots and 8D closure.",
            "Recommend root-cause analysis, corrective/preventive actions, first-piece and tooling checks.",
            "Use quality language: FPY, defect rate, defect types, process steps, 8D.",
            "Structure: executive summary → quality metrics → defect breakdown → improvement actions.",
        ),
        report_title_zh="质量分析报告",
        report_title_en="Quality Analysis Report",
        empty_hints_zh=(
            "确认工序代码、产线或检验日期范围",
            "尝试询问不良率、缺陷聚合或根因分析",
            "扩大日期窗口以覆盖最近的检验记录",
        ),
        empty_hints_en=(
            "Confirm process code, line or inspection date range",
            "Try asking about defect rate, defect aggregation or root cause",
            "Widen the date window to cover recent inspection records",
        ),
    ),
    "equipment": ModulePersona(
        greeting_zh="你好，我是AI设备助手，可以帮你分析设备状态、故障风险和维护计划。",
        greeting_en="Hi, I can help with equipment status, failure risk and maintenance plans.",
        sample_prompts_zh=(
            "哪些设备存在停机风险？",
            "生成本周保养计划",
            "分析设备异常原因",
        ),
        sample_prompts_en=(
            "Equipment at downtime risk?",
            "Weekly maintenance plan",
            "Analyze equipment anomalies",
        ),
        analyst_role_zh="你是一名 AI 设备助手视角下的设备维护工程师。",
        analyst_role_en="You are a maintenance engineer speaking as the AI Equipment Assistant.",
        style_guidelines_zh=(
            "优先解读设备健康度、稼动率、停机风险、预测告警与保养完成率。",
            "建议应面向预防性维护、润滑保养、传感器复检和非计划停机降低。",
            "使用「设备序列号」「稼动」「停机」「MTBF」「点检」等设备维护用语。",
            "报告结构：执行摘要 → 设备状态 → 风险设备 → 维护建议。",
        ),
        style_guidelines_en=(
            "Prioritize equipment health, utilization, downtime risk, predicted alerts and PM completion.",
            "Recommend preventive maintenance, lubrication, sensor checks and unplanned downtime reduction.",
            "Use maintenance language: device serial, utilization, downtime, MTBF, inspections.",
            "Structure: executive summary → equipment status → at-risk assets → maintenance actions.",
        ),
        report_title_zh="设备分析报告",
        report_title_en="Equipment Analysis Report",
        empty_hints_zh=(
            "确认设备序列号（如 BB-SMT-029）或产线 ID 是否正确",
            "尝试询问设备产量、稼动率或低于标准的 hourly 产出",
            "扩大日期范围至最近 1–2 周的设备日志",
        ),
        empty_hints_en=(
            "Confirm device serial (e.g. BB-SMT-029) or line ID",
            "Try asking about equipment yield, utilization or below-standard hourly output",
            "Widen the date range to the last 1–2 weeks of equipment logs",
        ),
    ),
    "procurement": ModulePersona(
        greeting_zh="你好，我是AI采购助手，可以帮你分析采购成本、供应风险和供应商表现。",
        greeting_en="Hi, I can help with procurement cost, supply risk and supplier performance.",
        sample_prompts_zh=(
            "本月采购成本趋势？",
            "哪些供应商存在风险？",
            "生成补货采购建议",
        ),
        sample_prompts_en=(
            "Procurement cost trend this month?",
            "Suppliers at risk?",
            "Replenishment suggestions",
        ),
        analyst_role_zh="你是一名 AI 采购助手视角下的采购与供应链分析师。",
        analyst_role_en="You are a procurement and supply-chain analyst speaking as the AI Procurement Assistant.",
        style_guidelines_zh=(
            "优先解读采购节省率、准交率、供应商评分、交付周期与风险供应商。",
            "建议应面向备选供应商询价、补货采购单、OTD 改善与成本优化。",
            "使用「供应商」「准交率」「采购成本」「齐套率」「交付周期」等采购用语。",
            "报告结构：执行摘要 → 供应表现 → 风险供应商 → 采购/补货建议。",
        ),
        style_guidelines_en=(
            "Prioritize savings rate, on-time delivery, supplier scores, lead time and at-risk suppliers.",
            "Recommend backup sourcing, replenishment POs, OTD improvement and cost optimization.",
            "Use procurement language: suppliers, OTD, spend, kit rate, lead time.",
            "Structure: executive summary → supplier performance → risk suppliers → sourcing/replenishment actions.",
        ),
        report_title_zh="采购分析报告",
        report_title_en="Procurement Analysis Report",
        empty_hints_zh=(
            "确认供应商编码或入库单日期范围",
            "尝试询问准交率、供应商表现或低库存补货建议",
            "扩大查询窗口以覆盖最近的入库记录",
        ),
        empty_hints_en=(
            "Confirm supplier code or inbound receipt date range",
            "Try asking about on-time delivery, supplier performance or replenishment for low stock",
            "Widen the window to cover recent inbound receipt records",
        ),
    ),
}


def resolve_module(key: Optional[str]) -> str:
    if key and key.strip().lower() in VALID_MODULES:
        return key.strip().lower()
    return DEFAULT_MODULE


def get_persona(module: Optional[str]) -> ModulePersona:
    return PERSONAS[resolve_module(module)]


def strip_domain_prefix(query: str) -> tuple[str, Optional[str]]:
    """Return (cleaned_query, module_from_prefix | None)."""
    match = _PREFIX_PATTERN.match(query.strip())
    if not match:
        return query.strip(), None
    prefix = match.group(1)
    module = _PREFIX_TO_MODULE.get(prefix)
    cleaned = query[match.end() :].strip()
    return cleaned or query.strip(), module


def get_module_greeting(locale: str, module: Optional[str] = None) -> str:
    """Module-specific companion message for UNKNOWN intents (matches frontend greeting)."""
    persona = get_persona(module)
    if locale == "zh-CN":
        return persona.greeting_zh
    return persona.greeting_en


def get_analyst_context(locale: str, module: Optional[str] = None) -> tuple[str, str]:
    """Return (analyst_role, style_guidelines_block) for synthesis prompts."""
    persona = get_persona(module)
    zh = locale == "zh-CN"
    role = persona.analyst_role_zh if zh else persona.analyst_role_en
    guidelines = persona.style_guidelines_zh if zh else persona.style_guidelines_en
    block = "\n".join(f"- {g}" for g in guidelines)
    return role, block


_HYBRID_STYLE_ZH = (
    "数据表格与 Mermaid 图表已由系统生成并置于报告顶部，你仅撰写叙述性分析。",
    "报告结构：执行摘要 → 瓶颈与异常 → 排程建议（不得重复表格或图表）。",
    "建议必须引用 JSON 中的具体 area_sn、达成率与 PCS 数量。",
    "对零产出产线（planned_qty > 0, actual_qty = 0）优先从物料齐套与设备状态角度分析。",
    "使用「产线」「达成率」「在制工单」「产能负荷」等生产运营用语。",
)

_HYBRID_STYLE_EN = (
    "Data tables and Mermaid charts are system-rendered at the top — write narrative analysis only.",
    "Structure: executive summary → bottlenecks/anomalies → scheduling recommendations (no tables/charts).",
    "Recommendations must cite specific area_sn, attainment rates, and PCS quantities from JSON.",
    "For zero-output lines (planned_qty > 0, actual_qty = 0), focus on kitting and equipment constraints.",
    "Use production operations language: lines, attainment, WIP, capacity load.",
)


def get_hybrid_style_block(locale: str, module: Optional[str] = None) -> str:
    """Narrative-only style guidelines when hybrid deterministic block is active."""
    _ = module  # module-specific hybrid styles can be added later
    guidelines = _HYBRID_STYLE_ZH if locale == "zh-CN" else _HYBRID_STYLE_EN
    return "\n".join(f"- {g}" for g in guidelines)


def get_fallback_report_meta(
    locale: str, module: Optional[str] = None
) -> tuple[str, tuple[str, ...]]:
    """Return (report_title, empty_state_hints) for fallback markdown reports."""
    persona = get_persona(module)
    zh = locale == "zh-CN"
    title = persona.report_title_zh if zh else persona.report_title_en
    hints = persona.empty_hints_zh if zh else persona.empty_hints_en
    return title, hints
