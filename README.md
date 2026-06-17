# Zero-to-Synced

Get your data syncing in minutes — no engineers required.

Zero-to-Synced is an AI agent that talks to everyday business people in plain English and handles the entire Fivetran pipeline setup for them: finding connectors, gathering credentials, creating connections, pruning schemas, and handing off a ready-to-query dataset.

**Live:** https://zero2synced.fly.dev

---

## What it does

You tell it something like _"I want to see my Shopify orders alongside my Stripe revenue"_ and it:

1. Figures out which Fivetran connectors you need
2. Asks for your credentials one source at a time, in plain English
3. Proposes a plan and waits for your go-ahead before touching anything
4. Creates the connections, runs setup tests, and prunes the schema to just the data you care about
5. Hands off a plain-English summary of what's now syncing and what you can do with it

It also accepts CSV / Excel file uploads and can bring them into your destination via an S3 connector alongside your other sources.

---

## Stack

| Layer | Tech |
|---|---|
| Agent | Google ADK + Gemini 3 (`gemini-3-pro-preview`) |
| Data pipelines | Fivetran MCP server (git submodule) |
| Backend | FastAPI + uvicorn, Python 3.12 |
| Auth | JWT (bcrypt passwords, Fernet-encrypted Fivetran keys at rest) |
| Database | Neon (Postgres) — ADK session history + app tables |
| Frontend | React + Vite, served same-origin from FastAPI |
| Deploy | Fly.io (single full-stack Docker image) |

---

## Running locally

### Prerequisites
- Python 3.10+, Node 20+
- A [Neon](https://neon.tech) Postgres database
- A [Gemini API key](https://aistudio.google.com/apikey) from AI Studio
- A Fivetran account with an API key + secret

### 1. Clone with submodule
```sh
git clone --recurse-submodules https://github.com/kenakeny/zero2synced
# or if already cloned:
git submodule update --init --recursive
```

### 2. Configure
```sh
cp .env.example .env
```
Fill in `.env`:
```dotenv
GOOGLE_GENAI_USE_VERTEXAI=false
GOOGLE_API_KEY=your_aistudio_key
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
JWT_SECRET=any_long_random_string
```

### 3. Backend (Terminal 1)
```sh
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
uvicorn src.api.app:app --reload --port 8000
```

### 4. Frontend (Terminal 2)
```sh
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — Vite proxies `/api` to the backend automatically.

---

## Deploying to Fly.io

```sh
# Set secrets (one time)
fly secrets set \
  GOOGLE_API_KEY="your_aistudio_key" \
  DATABASE_URL="postgresql://...?sslmode=require" \
  JWT_SECRET="$(openssl rand -hex 32)" \
  -a zero2synced

# Deploy
fly deploy -a zero2synced
```

See [DEPLOY.md](DEPLOY.md) for full details and optional secrets (`GEMINI_MODEL`, `S3_BUCKET`, `FERNET_KEY`).

---

## How the agent works

Each signed-in user connects their own Fivetran account (API key + secret). Those credentials are encrypted at rest and used to spawn a per-user Fivetran MCP subprocess. The agent talks to Fivetran through that subprocess — so every user's pipelines are fully isolated.

The conversation follows a fixed 7-phase flow: **Understand → Check Destination → Gather Credentials → Propose & Confirm → Build → Prune Schema → Handoff**. The agent will not create or modify anything without an explicit confirmation from the user.

---

## Project structure

```
├── src/
│   ├── agent/
│   │   ├── agent.py          # ADK agent definition (model, tools)
│   │   └── prompts.py        # System prompt / personality
│   ├── api/
│   │   ├── app.py            # FastAPI app, lifespan, static SPA mount
│   │   ├── agent_pool.py     # Per-user agent/runner cache
│   │   ├── auth.py           # JWT helpers
│   │   ├── db.py             # Postgres engine + DDL
│   │   ├── fivetran_store.py # Encrypted credential storage
│   │   ├── ingestion.py      # CSV/Excel parsing + S3 upload
│   │   └── routes/
│   │       ├── auth.py       # /api/auth/signup, login, me
│   │       ├── chat.py       # /api/sessions/{id}/chat (SSE)
│   │       ├── fivetran.py   # /api/fivetran/connect, disconnect
│   │       ├── sessions.py   # /api/sessions CRUD
│   │       └── uploads.py    # /api/sessions/{id}/files
│   └── fivetran-mcp/         # Fivetran MCP server (git submodule)
├── frontend/                 # React + Vite
├── Dockerfile                # Multi-stage: Node builds UI → Python serves everything
├── fly.toml
└── requirements.txt
```
