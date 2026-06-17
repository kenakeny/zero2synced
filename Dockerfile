# Stage 1: build frontend
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# Stage 2: backend + bundled frontend
FROM python:3.12.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# needed to fetch the submodule
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .
RUN git submodule update --init --recursive

COPY --from=frontend /fe/dist ./frontend/dist

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT}"]