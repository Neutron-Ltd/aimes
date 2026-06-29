# Assistant Integration Report / 助手集成报告

This document describes how each AI assistant module was integrated with the NEUTRON MES backend: dashboard charts, database tables, fallback behavior, and chat wiring. Labels match the frontend i18n in [`frontend/src/i18n/messages.js`](../frontend/src/i18n/messages.js).

---

## Shared architecture / 共用架构

### Dashboard flow / 看板数据流

```
Assistant page (index.vue)
  → use*AssistantPage.js
  → useIntegratedAssistantPage.js
  → GET /api/v1/assistants/{module}/dashboard
  → core/dashboard/{module}.py
  → MCP tools + SQL aggregations
  → { kpis[], charts[], insight, partial }
  → adapters/chartSlots.js merges live slots over mock data
```

### Chat flow / 对话数据流

```
AssistantChatConsole.vue
  → useAssistantChat.js (when module ∈ VITE_INTEGRATED_ASSISTANTS)
  → adapters/chat.js → POST /api/v1/query
     • query: 【AI…助手】 + user message
     • assistant_module: production | warehouse | quality | equipment | procurement
  → orchestrator/router.py
     • UNKNOWN intent → module greeting (orchestrator/module_personas.py)
     • tool intent → MCP + module-specific synthesis prompt
```

### Live vs fallback / 实时与回退

Each KPI/chart slot returns `source: "live"` or `"fallback"`. When `fallback`, the frontend keeps the static mock series from `charts.js`. When any slot falls back, the API sets `partial: true`.

### Environment / 环境变量

| Variable | Purpose |
|----------|---------|
| `VITE_INTEGRATED_ASSISTANTS` | Comma-separated modules using live dashboard + chat |
| `VITE_DEFAULT_LINE_ID` | Scope for production, quality, equipment (`line_id`) |
| `VITE_DEFAULT_WH_CODE` | Optional scope for warehouse, procurement (`wh_code`) |
| `DASHBOARD_REFERENCE_DATE` | Caps lookback window to last MES snapshot date |

---

## 1. Production / AI生产助手 (Product Assistant)

| Item | Value |
|------|-------|
| Route | `/assistant/production` |
| Module key | `production` |
| Backend builder | [`core/dashboard/production.py`](../core/dashboard/production.py) |
| Frontend composable | [`useProductionAssistantPage.js`](../frontend/src/composables/useProductionAssistantPage.js) |
| Dashboard API | `GET /api/v1/assistants/production/dashboard?line_id=…` |
| Scope param | `line_id` (required; default `FDQ-SMT-3`) |

### KPIs / 指标卡

| Index | 中文 | English | Source | Tables / tools | Why this source |
|-------|------|---------|--------|----------------|-----------------|
| 0 | 计划达成率 | Plan Attainment | **Live** | `get_yield_aggregation` → `t_smt_program_consumption_record`, `t_co_device` | Equipment achievement rate (`finish_qty / mount_sheet_qty`) is the closest live proxy for plan attainment on a line. |
| 0 trend | — | — | **Live** | `compare_yield_periods` (same tables) | Period-over-period growth for KPI trend arrow. |
| 1 | 设备稼动率 | Equipment Utilization | **Live** | `get_device_production_rate` → `t_smt_program_consumption_record` + `t_co_device` | Average `finish_qty` per device on the line; no dedicated OEE/utilization table. |
| 2 | 在制工单 | WIP Orders | **Fallback** | — | No MCP tool or WMS/MES table wired for open work-order count. |

### Charts / 图表

| Index | 中文 | English | Type | Status | Tables / tools | Why this source |
|-------|------|---------|------|--------|----------------|-----------------|
| 0 | 产线达成趋势 | Line Attainment Trend | line | **Live** | `get_yield_aggregation` (daily, achievement) → `t_smt_program_consumption_record`, `t_co_device` | Daily equipment achievement breakdown matches “line trend” intent. |
| 1 | 工单状态分布 | Work Order Status | bar | **Fallback** | — | No work-order status aggregation tool. |
| 2 | 产能负荷 | Capacity Load | gauge | **Live** | `forecast_capacity_hr` → `t_smt_program_consumption_record`, `t_co_device`, `t_co_standard_time` | Capacity engine computes utilization % from historical throughput vs standard time. |
| 3 | 产线负荷对比 | Line Load Comparison | bar | **Live** | `get_device_production_rate` → `t_smt_program_consumption_record`, `t_co_device` | Top 5 devices by avg rate show relative load across machines on the line. |
| 4 | OEE趋势 | OEE Trend | line | **Fallback** | — | Device rate tool has no daily OEE series; no OEE fact table. |
| 5 | 异常停机分析 | Downtime Analysis | bar | **Live** | `get_yield_anomalies` (below_standard) → `t_smt_program_consumption_record`, `t_co_device` | Hourly buckets below achievement threshold proxy “abnormal downtime / underperformance”. |

### Chat integration / 对话集成

| Item | Detail |
|------|--------|
| Domain prefix | `【AI生产助手】` |
| `assistant_module` | `production` |
| Static greeting (UI) | 你好，我是AI生产助手，可以帮你分析产能、排程、工单进度和瓶颈工序。 / Hi, I can help with capacity, scheduling, work orders and bottlenecks. |
| Persona | Production planning analyst — focuses on attainment, scheduling, bottlenecks, capacity load |
| Sample prompts | 今天各产线达成率如何？ / Line attainment today? · 帮我找出生产瓶颈 / Find production bottlenecks · 生成明日排产建议 / Tomorrow scheduling advice |
| NL routing | Existing production intents: yield aggregation, device rate, capacity forecast, root cause, schedule optimization |

---

## 2. Warehouse / AI仓库助手 (Stock Assistant)

| Item | Value |
|------|-------|
| Route | `/assistant/warehouse` |
| Module key | `warehouse` |
| Backend builder | [`core/dashboard/warehouse.py`](../core/dashboard/warehouse.py) |
| Frontend composable | [`useWarehouseAssistantPage.js`](../frontend/src/composables/useWarehouseAssistantPage.js) |
| Dashboard API | `GET /api/v1/assistants/warehouse/dashboard?wh_code=…` |
| Scope param | `wh_code` (optional; empty = all warehouses) |

### KPIs / 指标卡

| Index | 中文 | English | Source | Tables / tools | Why this source |
|-------|------|---------|--------|----------------|-----------------|
| 0 | 库存准确率 | Inventory Accuracy | **Live** | SQL `_fetch_stock_summary` → `t_wms_stock_info`, `t_co_item` | Derived: rows that are neither low-stock nor expiring within 30 days / total stock rows. |
| 1 | 周转天数 | Turnover Days | **Live** | Same SQL | Average days since `instock_time` — standard WMS turnover proxy. |
| 2 | 待拣任务 | Pick Tasks | **Live** | `get_inventory_status` → `t_wms_stock_info`, `t_co_item` | Count of low-stock items from MCP tool used as “pending pick/replenishment” proxy. |

### Charts / 图表

| Index | 中文 | English | Type | Status | Tables / tools | Why this source |
|-------|------|---------|------|--------|----------------|-----------------|
| 0 | 出入库趋势 | Inbound/Outbound Trend | line/bar | **Fallback** | — | No inbound/outbound time-series MCP tool yet. |
| 1 | 库存结构 | Inventory Structure | bar | **Live** | `_fetch_stock_summary` → `t_wms_stock_info`, `t_co_item` | Healthy vs low-stock vs expiring counts match UI categories. |
| 2 | 库位利用率 | Bin Utilization | gauge | **Live** | `_fetch_bin_utilization` → `t_wms_area`, `t_wms_stock_info` | Occupied distinct `storage_code` / total areas in `t_wms_area`. |
| 3 | 呆滞库存分析 | Slow-moving Stock | bar | **Live** | `_fetch_age_buckets` → `t_wms_stock_info` | Age buckets from `instock_time` (0–30d … 180d+) align with UI x-axis labels. |
| 4 | 拣货效率趋势 | Picking Efficiency | line | **Fallback** | — | No picking-efficiency time series in WMS MCP layer. |
| 5 | 收货及时率 | Receiving On-time Rate | gauge | **Fallback** | — | No receiving OTD tool in warehouse MCP set (procurement builder covers receive docs separately). |

### Chat integration / 对话集成

| Item | Detail |
|------|--------|
| Domain prefix | `【AI仓库助手】` |
| `assistant_module` | `warehouse` |
| Static greeting (UI) | 你好，我是AI仓库助手，可以帮你分析库存、库位、收发货效率和异常预警。 / Hi, I can help with inventory, locations, inbound/outbound efficiency and alerts. |
| Persona | WMS warehouse operator — inventory, bins, FIFO, turnover, obsolete stock |
| Sample prompts | 库存周转是否健康？ / Is inventory turnover healthy? · 哪些物料低于安全库存？ / Items below safety stock? · 今日出入库效率如何？ / Inbound/outbound efficiency today? |
| NL routing | Warehouse intents: inventory status, obsolete profile, inbound/outbound guide, material trace |

---

## 3. Quality / AI质量助手 (Quality Assistant)

| Item | Value |
|------|-------|
| Route | `/assistant/quality` |
| Module key | `quality` |
| Backend builder | [`core/dashboard/quality.py`](../core/dashboard/quality.py) |
| Frontend composable | [`useQualityAssistantPage.js`](../frontend/src/composables/useQualityAssistantPage.js) |
| Dashboard API | `GET /api/v1/assistants/quality/dashboard?line_id=…` |
| Scope param | `line_id` (optional; default or global if empty) |

### KPIs / 指标卡

| Index | 中文 | English | Source | Tables / tools | Why this source |
|-------|------|---------|--------|----------------|-----------------|
| 0 | 一次合格率 | First Pass Yield | **Live** | `get_quality_defect_aggregation` → `t_qm_inspect_info` | FPY = `100% − defect_rate` from inspected qty and error qty. |
| 1 | 异常批次 | Abnormal Lots | **Live** | SQL `_fetch_problem_summary` → `t_qm_problem_report` | Count of 8D problem reports created in the lookback window. |
| 2 | 闭环率 | Closure Rate | **Live** | Same SQL | `close_time IS NOT NULL` / total 8D reports — measures closure progress. |

### Charts / 图表

| Index | 中文 | English | Type | Status | Tables / tools | Why this source |
|-------|------|---------|------|--------|----------------|-----------------|
| 0 | 不良率趋势 | Defect Rate Trend | line | **Live** | SQL `_fetch_daily_defect_rates` → `t_qm_inspect_info` | Daily `(error_qty / real_qty) × 100` — direct defect trend. |
| 1 | 缺陷类型排行 | Defect Type Ranking | bar | **Live** | `analyze_defect_root_cause` → `t_qm_problem_report`, `t_qm_problem_reason` | Top reasons from root-cause hypotheses (may show 8D text, not fixed 外观/尺寸 categories). |
| 2 | 质量健康度 | Quality Health | gauge | **Live** | `get_quality_defect_aggregation` → `t_qm_inspect_info` | `100 − defect_rate` as health score. |
| 3 | 返修率趋势 | Rework Rate Trend | line | **Live*** | Same daily defect SQL (proxy) | Uses daily defect rate as rework proxy when no dedicated rework column exists. |
| 4 | 工序良率对比 | Process Yield | bar | **Live** | Defect tool `breakdown` by `process_code` → `t_qm_inspect_info` | Per-process yield = `100 − process defect_rate`. |
| 5 | 检验及时率 | Inspection On-time | gauge | **Fallback** | — | No on-time inspection MCP tool or schedule table wired. |

\*Chart 3 falls back to mock if the daily series is empty.

### Chat integration / 对话集成

| Item | Detail |
|------|--------|
| Domain prefix | `【AI质量助手】` |
| `assistant_module` | `quality` |
| Static greeting (UI) | 你好，我是AI质量助手，可以帮你分析质量异常、缺陷分布和改善建议。 / Hi, I can help with quality issues, defect distribution and improvement plans. |
| Persona | Quality engineer — FPY, defect types, 8D, root cause, corrective actions |
| Sample prompts | 本周质量异常有哪些？ / Quality issues this week? · 分析不良原因排行 / Top defect causes · 生成质量改善建议 / Improvement recommendations |
| NL routing | Quality intents: defect aggregation, root cause, error prevention, effectiveness verification |

---

## 4. Equipment / AI设备助手 (Device Assistant)

| Item | Value |
|------|-------|
| Route | `/assistant/equipment` |
| Module key | `equipment` |
| Backend builder | [`core/dashboard/equipment.py`](../core/dashboard/equipment.py) |
| Frontend composable | [`useEquipmentAssistantPage.js`](../frontend/src/composables/useEquipmentAssistantPage.js) |
| Dashboard API | `GET /api/v1/assistants/equipment/dashboard?line_id=…` |
| Scope param | `line_id` (optional) |

Equipment reuses **production MCP tools** scoped to `yield_type=equipment`, plus **device registry SQL**.

### KPIs / 指标卡

| Index | 中文 | English | Source | Tables / tools | Why this source |
|-------|------|---------|--------|----------------|-----------------|
| 0 | 设备健康度 | Equipment Health | **Live** | `get_yield_aggregation` (equipment achievement) → `t_smt_program_consumption_record`, `t_co_device` | Achievement rate treated as health score; trend from `compare_yield_periods`. |
| 1 | 预测告警 | Predicted Alerts | **Live** | `get_yield_anomalies` (below_standard) → `t_smt_program_consumption_record`, `t_co_device` | Count of below-standard hourly buckets as predictive alert proxy. |
| 2 | 平均停机 | Avg. Downtime | **Fallback** | — | No downtime duration table or PM work-order duration in MES schema. |

### Charts / 图表

| Index | 中文 | English | Type | Status | Tables / tools | Why this source |
|-------|------|---------|------|--------|----------------|-----------------|
| 0 | 设备健康趋势 | Equipment Health Trend | line | **Live** | Daily equipment achievement → `t_smt_program_consumption_record`, `t_co_device` | Daily achievement % tracks health over time. |
| 1 | 告警等级分布 | Alert Level Distribution | bar | **Fallback** | — | No alert severity taxonomy in DB. |
| 2 | 维护完成率 | Maintenance Completion | gauge | **Live** | SQL `_fetch_device_registry_summary` → `t_co_device` | Devices with valid `expire_date` (certification/maintenance) / total registered on line. |
| 3 | 停机时长分析 | Downtime by Equipment | bar | **Live** | `get_device_production_rate` → `t_smt_program_consumption_record`, `t_co_device` | Inverse of avg rate vs max rate as downtime **proxy**; x-axis shows device names (not CNC/注塑 UI labels). |
| 4 | MTBF趋势 | MTBF Trend | line | **Fallback** | — | No MTBF time-series source. |
| 5 | 点检完成率 | Inspection Completion | gauge | **Live** | SQL `_fetch_active_device_ratio` → `t_co_device`, `t_smt_program_consumption_record` | Devices with consumption logs in window / registered devices = “active/inspected” proxy. |

### Chat integration / 对话集成

| Item | Detail |
|------|--------|
| Domain prefix | `【AI设备助手】` |
| `assistant_module` | `equipment` |
| Static greeting (UI) | 你好，我是AI设备助手，可以帮你分析设备状态、故障风险和维护计划。 / Hi, I can help with equipment status, failure risk and maintenance plans. |
| Persona | Maintenance engineer — health, downtime risk, PM, alerts, device_sn |
| Sample prompts | 哪些设备存在停机风险？ / Equipment at downtime risk? · 生成本周保养计划 / Weekly maintenance plan · 分析设备异常原因 / Analyze equipment anomalies |
| NL routing | Production intents with `yield_type=equipment` and `device_sn` / `line_id`; device rate queries |

---

## 5. Procurement / AI采购助手 (Purchase Assistant)

| Item | Value |
|------|-------|
| Route | `/assistant/procurement` |
| Module key | `procurement` |
| Backend builder | [`core/dashboard/procurement.py`](../core/dashboard/procurement.py) |
| Frontend composable | [`useProcurementAssistantPage.js`](../frontend/src/composables/useProcurementAssistantPage.js) |
| Dashboard API | `GET /api/v1/assistants/procurement/dashboard?wh_code=…` |
| Scope param | `wh_code` (optional) |

Procurement has **no dedicated MCP module**; the builder uses **WMS receive/supplier SQL** plus `get_inventory_status` for insight context.

### KPIs / 指标卡

| Index | 中文 | English | Source | Tables / tools | Why this source |
|-------|------|---------|--------|----------------|-----------------|
| 0 | 采购节省率 | Savings Rate | **Live** | SQL `_fetch_spend_comparison` → `t_wms_receive_item`, `t_wms_receive_doc`, `t_co_item` | `(prev_spend − curr_spend) / prev_spend`; spend = `receive_qty × single_price`. Falls back if prior period spend is zero. |
| 1 | 准交率 | On-time Delivery | **Live** | SQL `_fetch_receive_summary` → `t_wms_receive_doc` | `receive_date ≤ plan_receive_date` / total receipts with both dates. |
| 2 | 风险供应商 | Risk Suppliers | **Live** | Same receive summary | Suppliers with ≥2 receipts and OTD &lt; 85% in window. |

### Charts / 图表

| Index | 中文 | English | Type | Status | Tables / tools | Why this source |
|-------|------|---------|------|--------|----------------|-----------------|
| 0 | 采购金额趋势 | Procurement Spend Trend | line | **Live** | SQL `_fetch_daily_spend` → `t_wms_receive_item`, `t_wms_receive_doc`, `t_co_item` | Daily sum of `receive_qty × single_price` (scaled to 万 in series). |
| 1 | 供应商评分 | Supplier Scores | bar | **Live** | Receive summary + `t_co_supplier` | Top 5 suppliers by volume; bar = OTD %. Labels use real supplier names from `t_co_supplier`. |
| 2 | 供应链稳定性 | Supply Chain Stability | gauge | **Live** | `_fetch_stability_score` → `t_wms_receive_doc` | `100 − late_delivery_rate` across receipts. |
| 3 | 交付周期对比 | Lead Time Comparison | bar | **Live** | `_fetch_lead_time_by_abc` → `t_wms_receive_doc`, `t_wms_receive_item`, `t_co_item` | Avg days `(receive_date − plan_receive_date)` by `abc_type` (A类–E类 / Cat A–E). |
| 4 | 议价空间趋势 | Negotiation Margin | line | **Fallback** | — | No price-history table; only snapshot `single_price` on `t_co_item`. |
| 5 | 物料齐套率 | Material Kit Rate | gauge | **Live** | SQL `_fetch_kit_rate` → `t_wms_stock_info`, `t_co_item` | Items with `stock_qty ≥ min_stock` / items with `min_stock > 0`. |

### Chat integration / 对话集成

| Item | Detail |
|------|--------|
| Domain prefix | `【AI采购助手】` |
| `assistant_module` | `procurement` |
| Static greeting (UI) | 你好，我是AI采购助手，可以帮你分析采购成本、供应风险和供应商表现。 / Hi, I can help with procurement cost, supply risk and supplier performance. |
| Persona | Procurement analyst — savings, OTD, supplier scores, replenishment, risk suppliers |
| Sample prompts | 本月采购成本趋势？ / Procurement cost trend this month? · 哪些供应商存在风险？ / Suppliers at risk? · 生成补货采购建议 / Replenishment suggestions |
| NL routing | No dedicated procurement intents yet; general queries may route to warehouse inventory or UNKNOWN greeting. Dashboard SQL covers receive/supplier analytics. |

---

## Database table reference / 数据库表索引

| Table | Used by modules | Role |
|-------|-----------------|------|
| `t_smt_program_consumption_record` | Production, Equipment | Machine logs: `finish_qty`, `mount_sheet_qty`, `device_sn`, `create_time` |
| `t_co_device` | Production, Equipment | Device registry: `device_sn`, `device_name`, `cd_location`, `expire_date` |
| `t_co_standard_time` | Production | Standard time targets for capacity forecast |
| `t_co_area` | Production (reported yield) | Line/area hierarchy |
| `t_wip_detail` | Production (reported yield), Warehouse trace | WIP quantities |
| `t_wms_stock_info` | Warehouse, Procurement | On-hand inventory, `instock_time`, `wh_code` |
| `t_co_item` | Warehouse, Procurement | `min_stock`, `single_price`, `abc_type` |
| `t_wms_area` | Warehouse | Bin/area master for utilization |
| `t_qm_inspect_info` | Quality | Inspection qty, defects, `process_code`, `test_start_time` |
| `t_qm_problem_report` | Quality, Procurement (indirect) | 8D reports, closure times |
| `t_qm_problem_reason` | Quality | Root-cause reason text for defect ranking |
| `t_co_supplier` | Procurement | Supplier names for score chart labels |
| `t_wms_receive_doc` | Procurement | Inbound header: `plan_receive_date`, `receive_date`, `supplier_code` |
| `t_wms_receive_item` | Procurement | Inbound lines: `receive_qty`, `item_code` |

---

## Frontend file map / 前端文件对照

| Module | Composable | Charts adapter | Chat |
|--------|------------|----------------|------|
| production | `useProductionAssistantPage.js` | `views/assistants/production/charts.js` | prefix + `assistant_module=production` |
| warehouse | `useWarehouseAssistantPage.js` | `views/assistants/warehouse/charts.js` | prefix + `assistant_module=warehouse` |
| quality | `useQualityAssistantPage.js` | `views/assistants/quality/charts.js` | prefix + `assistant_module=quality` |
| equipment | `useEquipmentAssistantPage.js` | `views/assistants/equipment/charts.js` | prefix + `assistant_module=equipment` |
| procurement | `useProcurementAssistantPage.js` | `views/assistants/procurement/charts.js` | prefix + `assistant_module=procurement` |

Shared: [`useIntegratedAssistantPage.js`](../frontend/src/composables/useIntegratedAssistantPage.js), [`adapters/chartSlots.js`](../frontend/src/adapters/chartSlots.js), [`adapters/dashboard.js`](../frontend/src/adapters/dashboard.js), [`api/dashboard.js`](../frontend/src/api/dashboard.js), [`api/query.js`](../frontend/src/api/query.js).

---

## Backend file map / 后端文件对照

| Module | Dashboard builder | Route registration |
|--------|-------------------|-------------------|
| production | `core/dashboard/production.py` | `DASHBOARD_BUILDERS["production"]` in `api/routes.py` |
| warehouse | `core/dashboard/warehouse.py` | `DASHBOARD_BUILDERS["warehouse"]` |
| quality | `core/dashboard/quality.py` | `DASHBOARD_BUILDERS["quality"]` |
| equipment | `core/dashboard/equipment.py` | `DASHBOARD_BUILDERS["equipment"]` |
| procurement | `core/dashboard/procurement.py` | `DASHBOARD_BUILDERS["procurement"]` |

Chat personas: [`orchestrator/module_personas.py`](../orchestrator/module_personas.py) (aligned with `messages.js` greetings).  
Synthesis prompts: [`orchestrator/prompts/synthesis.py`](../orchestrator/prompts/synthesis.py).

---

## Related docs / 相关文档

- [frontend.md](./frontend.md) — SPA architecture and env vars  
- [mesai-mcp-1.1.md](./mesai-mcp-1.1.md) — MCP tool catalog and SQL patterns  
- [mesai-query-1.1.md](./mesai-query-1.1.md) — Sample line/device IDs and data windows
