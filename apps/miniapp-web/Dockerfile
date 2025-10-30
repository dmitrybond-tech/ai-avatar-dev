# --- Builder stage ---
FROM node:20.16.0-alpine AS build

WORKDIR /app

# Build-time arguments for Vite
ARG VITE_API_BASE_URL
ARG VITE_DEFAULT_LANG

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_DEFAULT_LANG=${VITE_DEFAULT_LANG}

# Install dependencies using lockfile
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Copy the rest of the source and build
COPY . .
RUN npm run build

# --- Runtime stage ---
FROM nginx:1.27.2-alpine

WORKDIR /usr/share/nginx/html

COPY --from=build /app/dist/ .
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1


