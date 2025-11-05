FROM python:3.12.6-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# System deps for healthcheck tool
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY apps/miniapp-api/requirements.txt apps/miniapp-api/requirements.txt
RUN pip install --no-cache-dir -r apps/miniapp-api/requirements.txt

# Copy all sources (keeps repo structure intact)
COPY . .

# Ensure underscore module is available and overlay explicit underscore package if present
COPY apps/miniapp_api ./apps/miniapp_api

# Create import-friendly alias to support module path "apps.miniapp_api"
RUN mkdir -p apps \
    && cp -r apps/miniapp-api apps/miniapp_api || true \
    && touch apps/__init__.py \
    && touch apps/miniapp_api/__init__.py

EXPOSE 8080

ENV PYTHONPATH=/app

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -fsS http://127.0.0.1:8080/healthz || exit 1

CMD ["uvicorn","apps.miniapp_api.main:app","--host","0.0.0.0","--port","8080"]


