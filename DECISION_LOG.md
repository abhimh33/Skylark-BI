# SkyLark BI Agent — Decision Log

**Project**: Business Intelligence AI Agent for monday.com  
**Author**: Abhishek M H  
**Date**: February 2026  
**Stack**: FastAPI · React + Vite · Groq LLM · Render · Vercel  
**Live Application**: [https://skylark-bi.vercel.app](https://skylark-bi.vercel.app)

---

## 1. Key Assumptions

| # | Assumption | Rationale |
|---|-----------|-----------|
| 1 | **Read-only integration** — The agent only reads from monday.com boards; it never creates, updates, or deletes items. | The brief specified an analytical agent, not an automation tool. Read-only access is the safest posture for a live production board. |
| 2 | **Single-tenant evaluation context** — One monday.com account, two boards (Deals & Work Orders), one concurrent user. | Allowed elimination of multi-tenancy, auth, and rate-limit queuing in favour of speed of delivery. |
| 3 | **Messy real-world data** — Board data contains nulls, inconsistent casing, empty numeric fields, scientific notation, and conflicting status labels. | Discovered upon first live data pull (346 deals, 176 work orders). A dedicated data-cleaning layer was added immediately rather than trusting source quality. |
| 4 | **Founder-level audience** — All outputs target a technical founder / CXO who wants actionable summaries, not raw tables. | Drove prompt design, INR currency formatting (₹ Cr / ₹ L), severity-based warning labels, and the "Leadership Update" feature. |
| 5 | **LLM as a reasoning layer, not a data layer** — Groq generates summaries over pre-computed metrics; it never queries monday.com directly. | Avoids hallucination risk. Every number the LLM sees has been computed deterministically by the MetricsEngine. |

---

## 2. Tech Stack Justification

| Component | Choice | Why |
|-----------|--------|-----|
| **Backend Framework** | FastAPI (Python) | Async-native, dependency injection, Pydantic validation, auto-generated OpenAPI docs. Fastest iteration speed for an API-first project. |
| **Frontend** | React + Vite | Vite offers sub-second HMR; React's component model was ideal for the chat-style UI with markdown rendering, metric cards, and suggestion chips. |
| **LLM Provider** | Groq (`llama-3.3-70b-versatile`) | Lowest-latency inference API available (<2 s for 70B model). Free tier sufficient for evaluation. |
| **monday.com Client** | Custom GraphQL client (httpx) | monday.com's Python SDK is not async-ready. A thin custom client with column-value flattening gave full control over pagination and error handling. |
| **Caching** | In-memory TTL cache (custom) | Zero-dependency, thread-safe, Redis-interface-compatible. Perfectly adequate for single-instance deployment; designed to swap to Redis with a single import change. |
| **Backend Hosting** | Render (Web Service) | Free tier, GitHub auto-deploy, supports Python 3.11, environment variable management, and custom start commands. |
| **Frontend Hosting** | Vercel | Zero-config Vite deployment, global edge CDN, instant rollbacks, free tier. |

---

## 3. Architectural Design Decisions

### Layered Pipeline Architecture

```
 ┌──────────────────────────────────────────────────────────────┐
 │                        React Frontend                        │
 │          (Chat UI · Markdown · Metric Cards · Chips)         │
 └──────────────────────┬──────────────────────────────────────┘
                        │  POST /ask  { question }
 ┌──────────────────────▼──────────────────────────────────────┐
 │                     FastAPI Router                           │
 │         ┌───── Response Cache Check (SHA-256 key) ────┐     │
 │         │  HIT → return cached AskResponse             │     │
 │         │  MISS ↓                                      │     │
 │    ┌────▼────┐  ┌──────────┐  ┌─────────────┐         │     │
 │    │ monday  │→ │  Data    │→ │  Metrics    │         │     │
 │    │ Client  │  │ Cleaner  │  │  Engine     │         │     │
 │    └─────────┘  └──────────┘  └──────┬──────┘         │     │
 │    (Board Cache)                     │                 │     │
 │                               ┌──────▼──────┐         │     │
 │                               │  AI Service │         │     │
 │                               │  (Groq LLM) │         │     │
 │                               └──────┬──────┘         │     │
 │         │  Store in Response Cache    │                │     │
 │         └─────────────────────────────┘                │     │
 └──────────────────────────────────────────────────────────────┘
```

**Design rationale:**

- **monday_client** — Isolated GraphQL interaction. Column values are flattened into dictionaries at this layer so downstream code never deals with monday.com's nested `column_values` structure.
- **data_cleaner** — Normalises sector names, parses numerics (handles ₹, commas, scientific notation), fills nulls with sensible defaults, and emits structured `DataQualityWarning` objects.
- **business_logic/metrics** — Pure deterministic computation. Seven metric types (Pipeline Value, Pipeline by Sector, Deal Win/Loss Ratio, Revenue by Sector, Invoiced vs Collected, Collection Efficiency, Pipeline vs Revenue) plus a composite `LEADERSHIP_UPDATE` that runs all seven.
- **ai_service** — Prompt templates are separated from service logic (`prompts.py` vs `service.py`). The service performs intent extraction, summary generation, follow-up suggestions, and clarification handling.
- **cache** — Two singleton caches: `board_cache` (3 min TTL) for monday.com data, `response_cache` (5 min TTL) for identical-question deduplication. Thread-safe via `threading.Lock`.
- **routers/ask** — Orchestrates the pipeline; each step logs timing and failures independently.

---

## 4. Trade-offs Due to Time Constraint

| What I Built | What I Deferred | Why |
|-------------|----------------|-----|
| In-memory TTL cache | Redis / Memcached | Single-instance deployment makes in-memory sufficient; Redis adds infra cost. Cache class is designed as a drop-in swap. |
| Hardcoded board IDs | Dynamic board discovery | Two boards were specified; runtime introspection adds complexity without immediate value. |
| Simple chat UI | Full analytics dashboard with charts | Priority was proving the AI pipeline end-to-end. Chart.js / Recharts integration is a natural next step. |
| Basic CORS allowlist | JWT-based authentication / RBAC | Single-tenant evaluation context; no user data to protect beyond API keys in env vars. |
| Manual prompt tuning | Prompt evaluation framework | Would need a test harness with labelled question sets; skipped for velocity. |
| stdout logging | Structured logging + APM | `structlog` is in `requirements.txt` but not wired; would integrate Sentry/Datadog in production. |

---

## 5. Leadership Update Interpretation

The brief asked for executive-level insights. I interpreted "leadership update" as a structured briefing a founder would receive in a weekly standup:

1. **Trigger**: The user asks "Give me a leadership update" (or any query the LLM classifies as `LEADERSHIP_UPDATE` intent).
2. **Computation**: The `MetricsEngine` runs **all seven** metric computations in a single pass — pipeline value, sector breakdown, win/loss, revenue, invoiced vs collected, collection efficiency, and pipeline-to-revenue ratio.
3. **LLM Prompt**: A dedicated `LEADERSHIP_UPDATE` prompt template instructs the model to produce four sections:
   - 📊 **Key Numbers** — top-line pipeline, revenue, collection figures
   - ⚡ **What Needs Attention** — anomalies, low collection, stalled deals
   - ✅ **What's Going Well** — strong sectors, improving ratios
   - 📋 **Recommended Actions** — 2–3 concrete next steps
4. **Data Quality Context**: Warnings are formatted as executive-friendly severity badges (`🔴 High`, `🟡 Medium`, `🟢 Low`) so the founder understands data coverage limitations.
5. **Follow-up Suggestions**: The LLM generates 3 contextual follow-up questions displayed as clickable chips in the UI.

---

## 6. Error Handling & Data Resilience

| Layer | Strategy |
|-------|----------|
| **monday.com API** | HTTP 503 with structured error body; retryable. Timeout set at 30 s per request. Pagination cursor handles boards with 500+ items. |
| **Data Cleaning** | Never crashes on bad data. Nulls → 0.0 for numerics, "Unknown" for strings. Every anomaly logged as a `DataQualityWarning` with field name, issue description, affected count, and severity. |
| **Groq / LLM** | HTTP 502 on timeout or model error. Intent extraction uses fallback `GENERAL` type with 0.0 confidence if parsing fails. Clarification flow returned when confidence < 0.5. |
| **Cache** | Lazy expiry on read + manual `purge_expired()`. Cache miss is transparent — falls through to live fetch. Response cache stores `model_copy()` to avoid mutation. |
| **Global** | FastAPI `exception_handler(Exception)` catches unhandled errors; returns 500 with safe message in production (stack trace only when `DEBUG=true`). |

---

## 7. Future Improvements

| Priority | Improvement | Impact |
|----------|------------|--------|
| 🔴 High | **Redis cache** — Replace in-memory TTL cache with Redis for horizontal scaling and crash persistence. | Enables multi-instance deployment behind a load balancer. |
| 🔴 High | **Authentication & RBAC** — JWT tokens, API key management, role-based access (Viewer / Analyst / Admin). | Required for any multi-user deployment. |
| 🟡 Medium | **Analytics dashboard** — Interactive charts (Recharts / Chart.js) for pipeline funnel, sector heatmap, collection trend. | Visual layer dramatically improves founder experience. |
| 🟡 Medium | **Streaming responses** — SSE / WebSocket for token-by-token LLM output. | Reduces perceived latency from ~10 s to <1 s first-token. |
| 🟡 Medium | **Monitoring & observability** — Sentry for error tracking, Prometheus metrics, Grafana dashboards. | Production readiness. |
| 🟢 Low | **Multi-board discovery** — Auto-detect boards and columns at startup instead of hardcoding IDs. | Makes the agent reusable across monday.com accounts. |
| 🟢 Low | **Prompt evaluation suite** — Golden-set of 50 questions with expected outputs; automated regression testing. | Guards against prompt drift across model updates. |
| 🟢 Low | **Webhook-driven cache invalidation** — monday.com webhooks to bust cache on board changes instead of TTL. | Near-real-time data freshness without polling. |

---

*End of Decision Log*
