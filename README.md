# NEUTRON MES AI Assistant — Backend

Enterprise Manufacturing Execution System (MES) AI Assistant backend for the **NEUTRON** team. The system accepts natural-language queries, extracts structured intent via **Alibaba Cloud Bailian (DashScope)**, and dispatches typed parameters to predefined **Model Context Protocol (MCP) tools** that query the MES PostgreSQL database.

**Stack:** Python 3.10+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), asyncpg, dashscope (Bailian SDK).

**Current version:** `0.2.0` — Phase 2 Production Data Analysis (I.1) + Feature 1.2 Bailian Intent Router

---

## Architectural Constraints (Audit Checklist)

| Constraint | Status | Implementation |
|---|---|---|
| **No Text-to-SQL** | Enforced | LLM extracts parameters only. MCP tools run predefined `sqlalchemy.text()` queries. |
| **Intent routing (Feature 1.2)** | Done | `parse_intent()` → Bailian `dashscope.Application.call` → `IntentSchema` |
| **API-first testing** | Done | Swagger UI at `/docs` (root `/` redirects here), ReDoc at `/redoc` |
| **RBAC context injection (Feature 13.1)** | Done | `RBACMiddleware` injects `workshop_id`; MCP tools filter on `data_auth` |
| **Math safeguard (Feature 5.2)** | Done | `core/math_safeguard.py` — std dev and growth rates computed in Python |

---

## High-Level Request Flow

```mermaid
sequenceDiagram
    participant User as Swagger_UI
    participant API as POST_/api/v1/query
    participant RBAC as RBACMiddleware
    participant Bailian as dashscope.Application
    participant Router as route_and_execute
    participant MCP as production_tools
    participant DB as PostgreSQL

    User->>API: query + X-MES-Workshop-Id
    API->>RBAC: inject MCPContext
    RBAC->>Router: route_and_execute
    Router->>Bailian: asyncio.to_thread Application.call
    Bailian-->>Router: JSON intent params
    Router->>MCP: tool.run params context
    MCP->>DB: parameterized SQL
    DB-->>MCP: raw rows
    MCP-->>User: OrchestratorResponse
```

1. User sends `POST /api/v1/query` with a natural-language `query` and optional RBAC headers.
2. `RBACMiddleware` injects `MCPContext` (`workshop_id`, etc.) into `request.state`.
3. `parse_intent(query, context)` calls Bailian asynchronously and returns `IntentSchema`.
4. `route_and_execute()` switches on `IntentType` and calls the matching Phase 2 MCP tool.
5. MCP tool queries PostgreSQL, computes statistics in Python, returns JSON to the client.

**Intent routing map:**

| `IntentType` | MCP Tool | Example query |
|---|---|---|
| `yield_aggregation` | `get_yield_aggregation` | "Total equipment yield on line L-03 for today" |
| `yield_anomalies` | `get_yield_anomalies_and_peaks` | "Show volatility on line L-01 this week" |
| `yield_comparison` | `compare_yield_periods` | "Compare growth yesterday vs today on line L-02" |
| `unknown` | *(none)* | Unrecognized or failed intent extraction |

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
| `DEFAULT_WORKSHOP_ID` | No | Fallback workshop when no `X-MES-Workshop-Id` header (default: `WS-001`) |
| `DB_POOL_SIZE` | No | Connection pool size (default: `5`) |
| `DEBUG` | No | Enable SQL echo, Bailian raw response logging, and tool result debug logs |

\*Without Bailian credentials the app still starts; queries return `intent: unknown` with a logged warning.

**Common startup error:** If `DATABASE_URL` still contains the placeholder `host:port` (copied literally from an old template), SQLAlchemy will fail with `invalid literal for int() with base 10: 'port'`. Replace with a real hostname and numeric port (e.g. `5432`).

---

## Directory Structure

```
mesai/
├── main.py                     # FastAPI entry point (lifespan, RBAC, / → /docs redirect)
├── requirements.txt
├── .env.example                # Environment template (never commit .env)
├── README.md
│
├── api/
│   └── routes.py               # /api/v1/health, /api/v1/query
│
├── core/
│   ├── config.py               # Pydantic Settings (.env loader)
│   ├── db.py                   # Async SQLAlchemy engine & sessions
│   ├── logging.py
│   ├── math_safeguard.py       # Feature 5.2 — server-side statistics
│   └── security.py             # Feature 13.1 — RBAC middleware
│
├── models/
│   └── schemas.py              # IntentSchema, MCPContext, API models
│
├── mcp_tools/
│   ├── base.py                 # BaseMCPTool abstract class
│   └── production_tools.py     # Phase 2 — 3 real DB tools
│
├── orchestrator/
│   └── router.py               # Bailian intent router + MCP dispatcher
│
├── db/                         # Reference schema exports (not runtime)
│   ├── schema.sql
│   └── may.sql
│
└── docs/                       # Product documentation (Word)
```

---

## File-by-File Reference

### `main.py` — Application Entry Point

| Symbol | Purpose |
|---|---|
| `lifespan()` | `setup_logging()` → `init_db()` on startup; `close_db()` on shutdown |
| `create_app()` | FastAPI app + `RBACMiddleware` + API router + `/` → `/docs` redirect |
| `app` | ASGI instance for uvicorn |

---

### `api/routes.py` — HTTP Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/health` | GET | Liveness: `{"status": "ok", "service": "neutron-mes-ai"}` |
| `/api/v1/query` | POST | Natural-language query → Bailian intent → MCP tool → result |

**Swagger headers for RBAC simulation:**

| Header | Purpose |
|---|---|
| `X-MES-Workshop-Id` | Workshop scope → `data_auth` in DB queries |
| `X-MES-User-Id` | Optional user identity |
| `X-MES-Permission-Level` | Optional permission level (default: `operator`) |

---

### `core/config.py` — Settings

All settings load from `.env` via Pydantic `BaseSettings`. `get_settings()` is a cached singleton.

Key fields: `database_url`, `dashscope_api_key`, `bailian_app_id`, `default_workshop_id`, `db_pool_size`, `debug`.

If `.env` defines `DATABASE_URL`, it overrides the built-in default DSN in `config.py`.

---

### `core/db.py` — Database Bridge (F0.4)

SQLAlchemy 2.0 async connection pool.

| Symbol | Purpose |
|---|---|
| `init_db()` | Create engine, run `SELECT 1`. Logs errors for bad URL or unreachable DB; does not crash the app. |
| `close_db()` | Dispose engine on shutdown |
| `get_db()` | FastAPI dependency — yields `AsyncSession` per request |
| `get_session()` | Standalone session for MCP tool execution |

Invalid `DATABASE_URL` (e.g. non-numeric port) is caught at startup with a clear log message.

---

### `core/security.py` — RBAC (Feature 13.1)

`RBACMiddleware` reads MES headers and stores `MCPContext` on `request.state.mes_context`. `get_mes_context(request)` retrieves it in route handlers.

Production path (future): JWT/session → MES roles → `workshop_id`.

---

### `core/math_safeguard.py` — Mathematical Safeguard (Feature 5.2)

| Function | Formula | Used by |
|---|---|---|
| `population_std_dev(values)` | σ = √(Σ(x − μ)² / N) | `get_yield_anomalies_and_peaks` (`volatility`) |
| `period_over_period_growth_rate(current, past)` | ((current − past) / past) × 100 | `compare_yield_periods` |

---

### `models/schemas.py` — Shared Pydantic Models

| Model / Enum | Purpose |
|---|---|
| `IntentType` | `yield_aggregation`, `yield_anomalies`, `yield_comparison`, `unknown` |
| `BailianIntentExtraction` | Strict Pydantic model for raw Bailian JSON before mapping |
| `IntentSchema` | Bailian output: intent, dates, line_id, yield_type, group_by, metric, etc. |
| `MCPContext` | RBAC: `workshop_id`, `user_id`, `permission_level` |
| `OrchestratorRequest` | `{ "query": "..." }` |
| `OrchestratorResponse` | `{ intent, tool_name, result, message }` |

Phase 2 tool param/result models live in `mcp_tools/production_tools.py`.

---

### `mcp_tools/production_tools.py` — Phase 2 Tool Arsenal

Three token-optimized tools. All SQL via `sqlalchemy.text()` with bound parameters.

#### Database table routing

| `yield_type` | Table(s) | Line filter | Qty | Time column |
|---|---|---|---|---|
| `equipment` | `t_smt_program_consumption_record` | `area_sn = :line_id` | `finish_qty` | `create_time` |
| `reported` | `t_wip_detail` JOIN `t_co_area` ×2 | `line.area_sn = :line_id` | `pro_qty − ng_qty − scrap_qty` | `COALESCE(in_time, create_time)` |

**Reported yield join** (workstation → line hierarchy):

```sql
n2admin.t_wip_detail wd
JOIN n2admin.t_co_area ws ON wd.work_stationsn = ws.area_sn
JOIN n2admin.t_co_area line ON ws.parent_sn = line.area_sn
WHERE line.area_sn = :line_id AND wd.data_auth = :workshop_id
```

#### Tools

| Tool | Singleton | Purpose |
|---|---|---|
| `get_yield_aggregation` | `get_yield_aggregation_tool` | Sum, average, achievement rate (daily/hourly/total) |
| `get_yield_anomalies_and_peaks` | `get_yield_anomalies_tool` | Volatility, below-standard, peak hourly |
| `compare_yield_periods` | `compare_yield_periods_tool` | Period-over-period totals + growth rate |

Achievement rates and growth rates are computed in Python (`_compute_metric`, `math_safeguard`), not by the LLM.

---

### `orchestrator/router.py` — Intent Router (F0.2 + Feature 1.2)

| Function | Purpose |
|---|---|
| `parse_intent(query, context)` | Async Bailian call → `IntentSchema` |
| `_build_intent_prompt(query, context)` | Structured JSON extraction prompt |
| `_strip_markdown_json(text)` | Remove `` ```json ... ``` `` wrappers |
| `_normalize_intent(raw)` | Map `YIELD_AGGREGATION` → `IntentType.YIELD_AGGREGATION` |
| `_ai_payload_to_intent_schema(data, query)` | Bailian JSON → `IntentSchema` |
| `_fallback_intent(query, reason)` | `UNKNOWN` on missing credentials, API error, bad JSON |
| `_intent_to_*_params(intent)` | Map `IntentSchema` → tool param models |
| `route_and_execute(query, context)` | Full pipeline: Bailian → MCP tool → response |

**Bailian call pattern:**

```python
response = await asyncio.to_thread(
    dashscope.Application.call,
    app_id=settings.bailian_app_id,
    prompt=prompt_text,
    api_key=settings.dashscope_api_key,
)
```

`workshop_id` always comes from RBAC middleware — never from AI output.

---

## MES Database Reference

- **Database:** `mes_db`
- **Schema:** `n2admin`
- **Full export:** `db/schema.sql`
- **Read-only user:** configured via `DATABASE_URL`

Key tables: `t_smt_program_consumption_record`, `t_wip_detail`, `t_co_area`.

---

## Security Model

1. Read-only PostgreSQL user via `DATABASE_URL`
2. No Text-to-SQL — SQL is hardcoded in MCP tools
3. RBAC — `data_auth = :workshop_id` from middleware, not user free text
4. Parameterized queries only (`:named` bind params)
5. Secrets in `.env` (gitignored); `.env.example` as template

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
| `python-dateutil` | Date utilities |

---

## Implementation Status

### Phase 1 — Core Orchestration (Complete)
- [x] Modular FastAPI structure
- [x] RBAC middleware prep
- [x] Swagger UI endpoint

### Phase 2 — Production Data Analysis, I.1 (Complete)
- [x] Async SQLAlchemy + asyncpg
- [x] Three production MCP tools with table routing
- [x] `t_wip_detail` ↔ `t_co_area` join for reported yield
- [x] Mathematical safeguard layer

### Feature 1.2 — Bailian AI Intent Router (Complete)
- [x] `dashscope` SDK integration
- [x] Async `parse_intent()` via `asyncio.to_thread`
- [x] JSON sanitization + `IntentSchema` mapping
- [x] Graceful `UNKNOWN` fallback
- [x] Orchestrator wired to Phase 2 tools (Phase 1 mock deprecated)

### Known Gaps

| Item | Status |
|---|---|
| JWT / MES auth | Headers simulate RBAC |
| `t_co_area` deep hierarchy | One-level `parent_sn` join; may need recursive CTE |
| Unit tests | No `tests/` directory |
| Vue.js frontend | API-first via Swagger |

---

## Quick Test Guide

### Health check
```bash
curl http://127.0.0.1:8000/api/v1/health
```

### Natural-language queries (Bailian + DB required)
```bash
# Aggregation
curl -X POST http://127.0.0.1:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "X-MES-Workshop-Id: WS-042" \
  -d '{"query": "Total equipment yield on line L-03 for today"}'

# Anomalies
curl -X POST http://127.0.0.1:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "X-MES-Workshop-Id: WS-042" \
  -d '{"query": "Show volatility on line L-01 this week"}'

# Period comparison
curl -X POST http://127.0.0.1:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "X-MES-Workshop-Id: WS-042" \
  -d '{"query": "Compare yield growth yesterday vs today on line L-02"}'
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
        line_id="L-01",
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 31),
        group_by=GroupBy.DAILY,
        metric=Metric.SUM,
    )
    result = await get_yield_aggregation_tool.run(params, MCPContext(workshop_id="WS-001"))
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
| MCP tool DB errors | DB unreachable or wrong `workshop_id` | Check `DATABASE_URL` and `X-MES-Workshop-Id` header |
| `GET /` returns 404 | Old server without root redirect | Pull latest `main.py`; `/` redirects to `/docs` |

---

## Team

Built for the **NEUTRON** team MES AI Assistant initiative. Product docs: `docs/`.
