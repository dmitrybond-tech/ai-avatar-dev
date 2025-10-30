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

