# Website Dockerfile - Multi-stage build
FROM node:20-alpine AS builder

WORKDIR /app

# Copy workspace files
COPY package.json pnpm-workspace.yaml /workspace/
COPY packages /workspace/packages
COPY apps/website /workspace/apps/website

WORKDIR /workspace

# Install pnpm
RUN corepack enable && corepack prepare pnpm@8.15.0 --activate

# Install dependencies
RUN pnpm install --frozen-lockfile

# Build website
WORKDIR /workspace/apps/website
RUN pnpm build

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

