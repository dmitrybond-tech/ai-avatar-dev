# Website Dockerfile - Multi-stage build
FROM node:20-alpine AS builder

WORKDIR /workspace

# Install git (required by some pnpm dependencies)
RUN apk add --no-cache git

# Copy workspace files from monorepo root
COPY package.json pnpm-workspace.yaml ./
COPY packages ./packages
COPY apps/website ./apps/website

# Install pnpm via npm (network-robust, avoids Corepack DNS issues)
RUN npm config set fund false \
 && npm config set audit false \
 && npm i -g pnpm@8.15.0
# Optional: Use mirror if default registry is flaky
# RUN npm config set registry https://registry.npmmirror.com && npm i -g pnpm@8.15.0

# Install dependencies (no lockfile yet); fallback to npm if pnpm workspace не настроен
RUN (pnpm -v >/dev/null 2>&1 && pnpm install --no-frozen-lockfile) \
    || (cd apps/website && (npm ci || npm install))

# Build args for PUBLIC_* env vars (with safe defaults)
ARG PUBLIC_API_BASE_URL=http://localhost:8080
ENV PUBLIC_API_BASE_URL=$PUBLIC_API_BASE_URL

# Build website (from app dir)
WORKDIR /workspace/apps/website
RUN (pnpm run build) || (npx astro build || npm run build)

# Production stage
FROM node:20-alpine

WORKDIR /app

# Install serve to host static files
RUN npm install -g serve@14.2.3

# Copy built files
COPY --from=builder /workspace/apps/website/dist /app/dist

EXPOSE 3000

# Serve static files
CMD ["serve", "-s", "dist", "-l", "3000"]

