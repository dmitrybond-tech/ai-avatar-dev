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

