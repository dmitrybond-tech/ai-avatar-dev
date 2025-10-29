FROM python:3.12.6-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies
COPY apps/miniapp-bot/requirements.txt apps/miniapp-bot/requirements.txt
RUN pip install --no-cache-dir -r apps/miniapp-bot/requirements.txt

# Copy all sources (keeps repo structure intact)
COPY . .

# Do not bake secrets. Read TELEGRAM_TOKEN and others at runtime.
CMD ["python","-u","apps/miniapp-bot/main.py"]

# syntax=docker/dockerfile:1.4
FROM python:3.12-slim

WORKDIR /app

# Install CA certificates for SSL verification
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Configurable PyPI index (allows custom mirrors for network-restricted environments)
ARG PIP_INDEX_URL=https://pypi.org/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

# Copy requirements and install dependencies with retries and timeout
COPY requirements.txt .
RUN python -m pip install -U pip \
 && pip install --no-cache-dir -r requirements.txt \
    -i ${PIP_INDEX_URL} \
    --retries 5 \
    --timeout 60

# Copy application code
COPY bot.py .

# Run the bot
CMD ["python", "bot.py"]

