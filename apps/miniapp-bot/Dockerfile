FROM python:3.12.6-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm -f /tmp/requirements.txt

# Copy bot sources into both legacy (hyphen) and package (underscore) layouts
COPY . /app/apps/miniapp-bot
COPY . /app/apps/miniapp_bot

# Do not bake secrets. Read TELEGRAM_TOKEN and others at runtime.
CMD ["python", "-m", "apps.miniapp_bot.main"]

