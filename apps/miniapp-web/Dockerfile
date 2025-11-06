## -------- Build stage: Vite SPA build --------
FROM node:20.14.0-alpine AS build

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

# Copy built SPA assets
COPY --from=build /app/dist/ /usr/share/nginx/html/

# Provide nginx config inline as required
RUN set -eux; \
    cat > /etc/nginx/conf.d/default.conf <<'NGINXCONF'
server {
  listen 8080;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;

  client_max_body_size 64m;

  location /assets/ {
    expires 1y;
    add_header Cache-Control "public, max-age=31536000, immutable";
    try_files $uri =404;
  }

  location / {
    try_files $uri /index.html;
  }

  # Proxy client telemetry to API service
  location = /client-log {
    proxy_pass http://api:8080/client-log;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  # Proxy brief uploads (and any other /briefs/* endpoints) to API
  location /briefs/ {
    proxy_pass http://api:8080/briefs/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
NGINXCONF

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD wget -qO- http://127.0.0.1:8080/ >/dev/null 2>&1 || exit 1



