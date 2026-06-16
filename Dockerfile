# Zero-to-Synced — single full-stack image.
#   Stage 1 builds the React frontend.
#   Stage 2 runs the FastAPI backend, which serves that built frontend as a
#   same-origin SPA and spawns `python src/fivetran-mcp/server.py` over stdio.

# ── Stage 1: build the frontend ───────────────────────────────────────────
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# VITE_API_BASE is left empty → the app calls the same origin it's served from.
RUN npm run build

# ── Stage 2: backend + bundled frontend ───────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install deps first so this layer is cached across code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App source + the fivetran-mcp submodule (server.py + openapi defs).
COPY . .

# Drop the built SPA where app.py looks for it (frontend/dist).
COPY --from=frontend /fe/dist ./frontend/dist

# Gemini Developer API (API key), not Vertex/ADC. Real values come from
# `fly secrets` (GOOGLE_API_KEY, DATABASE_URL, JWT_SECRET, ...).
ENV GOOGLE_GENAI_USE_VERTEXAI=false \
    PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT}"]
