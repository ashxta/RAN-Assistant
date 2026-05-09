# ─────────────────────────────────────────────
# Stage 1: Build React frontend
# ─────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies first (better layer caching)
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps

# Copy source and build
COPY frontend ./
RUN npm run build

# ─────────────────────────────────────────────
# Stage 2: Python backend + built frontend
# ─────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by sentence-transformers / FAISS
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source (includes telecom_docs if it exists)
COPY backend ./backend

# Copy built React app from Stage 1
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Render injects $PORT at runtime; default to 8000 locally
EXPOSE 8000

# Use shell form so $PORT is expanded at runtime
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
CMD ["sh", "-c", "exec gunicorn backend.app:app --bind 0.0.0.0:${PORT} --workers 1 --timeout 120"]
