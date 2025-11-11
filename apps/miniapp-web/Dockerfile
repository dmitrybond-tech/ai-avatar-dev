## -------- Build stage: Vite SPA build --------
FROM node:20.14.0-alpine AS build

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /app

# Copy app sources (workflow will set context to apps/miniapp-web)
COPY . .

# Detect lockfile and install deterministically inside the app folder
RUN set -eux; \
    apk add --no-cache git bash; \
    if [ -f pnpm-lock.yaml ]; then \
      corepack enable; corepack prepare pnpm@latest --activate; \
      pnpm install --frozen-lockfile; \
      pnpm run build; \
    elif [ -f yarn.lock ]; then \
      corepack enable; corepack prepare yarn@1.22.22 --activate; \
      yarn install --frozen-lockfile; \
      yarn build; \
    elif [ -f package-lock.json ]; then \
      npm ci --no-audit --no-fund; \
      npm run build; \
    else \
      echo "No lockfile found; falling back to npm install"; \
      npm install --no-audit --no-fund; \
      npm run build; \
    fi

## -------- Runtime stage: nginx serving on 8080 --------
FROM nginx:1.27.2-alpine AS runtime

WORKDIR /usr/share/nginx/html

# Required for compose healthchecks
RUN apk add --no-cache curl

# Copy built SPA assets
COPY --from=build /app/dist/ /usr/share/nginx/html/

# Copy nginx config from repo (persistent)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD wget -qO- http://127.0.0.1:8080/ >/dev/null 2>&1 || exit 1



