# NEUTRON MES AI Assistant — Backend

Enterprise Manufacturing Execution System (MES) AI Assistant backend for the **NEUTRON** team. The system accepts natural-language queries, extracts structured intent via **Alibaba Cloud Bailian (DashScope)**, and dispatches typed parameters to predefined **Model Context Protocol (MCP) tools** that query the MES PostgreSQL database.

**Stack:** Python 3.10+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), asyncpg, dashscope (Bailian SDK).

**Current version:** `0.3.0` — RAG pipeline, 18 MCP tools (Production/Quality/Warehouse), voice/export/cross-module utilities, global DB access (no workshop row-level filtering).

**Debugging reference:** [docs/mesai-mcp-1.1.md](docs/mesai-mcp-1.1.md) (tool SQL, schemas, known mismatches) · [docs/mesai-query-1.1.md](docs/mesai-query-1.1.md) (real test IDs and date ranges)

---

## Architectural Constraints (Audit Checklist)

| Constraint | Status | Implementation |
|---|---|---|
| **No Text-to-SQL** | Enforced | LLM extracts parameters only. MCP tools run predefined `sqlalchemy.text()` queries. |
| **Intent routing (Feature 1.2)** | Done | `parse_intent()` → Bailian `dashscope.Application.call` → `IntentSchema` |
| **API-first testing** | Done | Swagger UI at `/docs` (root `/` redirects here), ReDoc at `/redoc` |
| **Param validation** | Done | `orchestrator/param_validation.py` blocks dispatch when required entities are missing (no dummy `L-01` fallbacks) |
| **Math safeguard (Feature 5.2)** | Done | `core/math_safeguard.py` — std dev and growth rates computed in Python |
| **Global data access** | Done | No `data_auth` / workshop filtering in MCP SQL; queries match on line, device, dates, product codes only |

---

## High-Level Request Flow

```mermaid
sequenceDiagram
    participant User as Swagger_UI
    participant API as POST_/api/v1/query
    participant MW as RequestContextMiddleware
    participant Bailian as dashscope.Application
    participant Router as route_and_execute
    participant Validate as param_validation
    participant MCP as MCP_tools
    participant DB as PostgreSQL

    User->>API: query JSON body
    API->>MW: empty MCPContext
    MW->>Router: route_and_execute
    Router->>Bailian: asyncio.to_thread Application.call
    Bailian-->>Router: JSON intent params
    Router->>Validate: required entities
    alt missing line_id etc
        Validate-->>User: message only (no DB call)
    else ok
        Validate->>MCP: tool.run params
        MCP->>DB: parameterized SQL (no data_auth filter)
        DB-->>MCP: raw rows
        MCP-->>User: OrchestratorResponse
    end
```

1. User sends `POST /api/v1/query` with a natural-language `query` (no auth headers required).
2. `RBACMiddleware` injects an empty `MCPContext` placeholder (headers are ignored for data scoping).
3. `parse_intent(query, context)` calls Bailian asynchronously and returns `IntentSchema`.
4. `validate_intent_params()` returns a user-facing message if required fields (e.g. `line_id`, `device_sn`) are missing.
5. `route_and_execute()` maps intent → Pydantic params via `param_mappers.py` and runs the matching MCP tool.
6. MCP tool queries PostgreSQL globally, computes statistics in Python, returns JSON.

**Intent routing map (v0.3 — 18 tools):**

| Module | `IntentType` examples | MCP Tool |
|---|---|---|
| Production | `yield_aggregation`, `production_root_cause`, `production_product_yield` | `get_yield_aggregation`, `get_production_root_cause`, … |
| Quality | `quality_defect_analysis`, `quality_error_prevention` | `get_quality_defect_aggregation`, `check_error_prevention`, … |
| Warehouse | `warehouse_inventory_monitor`, `warehouse_trace_forward` | `get_inventory_status`, `trace_material_forward`, … |
| System | `cross_module_analysis`, `export_report` | `cross_module_analysis`, `POST /export` |

RAG context is attached to `metadata.rag_context` for anomaly/root-cause intents when `enrich_response=true` (global vector search, not workshop-scoped).

---

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — see Environment Variables below
uvicorn main:app --reload
```

Open **http://127.0.0.1:8000/** (redirects to Swagger) or **http://127.0.0.1:8000/docs**.

### Environment Variables (`.env`)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Async PostgreSQL DSN: `postgresql+asyncpg://user:pass@host:5432/mes_db` |
| `DASHSCOPE_API_KEY` | Yes* | Alibaba DashScope API key for Bailian intent extraction |
| `BAILIAN_APP_ID` | Yes* | Bailian Application ID from Model Studio |
| `DB_POOL_SIZE` | No | Connection pool size (default: `5`) |
| `DEBUG` | No | Enable SQL echo, Bailian raw response logging, and tool result debug logs |
| `RAG_BACKEND` | No | `pgvector` \| `chroma` \| file fallback (default: `chroma` → file) |
| `RAG_EMBEDDING_MODEL` | No | DashScope embedding model (default: `text-embedding-v2`) |
| `CHROMA_PERSIST_DIR` | No | Local vector store path (default: `./data/chroma`) |
| `VOICE_MOCK` | No | Return mock transcript when `true` (default: `true`) |

\*Without Bailian credentials the app still starts; queries return `intent: unknown` with a logged warning.

**Common startup error:** If `DATABASE_URL` still contains the placeholder `host:port` (copied literally from an old template), SQLAlchemy will fail with `invalid literal for int() with base 10: 'port'`. Replace with a real hostname and numeric port (e.g. `5432`).

---

## Directory Structure

```
mesai/
├── main.py
├── api/routes.py               # query, voice, rag/ingest, export
├── core/
│   ├── rag/                    # store, ingest, retriever
│   ├── analytics/              # root_cause, scheduling, capacity
│   ├── export/                 # excel, pdf
│   ├── voice/                  # transcribe
│   └── security.py             # request context middleware (no RBAC enforcement)
├── models/intents/             # production, quality, warehouse, system
├── mcp_tools/
│   ├── production_tools.py     # 6 production tools
│   ├── production_engines.py   # root cause, scheduling, capacity
│   ├── quality_tools.py        # 4 quality tools
│   └── warehouse_tools.py      # 5 warehouse tools
├── orchestrator/
│   ├── router.py               # slim dispatcher
│   ├── tool_registry.py        # intent → tool map (18 tools)
│   ├── param_mappers.py        # IntentSchema → tool params
│   ├── param_validation.py     # required-entity checks before DB
│   ├── intent_prompt.py
│   ├── intent_utils.py         # parse_intent, Bailian call
│   └── cross_module.py
└── db/migrations/001_rag_pgvector.sql
```

---

## File-by-File Reference

### `main.py` — Application Entry Point

| Symbol | Purpose |
|---|---|
| `lifespan()` | `setup_logging()` → `init_db()` on startup; `close_db()` on shutdown |
| `create_app()` | FastAPI app + request context middleware + API router + `/` → `/docs` redirect |
| `app` | ASGI instance for uvicorn |

---

### `api/routes.py` — HTTP Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/health` | GET | Liveness + version |
| `/api/v1/query` | POST | NL query → Bailian → validate → MCP tool |
| `/api/v1/query/voice` | POST | Audio upload → transcribe → query |
| `/api/v1/rag/ingest` | POST | Ingest SOP/anomaly/solution into RAG (global index) |
| `/api/v1/export` | POST | Export result as xlsx or pdf |

No headers are required for data access. `X-MES-Workshop-Id` and related headers are accepted by Swagger for compatibility but **do not filter database queries**.

---

### `core/config.py` — Settings

All settings load from `.env` via Pydantic `BaseSettings`. `get_settings()` is a cached singleton.

Key fields: `database_url`, `dashscope_api_key`, `bailian_app_id`, `db_pool_size`, `debug`, `rag_backend`.

---

### `core/db.py` — Database Bridge (F0.4)

SQLAlchemy 2.0 async connection pool.

| Symbol | Purpose |
|---|---|
| `init_db()` | Create engine, run `SELECT 1`. Logs errors for bad URL or unreachable DB; does not crash the app. |
| `close_db()` | Dispose engine on shutdown |
| `get_db()` | FastAPI dependency — yields `AsyncSession` per request |
| `get_session()` | Standalone session for MCP tool execution |

---

### `core/security.py` — Request Context

`RBACMiddleware` injects an empty `MCPContext()` on every request. Workshop and permission headers are not read for query scoping. `get_mes_context(request)` returns the placeholder context for route handlers.

---

### `core/math_safeguard.py` — Mathematical Safeguard (Feature 5.2)

| Function | Formula | Used by |
|---|---|---|
| `population_std_dev(values)` | σ = √(Σ(x − μ)² / N) | `get_yield_anomalies_and_peaks` (`volatility`) |
| `period_over_period_growth_rate(current, past)` | ((current − past) / past) × 100 | `compare_yield_periods`, quality effectiveness |

---

### `models/schemas.py` — Shared Pydantic Models

| Model / Enum | Purpose |
|---|---|
| `IntentType` | All 18+ intents including production, quality, warehouse, system |
| `BailianIntentExtraction` | Strict Pydantic model for raw Bailian JSON before mapping |
| `IntentSchema` | Bailian output: intent, dates, line_id, device_sn, yield_type, group_by, metric, etc. |
| `MCPContext` | Placeholder context (`workshop_id` optional, unused for DB filtering) |
| `OrchestratorRequest` | `{ "query": "...", "enrich_response": true }` |
| `OrchestratorResponse` | `{ intent, tool_name, result, message, metadata }` |

Tool param/result models live in `mcp_tools/production_tools.py` and `models/intents/`.

---

### `mcp_tools/production_tools.py` — Production MCP Tools

Six tools. All SQL via `sqlalchemy.text()` with bound parameters. **No `data_auth` filters.**

#### Yield table routing

| `yield_type` | Table(s) | Scope filter | Qty | Time column |
|---|---|---|---|---|
| `equipment` | `t_smt_program_consumption_record` | `device_sn = :device_sn` **or** `device_sn IN (SELECT … FROM t_co_device WHERE cd_location = :line_id)` | `finish_qty` / `mount_sheet_qty` | `create_time` |
| `reported` | `t_wip_detail` JOIN `t_co_area` ×2 | `line.area_sn = :line_id` | `pro_qty − ng_qty − scrap_qty` | `COALESCE(in_time, create_time)` |

**Important:** `t_smt_program_consumption_record.area_sn` is often `NULL` in live machine logs — equipment yield must **not** filter on `eq.area_sn`. Use `t_co_device.cd_location` or direct `device_sn`.

**Reported yield join** (workstation → line hierarchy):

```sql
n2admin.t_wip_detail wd
JOIN n2admin.t_co_area ws ON wd.work_stationsn = ws.area_sn
JOIN n2admin.t_co_area line ON ws.parent_sn = line.area_sn
WHERE line.area_sn = :line_id
```

#### Yield validation (`param_validation.py`)

| `yield_type` | Required scope |
|---|---|
| `reported` | `line_id` |
| `equipment` | `line_id` **or** `device_sn` |

#### Tools

| Tool | Singleton | Purpose |
|---|---|---|
| `get_yield_aggregation` | `get_yield_aggregation_tool` | Sum, average, achievement rate (daily/hourly/total) |
| `get_yield_anomalies_and_peaks` | `get_yield_anomalies_tool` | Volatility, below-standard, peak hourly |
| `compare_yield_periods` | `compare_yield_periods_tool` | Period-over-period totals + growth rate |
| `get_product_yield` | `get_product_yield_tool` | Product yield per line + `t_co_item` metadata |
| `get_device_production_rate` | `get_device_production_rate_tool` | Avg rate via `t_co_device` join |
| `get_standard_time_achievement` | `get_standard_time_achievement_tool` | Actual vs `t_co_standard_time` goal |

Achievement rates and growth rates are computed in Python (`_compute_metric`, `math_safeguard`), not by the LLM.

---

### `mcp_tools/production_engines.py` — Analytics Engines

| Tool | Engine | Notes |
|---|---|---|
| `get_production_root_cause` | `core/analytics/root_cause.py` | Uses `wd.operator`; equipment join via `t_co_device` |
| `optimize_production_schedule` | `core/analytics/scheduling.py` | `t_aps_plan_mo_info` (no `mo.status` column) |
| `forecast_capacity_hr` | `core/analytics/capacity.py` | Historical throughput via `t_co_device` bridge |

---

### `orchestrator/` — Intent Pipeline

| File | Role |
|---|---|
| `intent_utils.py` | `parse_intent()` — async Bailian call, JSON strip, `IntentSchema` mapping |
| `intent_prompt.py` | Bailian extraction prompt (no workshop/RBAC fields in output) |
| `param_validation.py` | Per-intent required-field validators; returns message before DB on failure |
| `param_mappers.py` | `IntentSchema` → tool Pydantic params |
| `tool_registry.py` | Registers all 18 `IntentType` → tool + mapper + success message |
| `router.py` | `route_and_execute()` — parse → RAG → validate → dispatch |
| `cross_module.py` | Parallel production + quality + warehouse snapshot |

**Bailian call pattern:**

```python
response = await asyncio.to_thread(
    dashscope.Application.call,
    app_id=settings.bailian_app_id,
    prompt=prompt_text,
    api_key=settings.dashscope_api_key,
)
```

Entity IDs (`line_id`, `device_sn`, etc.) come from Bailian extraction only — never invented by the backend.

---

## MES Database Reference

- **Database:** `mes_db`
- **Schema:** `n2admin` (frozen — fixes are application-layer only)
- **Full export:** `db/schema.sql`
- **Read-only user:** configured via `DATABASE_URL`

Key tables: `t_smt_program_consumption_record`, `t_wip_detail`, `t_co_area`, `t_co_device`, `t_qm_inspect_info`, `t_wms_stock_info`.

**Real identifiers** (not placeholders like `L-01`): see [docs/mesai-query-1.1.md](docs/mesai-query-1.1.md) — e.g. line `FDQ-SMT-3`, device `BB-SMT-029`, equipment dates `2026-05-09`–`2026-06-21`.

---

## Security Model

1. Read-only PostgreSQL user via `DATABASE_URL`
2. No Text-to-SQL — SQL is hardcoded in MCP tools
3. **Global query scope** — MCP tools do not filter on `data_auth` or workshop headers
4. Parameterized queries only (`:named` bind params)
5. Param validation prevents execution with missing critical entities (no fake default line IDs)
6. Secrets in `.env` (gitignored); `.env.example` as template

---

## Dependencies

| Package | Role |
|---|---|
| `fastapi` | Web framework + OpenAPI/Swagger |
| `uvicorn[standard]` | ASGI server |
| `pydantic` / `pydantic-settings` | Validation + config |
| `sqlalchemy[asyncio]` | Async DB |
| `asyncpg` | PostgreSQL driver |
| `dashscope==1.20.0` | Alibaba Bailian / DashScope SDK |
| `pgvector` | PostgreSQL vector extension client |
| `pandas` / `openpyxl` | Excel export |
| `reportlab` | PDF export |
| `python-multipart` | Voice file uploads |

---

## Implementation Status

### Phase 1 — Core Orchestration (Complete)
- [x] Modular FastAPI structure
- [x] Request context middleware
- [x] Swagger UI endpoint

### Phase 2 — Production Data Analysis (Complete)
- [x] Async SQLAlchemy + asyncpg
- [x] Production MCP tools with table routing
- [x] `t_wip_detail` ↔ `t_co_area` join for reported yield
- [x] Mathematical safeguard layer

### v0.3 — Full Backend Upgrade (Complete)
- [x] RAG pipeline (pgvector + file fallback) + `/api/v1/rag/ingest`
- [x] Tool registry + param mappers + param validation (18 MCP tools)
- [x] Production extensions (`t_co_item`, `t_co_device`, `t_co_standard_time`) + analytics engines
- [x] Quality module (4 tools → `t_qm_*`)
- [x] Warehouse module (5 tools → `t_wms_*`)
- [x] Voice query, export xlsx/pdf, cross-module analysis
- [x] Schema/SQL alignment fixes (equipment `t_co_device` bridge, QM 8D joins, warehouse area lookup)
- [x] Global data access (RBAC row-level filtering removed)

### Known Gaps

| Item | Status |
|---|---|
| `get_standard_time_achievement` | Still filters `eq.area_sn` — often NULL; needs `t_co_device` bridge |
| `check_error_prevention` | SQL columns don't match physical QM scheme/IPQC schema |
| `t_co_area` deep hierarchy | One-level `parent_sn` join; may need recursive CTE |
| Unit tests | No `tests/` directory |
| Vue.js frontend | API-first via Swagger |

See [docs/mesai-mcp-1.1.md](docs/mesai-mcp-1.1.md) §5 for full mismatch tracking.

---

## Quick Test Guide

### Health check
```bash
curl http://127.0.0.1:8000/api/v1/health
```

### Natural-language queries (Bailian + DB required)

Use real line/device IDs and in-range dates from [docs/mesai-query-1.1.md](docs/mesai-query-1.1.md). No workshop header required.

```bash
# Equipment yield by line
curl -X POST http://127.0.0.1:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Total equipment yield on line FDQ-SMT-3 for 2026-06-20"}'

# Equipment yield by device
curl -X POST http://127.0.0.1:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Equipment yield for device BB-SMT-029 on 2026-06-20"}'

# Cross-module analysis
curl -X POST http://127.0.0.1:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Cross-module analysis for line FDQ-SMT-3"}'

# RAG ingest
curl -X POST http://127.0.0.1:8000/api/v1/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{"doc_type": "anomaly", "text": "FDQ-SMT-3 dip caused by feeder jam on device BB-SMT-029"}'
```

### Direct MCP tool invocation (bypasses Bailian)
```python
import asyncio
from datetime import datetime
from mcp_tools.production_tools import (
    get_yield_aggregation_tool,
    YieldAggregationParams,
    YieldType, GroupBy, Metric,
)
from models.schemas import MCPContext

async def test():
    params = YieldAggregationParams(
        yield_type=YieldType.EQUIPMENT,
        line_id="FDQ-SMT-3",
        start_date=datetime(2026, 6, 20),
        end_date=datetime(2026, 6, 21),
        group_by=GroupBy.DAILY,
        metric=Metric.SUM,
    )
    result = await get_yield_aggregation_tool.run(params, MCPContext())
    print(result)

asyncio.run(test())
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `invalid literal for int() with base 10: 'port'` | `DATABASE_URL` has literal `host:port` placeholder | Set real host and numeric port in `.env` |
| `intent: unknown` on every query | Missing `DASHSCOPE_API_KEY` or `BAILIAN_APP_ID` | Add Bailian credentials to `.env` |
| `intent: unknown`, API error in logs | Invalid Bailian key/app ID or API timeout | Verify credentials in Alibaba Model Studio |
| Empty `value: 0` or `[]` results | Wrong line ID (`L-01`), out-of-range dates, or schema mismatch | Use IDs from `mesai-query-1.1.md`; see `mesai-mcp-1.1.md` §5 |
| Validation message, no DB call | Missing `line_id` / `device_sn` / etc. in user query | Rephrase with explicit line or device |
| MCP tool DB errors | DB unreachable | Check `DATABASE_URL` connectivity |
| `GET /` returns 404 | Old server without root redirect | Pull latest `main.py`; `/` redirects to `/docs` |

---

## Team

Built for the **NEUTRON** team MES AI Assistant initiative. Product docs: `docs/`.
