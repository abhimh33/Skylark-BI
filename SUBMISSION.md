# SkyLark BI Agent — Submission

---

## Project Summary (< 300 words)

SkyLark BI Agent is a full-stack Business Intelligence platform that transforms raw monday.com board data into actionable executive insights through natural language conversation.

The system connects to live Deals (346 items) and Work Orders (176 items) boards via monday.com's GraphQL API, ingesting real-world data that includes nulls, inconsistent formatting, and mixed-case categorical values. A dedicated data-cleaning layer normalizes every record and emits structured quality warnings — ensuring the founder always knows exactly how much of the data is trustworthy.

Seven deterministic business metrics are computed on each request: pipeline value, sector breakdown, deal win/loss ratio, revenue by sector, invoiced vs collected, collection efficiency, and pipeline-to-revenue ratio. A composite "Leadership Update" runs all seven simultaneously to produce a structured executive briefing with key numbers, attention items, wins, and recommended actions.

Groq's `llama-3.3-70b-versatile` model powers three AI capabilities: intent extraction (classifying free-text questions into metric types), executive summary generation (converting raw metrics into human-readable narratives with INR currency formatting), and contextual follow-up suggestions displayed as clickable chips in the chat UI.

Performance is optimized through a thread-safe in-memory TTL caching layer — monday.com data is cached for 3 minutes and AI responses for 5 minutes, reducing repeat-query latency from ~11 seconds to <1 ms. Every response is labelled `source: cache` or `source: live` for full transparency.

The backend (FastAPI) is deployed on Render; the frontend (React + Vite) on Vercel. The architecture follows strict separation of concerns — monday client, data cleaner, metrics engine, AI service, and cache are each isolated modules with clean interfaces, making the system maintainable, testable, and production-extensible.

**Live**: [https://skylark-bi.vercel.app](https://skylark-bi.vercel.app)  
**API**: [https://skylark-bi.onrender.com/docs](https://skylark-bi.onrender.com/docs)

---

## Source ZIP Submission Checklist

### Include

- [x] `backend/` — All Python source code under `app/`
- [x] `backend/requirements.txt`
- [x] `backend/.env.example` (template, **not** actual `.env`)
- [x] `backend/README.md`
- [x] `frontend/src/` — All React source code
- [x] `frontend/package.json` and `package-lock.json`
- [x] `frontend/index.html`
- [x] `frontend/vite.config.js`
- [x] `frontend/vercel.json`
- [x] `frontend/public/` — Static assets
- [x] `render.yaml` — Render deployment blueprint
- [x] `README.md` — Root project README
- [x] `DECISION_LOG.md` — Architecture decisions & trade-offs
- [x] `.gitignore`

### Exclude

- [ ] `backend/.env` — Contains live API keys (secrets)
- [ ] `backend/__pycache__/` — Python bytecode
- [ ] `.venv/` or `venv/` — Virtual environment (large)
- [ ] `frontend/node_modules/` — npm dependencies (large)
- [ ] `frontend/dist/` — Build output
- [ ] `.git/` — Git history

### Directory Structure for ZIP

```
Skylark-BI/
├── README.md
├── DECISION_LOG.md
├── SUBMISSION.md
├── render.yaml
├── .gitignore
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── README.md
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── cache.py
│       ├── dependencies.py
│       ├── models/schemas.py
│       ├── monday_client/{client,queries}.py
│       ├── data_cleaner/cleaner.py
│       ├── business_logic/metrics.py
│       ├── ai_service/{service,prompts}.py
│       └── routers/ask.py
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── vercel.json
    ├── index.html
    └── src/
        ├── App.jsx
        ├── components/*.{jsx,css}
        ├── hooks/useChat.js
        └── services/api.js
```

### Quick ZIP Command (PowerShell)

```powershell
cd D:\SkyLark-project
Compress-Archive -Path backend, frontend, render.yaml, README.md, DECISION_LOG.md, SUBMISSION.md, .gitignore -DestinationPath Skylark-BI-Submission.zip -Force
```

---

*End of Submission Document*
