# MES AI Frontend — Design & Architecture Report

This document describes the new UI design in the `frontend/` folder: what it is, how it is structured, and what still needs to be wired to the NEUTRON MES AI backend.

**Product name (UI):** 宁波睿创 AI 工业大脑 (Ningbo Ruichuang AI Industrial Brain)  
**Package name:** `mes-ai-client`  
**Current state:** All five assistants use live backend data for dashboard and chat where MES data is available; slots without data sources fall back to mock values (`partial: true`).

---

## Purpose

The frontend is a **single-page application (SPA)** that showcases five domain-specific AI assistants for manufacturing operations:

| Assistant | Route | Domain focus |
|-----------|-------|--------------|
| AI 生产助手 (Production) | `/assistant/production` | Scheduling, capacity, work orders, bottlenecks |
| AI 仓库助手 (Warehouse) | `/assistant/warehouse` | Inventory, locations, inbound/outbound efficiency |
| AI 质量助手 (Quality) | `/assistant/quality` | Defect analysis, quality trends, improvement |
| AI 设备助手 (Equipment) | `/assistant/equipment` | Equipment health, predictive maintenance, downtime |
| AI 采购助手 (Procurement) | `/assistant/procurement` | Supplier performance, cost, supply risk |

Users land on a **home page** with five interactive cards, then open an assistant dashboard that combines KPI cards, charts, an insight panel, and a collapsible AI chat console.

---

## Technology Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Framework | Vue 3 (Composition API, `<script setup>`) | JavaScript only in the active entry path |
| Build tool | Vite 5 | Dev server on port **3000**, auto-open browser |
| UI library | Element Plus 2.x | Layout, cards, inputs, buttons, tags, icons |
| Routing | Vue Router 4 | History mode (`createWebHistory`) |
| Charts | ECharts 6 | Six charts per assistant in a bento-style mosaic |
| i18n | Custom (`useLocale` + `messages.js`) | Chinese (default) and English; persisted in `localStorage` |

There is no Pinia/Vuex store, no TypeScript in the running app (`main.js` is the entry point), and no test suite.

---

## High-Level Architecture

Every route shares the same global shell. Page content is rendered inside the shell via `<RouterView>`.

```
index.html
└── main.js
    └── App.vue
        └── AppShell.vue
            ├── AppBackground.vue     # Full-screen sci-fi background (gradient, grid, particles)
            ├── AppHeader.vue         # Title, clock, language toggle, fullscreen, back button
            └── <RouterView />
                ├── Index.vue         # Home — five assistant entry cards
                └── assistants/*/index.vue   # Thin wrapper → AssistantDashboardLayout
```

### Request / data flow (current)

```
User action
    │
    ├─ Home card click ──► vue-router ──► assistant index.vue
    │
    ├─ Dashboard KPIs / charts ──► useAssistantPage ──► static mock data (charts.js + messages.js)
    │
    └─ Chat message ──► useAssistantChat ──► simulated delay + mock reply from i18n
```

There is **no live call** to `POST /api/v1/query` or other backend endpoints in the code that actually runs today.

---

## Routing

Defined in `frontend/src/router/index.js`.

| Path | Component | Description |
|------|-----------|-------------|
| `/` | `views/Index.vue` | Home page with hero and assistant cards |
| `/assistant/production` | `views/assistants/production/index.vue` | Production dashboard |
| `/assistant/warehouse` | `views/assistants/warehouse/index.vue` | Warehouse dashboard |
| `/assistant/quality` | `views/assistants/quality/index.vue` | Quality dashboard |
| `/assistant/equipment` | `views/assistants/equipment/index.vue` | Equipment dashboard |
| `/assistant/procurement` | `views/assistants/procurement/index.vue` | Procurement dashboard |
| `/assistant/:type` | redirect | Legacy alias; maps `type` to the explicit routes above |
| `*` | redirect → `/` | Catch-all |

Assistant routes use **lazy imports** (`() => import(...)`) to split bundles per assistant.

---

## Page Breakdown

### Home page (`Index.vue`)

Three main sections:

1. **Hero** — Main headline, subtitle, and partner tags (阿里云, 千问大模型, 睿创 Ai). Copy comes from i18n keys under `home.*`.
2. **Assistant cards** — Responsive grid (1–5 columns depending on breakpoint). Each card shows avatar, title, and hover detail panel with feature bullets.
3. **Floating decoration** — Decorative AI avatar in the bottom-right (loaded from an external image URL).

**Interactions:**

- Hover a card → detail panel slides in with capability description.
- Click a card → navigate to that assistant’s dashboard.

Card data is built by `useLocale().homeAssistants`, which merges i18n text with static routes and avatars from `i18n/messages.js`.

### Assistant dashboard (shared layout)

All five assistants use **`AssistantDashboardLayout.vue`** with the same structure; only the assistant key, chart builder, and theme accent differ.

**Loading behavior**

- Navigating from the home page opens the **page shell immediately** (header + layout).
- The **AI chat console** on the right is interactive right away — it does not wait for dashboard data.
- The **left report column** shows Element Plus skeletons (KPI cards, chart placeholders, insight) while `GET /api/v1/assistants/{module}/dashboard` runs in the background.
- ECharts instances are **not mounted** until dashboard data arrives (avoids double-render on mock data).
- On failure, an error banner with retry appears; chat remains usable. Dashboard fetch timeout: **60 seconds**.

**Left column (~65% width on large screens) — Data report**

- **KPI row** — Three metric cards (label, value, trend), e.g. plan attainment, utilization, WIP.
- **Chart mosaic** — Six ECharts panels in a bento grid (`AssistantChartMosaic` + `chartMosaicLayout.js`).
- **Insight card** — Summary from backend `insight` when live, else i18n template.

**Right column (~35%) — AI chat console**

- Greeting and quick-prompt buttons when no conversation yet.
- Message thread; integrated assistants call `POST /api/v1/query` (independent of dashboard load).
- Collapsible panel: user can hide the console and reopen it from a docked floating button (`Teleport` to `body`).
- Enter key or Send button submits messages.

Each assistant sets a CSS variable `--assistant-accent` for theme-colored charts, borders, and glow effects.

**Backend cache:** Dashboard responses may be served from SQLite cache on the server (see [database.md](./database.md)); the frontend uses the same API contract regardless.

---

## Configuration & Content Model

Content is centralized in **`src/i18n/messages.js`**, which holds:

- UI strings for header, common labels, home page, and all five assistants (zh + en).
- Per-assistant: title, subtitle, greeting, prompts, mock chat replies, KPI labels, chart titles/axis labels.
- Static metadata exports: `assistantRoutes`, `assistantAvatars`, `assistantAccents`, `assistantLayouts`, `assistantKpiValues`.

The composable **`useLocale.js`** is the runtime source of truth:

- `t(key, params)` — translation with `{placeholder}` interpolation.
- `getAssistantPageConfig(key)` — merges i18n text with numeric KPI values and chart definitions.
- `homeAssistants` — list for the home page cards.
- Locale persisted under `localStorage` key `mes-ai-locale` (`zh` | `en`).

### Per-assistant file split

Each assistant folder under `views/assistants/<name>/` contains:

| File | Role |
|------|------|
| `index.vue` | Page template; wires header, charts, chat; sets `assistantKey` |
| `charts.js` | Builds six ECharts options from presets + mock series data |
| `pageConfig.js` | **Legacy duplicate** of config now served by i18n — **not imported** by `index.vue` |

`src/data/assistantConfigs.js` aggregates static route/avatar/accent data from `messages.js`. The home page no longer imports it directly; prefer `useLocale()`.

---

## Shared Components

| Component | File | Responsibility |
|-----------|------|----------------|
| `AppShell` | `components/AppShell.vue` | Root layout: background + header + main slot |
| `AppBackground` | `components/AppBackground.vue` | Animated background layer |
| `AppHeader` | `components/AppHeader.vue` | Live clock, product title, zh/en switch, fullscreen, conditional “Back to Home” |
| `AssistantPageHeader` | `components/AssistantPageHeader.vue` | Dashboard title bar with status pill |
| `AssistantChartMosaic` | `components/AssistantChartMosaic.vue` | Renders the six-chart bento grid |
| `AssistantChatConsole` | `components/AssistantChatConsole.vue` | Full chat UI with collapse/expand |

---

## Composables

| Composable | File | Role |
|------------|------|------|
| `useLocale` | `composables/useLocale.js` | i18n, datetime formatting, page config assembly |
| `useAssistantPage` | `composables/useAssistantPage.js` | ECharts lifecycle (init, resize, dispose), insight text, chart refs |
| `useAssistantChat` | `composables/useAssistantChat.js` | Chat send/prompt handlers — **mock only** today |

The chat composable includes a commented TODO showing the intended integration point:

```js
// POST /api/assistant/chat  (or the project's /api/v1/query)
// body: { assistantKey, message }
```

Mock replies use keys like `assistants.production.mockReply` in `messages.js`, with ~1–1.5 s artificial latency.

---

## Chart System

- **`utils/chartPresets.js`** — Reusable ECharts option builders: `lineChart`, `barChart`, `gaugeChart`, shared axis/tooltip styling tuned for dark dashboards.
- **`utils/chartMosaicLayout.js`** — Fixed 6-panel bento layout (varying `colSpan` / `rowSpan` / `size`).
- **`views/assistants/*/charts.js`** — Per-assistant mock data mapped to chart types (line, bar, gauge).

Charts re-render when the user switches language (month labels and titles update). `ResizeObserver` keeps charts sized correctly inside the mosaic grid.

---

## Styling & Visual Design

The UI follows a **dark, industrial “command center”** aesthetic:

- Deep blue/slate backgrounds with grid lines, scan effects, and particle animation.
- Glassmorphism-style cards with accent-colored borders and glow.
- Per-assistant accent colors (e.g. production `#38bdf8`, warehouse `#22c55e`).
- Custom scrollbars (`assets/styles/scrollbars.css`).
- Scoped styles in `Index.vue`; shared dashboard styles in `assets/styles/assistant-dashboard.css`.

Stylesheet map:

| File | Scope |
|------|-------|
| `style.css` | Global reset, body, `#app` |
| `assets/styles/app.css` | Background layers |
| `assets/styles/header.css` | Top navigation bar |
| `assets/styles/index.css` | Home page (imported by Index or global) |
| `assets/styles/assistant-dashboard.css` | All assistant dashboards |
| `assets/styles/scrollbars.css` | Scrollbar theming |

---

## Static Assets

Located in `frontend/public/`:

- **`avatars/`** — PNG avatar for each assistant (production, warehouse, quality, equipment, procurement).
- **`effects/halo-platform-blue.png`** — Decorative halo image.

Home page also references one **external** portrait URL for the floating AI decoration (Trae IDE image API). That dependency may break offline or if the URL expires.

---

## Backend Integration

All five assistants are integrated with the NEUTRON backend. Slots without MES coverage use mock fallback on the frontend.

### Environment variables

Copy [`frontend/.env.example`](frontend/.env.example) to `.env.development` or `.env.local`:

| Variable | Purpose | Default |
|----------|---------|---------|
| `VITE_API_BASE_URL` | Backend origin | empty (same-origin / Vite proxy) |
| `VITE_DEFAULT_LINE_ID` | Production line for dashboard | `FDQ-SMT-3` |
| `VITE_DEFAULT_WH_CODE` | Warehouse code filter (empty = all) | empty |
| `VITE_DEFAULT_WORKSHOP_ID` | Header for chat history APIs | `WS-001` |
| `VITE_INTEGRATED_ASSISTANTS` | Comma-separated live modules | `production,warehouse,quality,equipment,procurement` |

**Standalone repo:** set `VITE_API_BASE_URL=http://127.0.0.1:8000` and ensure backend CORS allows your frontend origin (port 3000 is included).

Backend optional: `DEFAULT_LINE_ID=FDQ-SMT-3`, `DEFAULT_WH_CODE=WH01` in root `.env`.

### API endpoints used

| Endpoint | Used by | Purpose |
|----------|---------|---------|
| `GET /api/v1/assistants/production/dashboard` | Production dashboard | KPI + chart slots (`line_id`) |
| `GET /api/v1/assistants/warehouse/dashboard` | Warehouse dashboard | KPI + chart slots (`wh_code` optional) |
| `GET /api/v1/assistants/quality/dashboard` | Quality dashboard | KPI + chart slots (`line_id` optional) |
| `GET /api/v1/assistants/equipment/dashboard` | Equipment dashboard | KPI + chart slots (`line_id` optional) |
| `GET /api/v1/assistants/procurement/dashboard` | Procurement dashboard | KPI + chart slots (`wh_code` optional) |
| `POST /api/v1/query` | Integrated assistant chat | NL query → Markdown reply; optional `assistant_module` for persona |
| `GET /api/v1/health` | Optional | Liveness check |

### Integration architecture

```
frontend/src/api/           # HTTP client (repo-independent)
frontend/src/adapters/      # chartSlots.js, dashboard.js, chat.js (shared)
frontend/src/composables/
  useIntegratedAssistantPage.js   # generic dashboard loader
  useProductionAssistantPage.js   # production wrapper
  useWarehouseAssistantPage.js    # warehouse wrapper
  useQualityAssistantPage.js      # quality wrapper
  useEquipmentAssistantPage.js    # equipment wrapper
  useProcurementAssistantPage.js  # procurement wrapper
  useAssistantChat.js             # routes integrated keys to /query
  useAssistantPage.js             # optional live KPI/chart refs
```

**Graceful degradation:** If the dashboard API fails after loading completes, mock KPIs/charts are shown and an error banner offers retry. Chat is never blocked by dashboard load state.

**Dashboard cache:** The backend may return cached snapshots (`X-Dashboard-Cache: hit|stale|miss`). Prewarm with `python scripts/refresh_dashboard_cache.py` on deploy.

**Chat personas:** Integrated chat sends `assistant_module` (same key as the route, e.g. `procurement`) plus a domain prefix on the query string. The backend uses [`orchestrator/module_personas.py`](../orchestrator/module_personas.py) (aligned with `messages.js` greetings) for UNKNOWN-intent replies and module-specific synthesis/fallback report styles.

**Partial live data (production):** KPI 在制工单, chart 工单状态分布, and chart OEE趋势 have no MCP tools yet.

**Partial live data (warehouse):** Charts 出入库趋势, 拣货效率趋势, 收货及时率 have no MCP tools yet; KPI 库存准确率 is derived from stock summary SQL.

**Partial live data (quality):** Chart 检验及时率 has no MCP tool; chart 返修率趋势 may fall back if daily rework series is empty; chart 缺陷类型排行 may show 8D reason text rather than fixed i18n categories.

**Partial live data (equipment):** KPI 平均停机, charts 告警等级分布 and MTBF趋势 have no MES data source; chart 停机时长分析 uses a production-rate proxy and may show device names instead of equipment-type categories.

**Partial live data (procurement):** Chart 议价空间趋势 has no price-history table; KPI 采购节省率 falls back if prior-period spend is zero; chart labels may show real supplier names and ABC type codes from MES.

### Local development (integrated)

Terminal 1 — backend:

```bash
source .venv/bin/activate
uvicorn main:app --reload   # http://127.0.0.1:8000
```

Terminal 2 — frontend (Vite proxies `/api/v1` → backend):

```bash
cd frontend && npm run dev   # http://localhost:3000
```

Open any assistant route under `/assistant/*` — dashboard loads from API; chat sends to `/api/v1/query`.

---

## Backend Integration Status (all modules)

| Module | Dashboard API | Chat API |
|--------|---------------|----------|
| production | Live (`GET .../production/dashboard`) | Live (`POST /query`) |
| warehouse | Live (`GET .../warehouse/dashboard`) | Live (`POST /query`) |
| quality | Live (`GET .../quality/dashboard`) | Live (`POST /query`) |
| equipment | Live (`GET .../equipment/dashboard`) | Live (`POST /query`) |
| procurement | Live (`GET .../procurement/dashboard`) | Live (`POST /query`) |

---

## Development

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000
npm run build    # output to dist/
npm run preview  # preview production build
```

**Scripts** (`package.json`): `dev`, `build`, `preview` only.

**Build verified:** `npm install` and `npm run build` complete successfully (Vite production output in `dist/`). Rollup warns about two chunks over 500 kB (ECharts + main bundle) — expected for a chart-heavy dashboard app.

**Element Plus locale** follows the app language in `App.vue` (`zh-cn` vs `en`).

---

## Directory Structure (actual)

```
frontend/
├── index.html
├── package.json
├── vite.config.js
├── .env.example              # VITE_* integration vars
├── .env.development
├── README.md                 # Partially outdated — see notes below
├── public/
│   ├── avatars/              # Assistant PNG avatars
│   └── effects/
└── src/
    ├── api/                  # client.js, query.js, dashboard.js, locale.js, integration.js
    ├── adapters/             # chartSlots.js, dashboard.js, chat.js
    ├── main.js               # Entry point
    ├── App.vue
    ├── router/index.js
    ├── i18n/messages.js      # All copy + assistant metadata
    ├── data/assistantConfigs.js   # Legacy aggregator (prefer useLocale)
    ├── composables/          # useLocale, useAssistantPage, useIntegratedAssistantPage, use*AssistantPage
    ├── components/           # Shell, header, charts, chat
    ├── views/
    │   ├── Index.vue
    │   └── assistants/
    │       ├── production/     # index.vue, charts.js, pageConfig.js (unused)
    │       ├── warehouse/
    │       ├── quality/
    │       ├── equipment/
    │       └── procurement/
    ├── utils/                # chartPresets.js, chartMosaicLayout.js
    └── assets/styles/        # Themed CSS
```

---

## Deployment Notes

Root `docker-compose.yml` defines a `web` service that builds from `./frontend/Dockerfile`. **That Dockerfile is not present in the frontend folder yet**, so containerized frontend deployment will need that file added (typical pattern: Node build stage + nginx serving `dist/` and proxying `/api` to the `api` service).

---

## Gaps, Cleanup, and Documentation Drift

Items to be aware of when continuing development:

1. **`frontend/README.md` is outdated** — It describes a single `AssistantDashboard.vue` driven by `assistantConfigs.js`. The implemented design uses **five separate** `views/assistants/*/index.vue` files and **`useLocale().getAssistantPageConfig`** for text.
2. **`pageConfig.js` per assistant is dead code** — Safe to remove or wire up only if you want locale-free static configs again.
3. **Mock data everywhere** — Dashboards are demos; numbers and chart series do not reflect live MES PostgreSQL data.
4. **Procurement MCP tools** — Dashboard uses WMS receive/supplier SQL; dedicated procurement NL intents and price-history sourcing remain future work.
5. **External floating avatar URL** — Consider hosting locally under `public/` for reliability.
6. **No frontend Dockerfile** — Required for the existing compose stack.

---

## Summary

The frontend is a **Vue 3 + Vite + Element Plus + ECharts** showcase for five manufacturing AI assistants. All five are wired to the FastAPI dashboard API; chat uses `/api/v1/query` with `assistant_module` and domain prefixes when listed in `VITE_INTEGRATED_ASSISTANTS`.

For backend API details, intent routing, and test queries, see [readme.md](./readme.md), [mesai-mcp-1.1.md](./mesai-mcp-1.1.md), and [mesai-query-1.1.md](./mesai-query-1.1.md).
