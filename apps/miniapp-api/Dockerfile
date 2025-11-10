FROM python:3.12.6-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# System deps for healthcheck tool
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm -f /tmp/requirements.txt

# Copy service source into staging directory
COPY . /app/src

# Ensure import-friendly aliases
RUN mkdir -p apps && \
    rm -rf apps/miniapp_api && \
    mv src apps/miniapp_api && \
    touch apps/__init__.py && \
    touch apps/miniapp_api/__init__.py

EXPOSE 8000

ENV PYTHONPATH=/app

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -fsS http://127.0.0.1:8000/api/healthz || exit 1

CMD ["uvicorn","apps.miniapp_api.main:app","--host","0.0.0.0","--port","8000"]


