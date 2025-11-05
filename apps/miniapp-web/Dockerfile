## -------- Build stage: Vite SPA build --------
FROM node:20.14.0-alpine AS build

WORKDIR /app

# Bring in repo (monorepo) contents; CI will set context to repository root
# so we can respect the existing package manager and workspaces
COPY . .

# Detect lockfile and install deterministically
RUN set -eux; \
    apk add --no-cache git bash; \
    if [ -f pnpm-lock.yaml ]; then \
      corepack enable; corepack prepare pnpm@latest --activate; \
      pnpm install --frozen-lockfile; \
      pnpm -C apps/miniapp-web run build; \
    elif [ -f yarn.lock ]; then \
      corepack enable; corepack prepare yarn@1.22.22 --activate; \
      yarn install --frozen-lockfile; \
      yarn --cwd apps/miniapp-web build; \
    elif [ -f package-lock.json ]; then \
      npm ci --no-audit --no-fund; \
      npm --prefix apps/miniapp-web run build; \
    else \
      echo "No lockfile found; falling back to npm install"; \
      npm install --no-audit --no-fund; \
      npm --prefix apps/miniapp-web run build; \
    fi

## -------- Runtime stage: nginx serving on 8080 --------
FROM nginx:1.27.2-alpine AS runtime

WORKDIR /usr/share/nginx/html

# Copy built SPA assets
COPY --from=build /app/apps/miniapp-web/dist/ /usr/share/nginx/html/

# Provide nginx config inline as required
RUN set -eux; \
    cat > /etc/nginx/conf.d/default.conf <<'NGINXCONF'
server {
  listen 8080;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;

  location /assets/ {
    expires 1y;
    add_header Cache-Control "public, max-age=31536000, immutable";
    try_files $uri =404;
  }

  location / {
    try_files $uri /index.html;
  }
}
NGINXCONF

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD wget -qO- http://127.0.0.1:8080/ >/dev/null 2>&1 || exit 1



