# Multi-stage build
FROM node:24-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps
COPY frontend .
RUN npm run build

# Python backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Copy backend
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend ./backend
COPY backend/telecom_docs ./backend/telecom_docs

# Pre-download the sentence transformer model at build time
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Expose port
EXPOSE 10000

# Start app
CMD ["sh", "-c", "exec gunicorn backend.app:app --bind 0.0.0.0:${PORT:-10000} --workers 1 --timeout 120"]
