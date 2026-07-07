# Visualization to Database Schema / 可视化与数据库对照表

Maps each assistant dashboard chart to its visualization type, live vs fallback status, underlying database tables, and data-source rationale. Companion to the module integration report in [integration.md](./integration.md).

**Legend / 图例**

| Status | Meaning |
|--------|---------|
| **Live / 实时** | Chart data comes from MCP tools or SQL against live MES tables |
| **Fallback / 回退** | No live source wired; frontend uses static mock series |

| Mark | Meaning |
|------|---------|
| ✅ | Matches frontend i18n chart slot + backend dashboard builder (`core/dashboard/{module}.py`) + live/fallback wiring |
| ❌ | Doc row does not match the integrated codebase (wrong chart name, status, or tables not referenced in code) |

*Verified against `frontend/src/i18n/messages.js`, `frontend/src/adapters/chartSlots.js`, and `core/dashboard/*.py`.*

---

## Chat report charts (hybrid synthesis)

Separate from the six **dashboard ECharts** slots, the AI chat console can render **Mermaid** diagrams embedded in Markdown replies.

| Aspect | Detail |
|--------|--------|
| **When** | MCP tool JSON contains list arrays (`line_breakdown`, `breakdown` with rates, etc.) — hybrid mode in [`orchestrator/report_generator.py`](../orchestrator/report_generator.py) |
| **Generator** | Python `_generate_mermaid_attainment_chart()` / `_generate_mermaid_trend_chart()` — `xychart-beta` bar or line |
| **Renderer** | `frontend/src/utils/markdown.js` → `initMermaidIn()`; triggered from `AssistantChatConsole.vue` |
| **Data source** | Same MCP JSON as the deterministic Markdown table (not a separate API) |
| **Example** | Plan attainment query → bar chart of `achievement_rate` by `area_sn` + full 5-column table |

Dashboard charts (below) use **ECharts** via `GET /api/v1/assistants/{module}/dashboard`. Chat charts use **Mermaid** via `POST /api/v1/query` hybrid reports.

---

## 1. Production / AI生产助手

### Charts / 图表

| ✓ | Name / 名称 | Type / 类型 | Status / 状态 | Tables / 数据表 | Why this source / 数据来源说明 |
|---|-------------|-------------|---------------|-----------------|-------------------------------|
| ✅ | 产线达成趋势 (Line Attainment Trend) | 折线图 (Line) | Live / 实时 | `t_smt_program_consumption_record`, `t_co_device` | Daily equipment achievement breakdown matches “line trend” intent. |
| ✅ | 工单状态分布 (Work Order Status) | 柱状图 (Bar) | Fallback / 回退 | `t_pm_project_base` | No work-order status aggregation tool. |
| ✅ | 产能负荷 (Capacity Load) | 仪表盘 (Gauge) | Live / 实时 | `t_smt_program_consumption_record`, `t_co_device`, `t_co_standard_time` | Capacity engine computes utilization % from historical throughput vs standard time. |
| ✅ | 产线负荷对比 (Line Load Comparison) | 柱状图 (Bar) | Live / 实时 | `t_smt_program_consumption_record`, `t_co_device` | Top 5 devices by avg rate show relative load across machines on the line. |
| ✅ | 不良品分析 (Defect Analysis) | 折线图 (Line) | Live / 实时 | `t_wip_detail` | Monthly sum of `ng_qty + scrap_qty` from WIP station records on the line. |
| ✅ | 异常停机分析 (Downtime Analysis) | 柱状图 (Bar) | Live / 实时 | `t_smt_program_consumption_record`, `t_co_device` | Hourly buckets below achievement threshold proxy “abnormal downtime”. |

---

## 2. Warehouse / AI仓库助手

### Charts / 图表

| ✓ | Name / 名称 | Type / 类型 | Status / 状态 | Tables / 数据表 | Why this source / 数据来源说明 |
|---|-------------|-------------|---------------|-----------------|-------------------------------|
| ✅ | 出入库趋势 (Inbound/Outbound Trend) | 折线/柱状 (Line/Bar) | Fallback / 回退 | `t_wms_outstock_item`, `t_wms_receive_item` | No inbound/outbound time-series MCP tool yet. |
| ✅ | 库存结构 (Inventory Structure) | 柱状图 (Bar) | Live / 实时 | `t_wms_stock_info`, `t_co_item` | Healthy vs low-stock vs expiring counts match UI categories. |
| ✅ | 库位利用率 (Bin Utilization) | 仪表盘 (Gauge) | Live / 实时 | `t_wms_area`, `t_wms_stock_info` | Occupied distinct `storage_code` / total areas in `t_wms_area`. |
| ✅ | 呆滞库存分析 (Slow-moving Stock) | 柱状图 (Bar) | Live / 实时 | `t_wms_stock_info` | Age buckets from `instock_time` (0–30d … 180d+) align with UI x-axis labels. |
| ✅ | 拣货效率趋势 (Picking Efficiency) | 折线图 (Line) | Fallback / 回退 | — | No picking-efficiency time series in WMS MCP layer. |
| ✅ | 收货及时率 (Receiving On-time Rate) | 仪表盘 (Gauge) | Fallback / 回退 | — | No receiving OTD tool in warehouse MCP set. |

---

## 3. Quality / AI质量助手

### Charts / 图表

| ✓ | Name / 名称 | Type / 类型 | Status / 状态 | Tables / 数据表 | Why this source / 数据来源说明 |
|---|-------------|-------------|---------------|-----------------|-------------------------------|
| ✅ | 不良率趋势 (Defect Rate Trend) | 折线图 (Line) | Live / 实时 | `t_qm_inspect_info` | Daily `(error_qty / real_qty) × 100` — direct defect trend. |
| ✅ | 缺陷类型排行 (Defect Type Ranking) | 柱状图 (Bar) | Live / 实时 | `t_qm_problem_report`, `t_qm_problem_reason` | Top reasons from root-cause hypotheses. |
| ✅ | 质量健康度 (Quality Health) | 仪表盘 (Gauge) | Live / 实时 | `t_qm_inspect_info` | `100 − defect_rate` as health score. |
| ✅ | 返修率趋势 (Rework Rate Trend) | 折线图 (Line) | Live / 实时 | `t_qm_inspect_info` | Uses daily defect rate as rework proxy. |
| ✅ | 工序良率对比 (Process Yield) | 柱状图 (Bar) | Live / 实时 | `t_qm_inspect_info` | Per-process yield = `100 − process defect_rate`. |
| ✅ | 检验及时率 (Inspection On-time) | 仪表盘 (Gauge) | Fallback / 回退 | — | No on-time inspection MCP tool wired. |

---

## 4. Equipment / AI设备助手

### Charts / 图表

| ✓ | Name / 名称 | Type / 类型 | Status / 状态 | Tables / 数据表 | Why this source / 数据来源说明 |
|---|-------------|-------------|---------------|-----------------|-------------------------------|
| ✅ | 设备健康趋势 (Equipment Health Trend) | 折线图 (Line) | Live / 实时 | `t_smt_program_consumption_record`, `t_co_device` | Daily achievement % tracks health over time. |
| ✅ | 告警等级分布 (Alert Level Distribution) | 柱状图 (Bar) | Fallback / 回退 | — | No alert severity taxonomy in DB. |
| ✅ | 维护完成率 (Maintenance Completion) | 仪表盘 (Gauge) | Live / 实时 | `t_co_device` | Devices with valid `expire_date` / total registered. |
| ✅ | 停机时长分析 (Downtime by Equipment) | 柱状图 (Bar) | Live / 实时 | `t_smt_program_consumption_record`, `t_co_device` | Inverse of avg rate vs max rate as downtime proxy. |
| ✅ | MTBF趋势 (MTBF Trend) | 折线图 (Line) | Fallback / 回退 | — | No MTBF time-series source. |
| ✅ | 点检完成率 (Inspection Completion) | 仪表盘 (Gauge) | Live / 实时 | `t_co_device` | Active devices with logs / registered devices. |

---

## 5. Procurement / AI采购助手

### Charts / 图表

| ✓ | Name / 名称 | Type / 类型 | Status / 状态 | Tables / 数据表 | Why this source / 数据来源说明 |
|---|-------------|-------------|---------------|-----------------|-------------------------------|
| ✅ | 采购金额趋势 (Procurement Spend Trend) | 折线图 (Line) | Live / 实时 | `t_wms_receive_item`, `t_wms_receive_doc` | Daily sum of `receive_qty × single_price`. |
| ✅ | 供应商评分 (Supplier Scores) | 柱状图 (Bar) | Live / 实时 | `t_wms_receive_doc`, `t_co_supplier` | Top 5 suppliers by volume; bar = OTD %. |
| ✅ | 供应链稳定性 (Supply Chain Stability) | 仪表盘 (Gauge) | Live / 实时 | `t_wms_receive_doc` | `100 − late_delivery_rate`. |
| ✅ | 交付周期对比 (Lead Time Comparison) | 柱状图 (Bar) | Live / 实时 | `t_wms_receive_doc` | Avg lead days by `abc_type`. |
| ✅ | 议价空间趋势 (Negotiation Margin) | 折线图 (Line) | Fallback / 回退 | — | No price-history table. |
| ✅ | 物料齐套率 (Material Kit Rate) | 仪表盘 (Gauge) | Live / 实时 | `t_wms_stock_info` | Items with `stock_qty ≥ min_stock` / items with `min_stock > 0`. |

---

## Database table reference / 数据库表索引

Tables referenced by live dashboard SQL or MCP tools in `core/dashboard/*.py`.

| ✓ | Table / 表名 | Modules (count) / 使用模块 (计数) | Role / 作用 |
|---|--------------|-----------------------------------|-------------|
| ✅ | `t_smt_program_consumption_record` | 2 — Production / 生产, Equipment / 设备 | Machine logs / 设备日志 |
| ✅ | `t_co_device` | 2 — Production / 生产, Equipment / 设备 | Device registry / 设备注册 |
| ✅ | `t_wms_stock_info` | 2 — Warehouse / 仓库, Procurement / 采购 | On-hand inventory / 现有库存 |
| ✅ | `t_wip_detail` | 1 — Production / 生产 | WIP station records; monthly defect counts (`ng_qty`, `scrap_qty`) / 过站详情与不良数量 |
| ✅ | `t_wms_receive_doc` | 1 — Procurement / 采购 | Inbound header / 入库单据头 — **procurement dashboard only; warehouse dashboard does not query this table** |
| ✅ | `t_qm_inspect_info` | 1 — Quality / 质量 | Inspection qty, defects / 检验数量与缺陷 |
| ✅ | `t_co_item` | 1 — Warehouse / 仓库 | Item registry / 物料注册 — **also joined in procurement spend SQL** |
| ✅ | `t_co_standard_time` | 1 — Production / 生产 | Standard times / 标准工时 |
| ✅ | `t_wms_area` | 1 — Warehouse / 仓库 | Storage areas / 存储区域 |
| ✅ | `t_qm_problem_report` | 1 — Quality / 质量 | Problem reports / 问题报告 |
| ✅ | `t_qm_problem_reason` | 1 — Quality / 质量 | Problem reasons / 问题原因 |
| ✅ | `t_co_supplier` | 1 — Procurement / 采购 | Supplier registry / 供应商注册 |
| ✅ | `t_wms_receive_item` | 1 — Procurement / 采购 | Receive line items / 入库明细项 |

**Tables listed in chart rows above but not present in dashboard code:** `t_pm_project_base`, `t_wms_outstock_item` (fallback placeholders only; no SQL references).
