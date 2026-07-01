# Dashboard Database Access — How It Works Today & Proposed Caching

This document explains, in plain language, how the MES AI assistant dashboards load data from PostgreSQL, why opening a module on the live server can feel slow or cause the browser to hang, and how we could split **historical (cached on server)** from **live (daily) remote queries**.

Related docs: [integration.md](./integration.md), [mesai-vpd.md](./mesai-vpd.md), [mesai-query-1.1.md](./mesai-query-1.1.md).

---

## 1. What happens when you open an assistant page

```
Browser (Vue)
  → GET /api/v1/assistants/{module}/dashboard
  → FastAPI route (api/routes.py)
  → core/dashboard/{module}.py  (one builder per module)
  → Many parallel DB calls (asyncio.gather)
       • MCP tools (mcp_tools/*.py) — predefined SQL
       • Direct SQL in dashboard builders
  → Remote PostgreSQL (MES read-only DB)
  → Small JSON response (3 KPIs + 6 chart slots + insight text)
  → Frontend merges live slots into ECharts
```

**Important:** The browser does **not** receive raw MES rows. Each chart gets a short list of labels (`x_data`) and numbers (`series`), or one gauge value. A typical response is a few kilobytes.

If the page “crashes” or freezes, it is usually because:

1. **The API call takes too long** — the browser waits with no timeout (`frontend/src/api/client.js` has no request timeout).
2. **The backend opens many DB connections at once** — each sub-query uses its own session; the pool is small (5 connections + 10 overflow).
3. **The remote database is slow or far away** — default `DATABASE_URL` points at a tunneled/hosted PostgreSQL, not a local copy.
4. **Some queries scan large tables** — especially `t_smt_program_consumption_record` (~453K rows) and full inventory pulls.

So the problem is **work on the server and remote DB**, not “too much JSON for the browser.”

---

## 2. Database connection setup

| Setting | Default / location | Meaning |
|---------|-------------------|---------|
| `DATABASE_URL` | `.env` → `core/config.py` | Async PostgreSQL via SQLAlchemy + `asyncpg` |
| Pool size | `db_pool_size = 5` | Max 5 idle connections; up to 10 extra under load |
| Sessions | `core/db.py` → `get_session()` | Each tool/query opens and closes its own session |
| SQL style | `sqlalchemy.text()` only | No LLM-generated SQL; fixed queries with bind params |
| Reference date | `DASHBOARD_REFERENCE_DATE` (default `2026-06-21`) | Dashboard windows never look past this “latest snapshot” date |

There is **no Redis, no response cache, and no local MES replica** in the current codebase. Every dashboard page load hits the remote DB fresh.

---

## 3. Time windows — how far back each request looks

| Mechanism | Window | Used by |
|-----------|--------|---------|
| `lookback_days` (API query param) | Default **7**, max **90** | Most KPI/chart queries |
| `resolve_date_range()` | `[reference_date − lookback_days + 1 … reference_date]` | Production, quality, equipment, procurement |
| Defect analysis chart | **6 months** (fixed) | Production slot 4 — `t_wip_detail` monthly buckets |
| Capacity forecast | **30 days** (fixed inside analytics) | Production slot 2 — `forecast_capacity_hr` |

The frontend calls the API with `lookback_days=7` by default (`frontend/src/api/dashboard.js`).

---

## 4. Per-module workload (one page load)

Each row is a **separate** parallel task. Each task typically opens **one** DB session, runs SQL, closes the session.

### Production (`core/dashboard/production.py`)

| # | What runs | Main table(s) | Aggregation |
|---|-----------|---------------|-------------|
| 1 | Plan attainment (total) | `t_smt_program_consumption_record`, `t_co_device` | SQL `SUM` + Python rate |
| 2 | Line attainment trend (daily) | Same | SQL `GROUP BY day` |
| 3 | Period comparison (trend arrow) | Same | Two period totals |
| 4 | Device production rate | Same | SQL `GROUP BY device` |
| 5 | Capacity load gauge | Same + `t_co_standard_time` | 30-day scan + Python forecast |
| 6 | Downtime / anomalies chart | Same | SQL **hourly** buckets, then Python filter |
| 7 | Defect analysis (monthly) | `t_wip_detail`, `t_co_area` | SQL `GROUP BY month` |

**~7 parallel DB sessions** per production dashboard request.

### Equipment (`core/dashboard/equipment.py`)

Same production MCP tools as above (6 calls) plus 2 small SQL helpers on `t_co_device` and consumption logs.

**~8 parallel DB sessions.**

### Warehouse (`core/dashboard/warehouse.py`)

| # | What runs | Risk |
|---|-----------|------|
| 1 | Inventory status MCP | Loads **all** stock rows (`item_qty > 0`) into Python |
| 2 | Obsolete inventory MCP | Additional WMS query |
| 3 | Stock summary (KPIs + structure chart) | **Again** loads all stock rows, loops in Python |
| 4 | Age buckets (slow-moving chart) | Loads **every** `instock_time` for in-stock items |
| 5 | Bin utilization | Two `COUNT` queries (light) |

**~5 parallel sessions**, but queries **3 and 4 can transfer many rows** from the remote DB even though the API only returns a handful of chart numbers.

### Quality (`core/dashboard/quality.py`)

| # | What runs | Notes |
|---|-----------|-------|
| 1 | Defect aggregation MCP | `t_qm_inspect_info` — aggregated in SQL |
| 2 | Root cause MCP | `t_qm_problem_report`, `t_qm_problem_reason` |
| 3 | Daily defect rates SQL | `GROUP BY day` — efficient |
| 4 | Problem summary SQL | Count of 8D reports |

**~4 parallel sessions** — generally lighter than production/warehouse.

### Procurement (`core/dashboard/procurement.py`)

| # | What runs | Notes |
|---|-----------|-------|
| 1 | Receive summary | All receive docs in window → Python OTD math |
| 2 | Spend comparison | Two period totals |
| 3 | Daily spend trend | SQL `GROUP BY day` |
| 4 | Supplier scores | Receive docs + supplier name lookup |
| 5 | Stability score | Receive docs again (duplicate scan) |
| 6 | Lead time by ABC | SQL `GROUP BY abc_type` |
| 7 | Kit rate | All items with `min_stock > 0` |
| 8 | Inventory status MCP | Full stock pull (same as warehouse) |

**~8 parallel sessions**, with some **duplicate reads** of receive documents inside the same request.

---

## 5. Where the heavy work actually is

### Large MES tables (from test-data audit)

| Table | Approx. size | Used for |
|-------|--------------|----------|
| `t_smt_program_consumption_record` | ~453K rows | Production & equipment charts (achievement, device rate, anomalies, capacity) |
| `t_wip_detail` | ~8.2K rows | Reported yield, monthly defect chart |
| `t_wms_stock_info` | Many rows | Warehouse & procurement — often **full table read** |
| `t_qm_inspect_info` | Moderate | Quality dashboards |

### Patterns that cost the most

1. **Same big table queried many times in one request**  
   Production/equipment call `t_smt_program_consumption_record` up to **6 times** with different `GROUP BY` (total, daily, hourly, per device, 30-day capacity).

2. **Hourly aggregation for anomalies**  
   `get_yield_anomalies` builds an hourly series over the lookback window — more buckets and more rows touched than daily charts.

3. **Full inventory loads in Python**  
   Warehouse builder and `get_inventory_status` pull all matching stock rows, then count low-stock / expiring / age buckets in application code instead of one SQL `GROUP BY`.

4. **Connection pool contention**  
   With pool size 5 and 7–8 parallel tasks, tasks queue for connections. Over a slow network tunnel this multiplies wait time.

5. **No caching between users or refreshes**  
   Two users opening Production at the same time both run the full query set.

### What the API returns (small)

Example shape (`models/dashboard.py`):

```json
{
  "module": "production",
  "kpis": [ { "index": 0, "value": "96.8%", "source": "live" }, ... ],
  "charts": [ { "index": 0, "chart_type": "line", "x_data": ["6月15日", ...], "series": [91.2, ...], "source": "live" }, ... ],
  "partial": false,
  "generated_at": "..."
}
```

Six charts × ~7 daily points = tiny payload. **ECharts** renders this quickly once the HTTP call completes.

---

## 6. How data fetching is handled (summary)

| Layer | Behavior |
|-------|----------|
| **SQL** | Fixed, parameterized queries; warehouse stock/age buckets now aggregate in SQL |
| **Python** | Second-pass math (rates, trends, bucket labels) on query results |
| **Parallelism** | `asyncio.gather` — all module queries start together |
| **Sessions** | One session per tool/query; opened and closed independently |
| **Errors** | MCP tools return `{ success: false }`; dashboard slots fall back to mock data |
| **Cache** | SQLite snapshots in `data/dashboard_cache.db` (see §7) |
| **Frontend** | Page shell + chat render immediately; KPI/charts show skeleton until dashboard GET completes |

---

## 7. Implemented — SQLite dashboard cache (Phase 1)

**Status:** Implemented in `core/dashboard_cache/`.

### 7.1 What was built

Full `AssistantDashboardResponse` JSON is cached per `(module, scope_key, locale, lookback_days)` in SQLite — same pattern as chat history (`core/chat_store.py`).

| File | Role |
|------|------|
| [`core/dashboard_cache/store.py`](../core/dashboard_cache/store.py) | SQLite CRUD |
| [`core/dashboard_cache/service.py`](../core/dashboard_cache/service.py) | Fresh/stale checks, build + store |
| [`core/dashboard_cache/scheduler.py`](../core/dashboard_cache/scheduler.py) | Hourly prewarm loop in FastAPI lifespan |
| [`scripts/refresh_dashboard_cache.py`](../scripts/refresh_dashboard_cache.py) | CLI / cron prewarm |
| [`api/routes.py`](../api/routes.py) | Cache hit / stale-while-revalidate / miss |

### 7.2 API read path

1. `GET /api/v1/assistants/{module}/dashboard` checks SQLite.
2. **Fresh** (within TTL) → return cached JSON immediately (`X-Dashboard-Cache: hit`).
3. **Stale** → return cached JSON + background revalidation (`X-Dashboard-Cache: stale`).
4. **Miss** → run dashboard builder against remote MES DB, store snapshot, return (`X-Dashboard-Cache: miss`).

### 7.3 Environment variables

| Variable | Default | Role |
|----------|---------|------|
| `DASHBOARD_CACHE_ENABLED` | `true` | Toggle cache |
| `DASHBOARD_CACHE_DB_PATH` | `./data/dashboard_cache.db` | SQLite file |
| `DASHBOARD_CACHE_TTL_SECONDS` | `900` | Fresh window (15 min) |
| `DASHBOARD_CACHE_STALE_OK` | `true` | Serve stale while refreshing |
| `DASHBOARD_CACHE_REFRESH_INTERVAL_SECONDS` | `3600` | Background prewarm interval |

### 7.4 Manual refresh (deploy / cron)

```bash
python scripts/refresh_dashboard_cache.py
python scripts/refresh_dashboard_cache.py --module production --locale zh-CN
```

Prewarms default scopes: `DEFAULT_LINE_ID` for production/quality/equipment; `DEFAULT_WH_CODE` (or `__all__`) for warehouse/procurement.

### 7.5 Query optimizations (same release)

- **Warehouse:** `_fetch_stock_summary` and `_fetch_age_buckets` use SQL `SUM`/`CASE` instead of downloading all stock rows.
- **Procurement:** receive documents fetched once per request and reused for OTD, supplier scores, and stability.

### 7.6 Frontend loading UX

Assistant pages use [`AssistantDashboardLayout.vue`](../frontend/src/components/AssistantDashboardLayout.vue):

- Header + **chat panel** render immediately on navigation.
- Left report panel shows **skeletons** while dashboard API loads (no ECharts init until data arrives).
- Dashboard fetch has a **60s timeout**; errors show a retry button; chat remains usable throughout.

### 7.7 Not yet implemented (Phase 2+)

- Granular `dashboard_metrics` table with historical/live tail merge inside builders.
- Redis response cache.
- Shared DB session per dashboard request.

---

## 8. Original proposal (reference)

Goal: **instant dashboards** for history, **fresh data** only for recent periods, **less load** on the remote MES DB.

### 8.1 Concept

```
                    ┌─────────────────────────────┐
                    │   Remote MES PostgreSQL      │
                    │   (read-only, slow link)     │
                    └──────────────┬──────────────┘
                                   │
              ETL / refresh job    │  Live tail only
              (nightly + hourly)   │  (today / last 1–2 days)
                                   ▼
                    ┌─────────────────────────────┐
                    │   Local store on app server  │
                    │   SQLite or local PostgreSQL │
                    │   + optional Redis hot cache │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │   Dashboard API              │
                    │   merge cache + live         │
                    └──────────────┬──────────────┘
                                   ▼
                              Browser (fast)
```

### 8.2 Local store — what to save (Phase 2)

Store **pre-aggregated facts**, not raw MES rows. One row per metric bucket, for example:

| Table (local) | Grain | Example metrics |
|---------------|-------|-----------------|
| `dash_prod_daily` | line_id + date | achievement_rate, defect_qty, anomaly_count |
| `dash_prod_monthly` | line_id + month | defect_qty (不良品) |
| `dash_equip_daily` | line_id + date | health_rate, maintenance_pct |
| `dash_wh_daily` | wh_code + date | healthy / low / expiring counts, bin_util |
| `dash_qm_daily` | line_id + date | defect_rate, fpy |
| `dash_proc_daily` | wh_code + date | spend, otd_rate, kit_rate |

Each record: `{ module, scope_key, bucket_date, metric_key, value, updated_at }`.

**Rule of thumb:** If a chart only needs 6–30 points, the local table should already hold those points — the API should not re-scan 453K consumption rows to build them.

### 8.3 What stays live (remote DB)

| Data type | Suggested source | Refresh |
|-----------|------------------|---------|
| **Today / yesterday** | Remote DB direct | Every 5–15 minutes or on demand |
| **Current shift KPIs** | Remote DB | Short TTL cache (e.g. 5 min) |
| **Inventory snapshot** | Remote DB or hourly ETL | Warehouse/procurement “as of” hour |
| **Chat / NL queries** | Remote DB (unchanged) | Real-time — not dashboard cache |

Historical months and closed days never need to hit the remote DB on every page view.

### 8.4 ETL / refresh jobs (Phase 2 granular metrics)

**Job A — Nightly (e.g. 02:00)**  
For each module, line, and warehouse scope:

1. Connect to remote MES DB (batch-friendly, off-peak).
2. Run the **same aggregation SQL** already used in `core/dashboard/*.py`, but for **completed dates only** (date &lt; today).
3. Upsert into local `dash_*` tables.
4. Mark `last_closed_date` per scope.

**Job B — Hourly (optional)**  
Refresh **yesterday + today** buckets only.

**Job C — On-demand backfill (one-time)**  
When deploying, backfill 6–12 months of daily/monthly aggregates into local store so charts are instant from day one.

Implementation options (no code change required now — pick at deploy time):

- **Cron + Python script** in the repo (`scripts/refresh_dashboard_cache.py`)
- **APScheduler** inside FastAPI lifespan
- **Systemd timer** on the server

### 8.5 API read path (Phase 2 — live tail merge)

When `GET /assistants/{module}/dashboard` runs:

1. Load **cached buckets** from local store for `[start … yesterday]`.
2. Fetch **live tail** from remote DB for `[today]` (or last 1–2 days if ETL lag).
3. Merge series in Python → build `DashboardChartSlot` list (same JSON shape as today).
4. Optionally store full response in **Redis** keyed by `(module, line_id, wh_code, locale, date)` with TTL 5–15 minutes.

Frontend stays unchanged — same endpoint, same response model.

### 8.6 Quick wins

These are low-effort improvements aligned with the same goal:

| Change | Effect |
|--------|--------|
| **Single shared session per dashboard request** | Reuse one connection for all queries in a module |
| **Push aggregations into SQL** | Warehouse age buckets & stock summary via `GROUP BY` — **done** |
| **Deduplicate queries** | Procurement receive docs — **done** |
| **HTTP timeout + loading UI** | Frontend skeleton + 60s timeout — **done** |
| **Reduce parallel duplicate scans** | One daily aggregation query for production instead of separate total + daily + hourly reads where possible |
| **Increase pool size** (carefully) | Only if remote DB allows more connections |

### 8.7 Rollout phases

| Phase | Scope | Outcome |
|-------|-------|---------|
| **1** | Local SQLite full-response cache + stale-while-revalidate | **Done** — all modules |
| **2** | Warehouse/procurement inventory aggregates (SQL `GROUP BY`, local daily snapshot) | Warehouse stops full table pulls |
| **3** | Quality + equipment daily tables | All five modules cached |
| **4** | Redis response cache + hourly today refresh | Safe under concurrent users |

---

## 9. Environment variables

**Remote MES**

| Variable | Role |
|----------|------|
| `DATABASE_URL` | Remote MES PostgreSQL |
| `DASHBOARD_REFERENCE_DATE` | Upper bound for lookback |
| `DB_POOL_SIZE` | Connection pool (default 5) |

**Dashboard cache (implemented)**

| Variable | Role |
|----------|------|
| `DASHBOARD_CACHE_ENABLED` | Toggle SQLite cache |
| `DASHBOARD_CACHE_DB_PATH` | SQLite file path |
| `DASHBOARD_CACHE_TTL_SECONDS` | Fresh window |
| `DASHBOARD_CACHE_STALE_OK` | Serve stale while revalidating |
| `DASHBOARD_CACHE_REFRESH_INTERVAL_SECONDS` | Background prewarm interval |

---

## 10. Takeaway

| Question | Answer |
|----------|--------|
| Is the browser downloading huge chart datasets? | **No** — responses are small aggregated arrays. |
| Is the backend doing a lot of DB work on cache miss? | **Yes** — 4–8 parallel queries per page. |
| Is anything cached? | **Yes** — SQLite snapshots with TTL + stale-while-revalidate. |
| Why did live server feel broken? | Slow remote DB + no loading UX + ECharts on mock data during wait. |
| Current fix? | **SQLite response cache** + **instant page with chat-first UX** + SQL/query optimizations. |

For chart-to-table mapping after integration changes, see [mesai-vpd.md](./mesai-vpd.md). For module wiring details, see [integration.md](./integration.md).
