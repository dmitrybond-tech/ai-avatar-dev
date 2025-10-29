# --- Builder stage ---
FROM node:20.16.0-alpine AS builder

WORKDIR /app

# Build-time arguments for Vite
ARG VITE_API_BASE_URL
ARG VITE_DEFAULT_LANG

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_DEFAULT_LANG=${VITE_DEFAULT_LANG}

COPY apps/miniapp-web/package.json apps/miniapp-web/package.json
COPY apps/miniapp-web/package-lock.json apps/miniapp-web/package-lock.json 2>/dev/null || true
COPY apps/miniapp-web/ .

# Install deps and build
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi \
    && npm run build

# --- Runtime stage ---
FROM nginx:1.27.2-alpine

WORKDIR /usr/share/nginx/html

COPY --from=builder /app/dist/ .
COPY apps/miniapp-web/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1


