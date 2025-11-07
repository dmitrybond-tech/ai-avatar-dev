diff --git a/.github/workflows/miniapp-images.yml b/.github/workflows/miniapp-images.yml
deleted file mode 100644
index a7089d1..0000000
--- a/.github/workflows/miniapp-images.yml
+++ /dev/null
@@ -1,181 +0,0 @@
-name: MiniApp Images — Build & Push (GHCR)
-
-on:
-  push:
-    branches: [ "main" ]
-  workflow_dispatch: {}
-
-jobs:
-  web:
-    name: Build & Push Web
-    runs-on: ubuntu-24.04
-    concurrency:
-      group: miniapp-web-${{ github.ref }}
-      cancel-in-progress: false
-    permissions:
-      contents: read
-      packages: write
-    env:
-      IMAGE: ghcr.io/dmitrybond-tech/ai-avatar-miniapp-web
-    steps:
-      - name: Checkout
-        uses: actions/checkout@v4.2.2
-
-      - name: Set up Docker Buildx
-        uses: docker/setup-buildx-action@v3.7.1
-
-      - name: Login to GHCR
-        uses: docker/login-action@v3.3.0
-        with:
-          registry: ghcr.io
-          username: ${{ github.actor }}
-          password: ${{ secrets.GITHUB_TOKEN }}
-
-      - name: Build and Push
-        uses: docker/build-push-action@v6.9.0
-        with:
-          context: ./apps/miniapp-web
-          file: ./apps/miniapp-web/Dockerfile
-          push: true
-          tags: |
-            ${{ env.IMAGE }}:sha-${{ github.sha }}
-            ${{ env.IMAGE }}:main
-          labels: |
-            org.opencontainers.image.source=${{ github.repository }}
-            org.opencontainers.image.revision=${{ github.sha }}
-            org.opencontainers.image.title=miniapp-web
-          provenance: false
-          sbom: false
-
-      - name: Export image digest
-        run: |
-          mkdir -p dist
-          echo "${{ env.IMAGE }}@$(docker buildx imagetools inspect ${{ env.IMAGE }}:sha-${{ github.sha }} --format '{{json .Manifest.Digest}}' | sed 's/["}]//g')" > dist/image-digest-web.txt
-
-      - name: Upload artifact
-        uses: actions/upload-artifact@v4.4.3
-        with:
-          name: miniapp-web-image-digest
-          path: dist/image-digest-web.txt
-
-  api:
-    name: Build & Push API
-    runs-on: ubuntu-24.04
-    concurrency:
-      group: miniapp-api-${{ github.ref }}
-      cancel-in-progress: false
-    permissions:
-      contents: read
-      packages: write
-    env:
-      IMAGE: ghcr.io/dmitrybond-tech/ai-avatar-miniapp-api
-    steps:
-      - name: Checkout
-        uses: actions/checkout@v4.2.2
-
-      - name: Set up Docker Buildx
-        uses: docker/setup-buildx-action@v3.7.1
-
-      - name: Login to GHCR
-        uses: docker/login-action@v3.3.0
-        with:
-          registry: ghcr.io
-          username: ${{ github.actor }}
-          password: ${{ secrets.GITHUB_TOKEN }}
-
-      - name: Build and Push
-        uses: docker/build-push-action@v6.9.0
-        with:
-          context: .
-          file: ./apps/miniapp-api/Dockerfile
-          push: true
-          tags: |
-            ${{ env.IMAGE }}:sha-${{ github.sha }}
-            ${{ env.IMAGE }}:main
-          labels: |
-            org.opencontainers.image.source=${{ github.repository }}
-            org.opencontainers.image.revision=${{ github.sha }}
-            org.opencontainers.image.title=miniapp-api
-          provenance: false
-          sbom: false
-
-      - name: Export image digest
-        run: |
-          mkdir -p dist
-          echo "${{ env.IMAGE }}@$(docker buildx imagetools inspect ${{ env.IMAGE }}:sha-${{ github.sha }} --format '{{json .Manifest.Digest}}' | sed 's/["}]//g')" > dist/image-digest-api.txt
-
-      - name: Upload artifact
-        uses: actions/upload-artifact@v4.4.3
-        with:
-          name: miniapp-api-image-digest
-          path: dist/image-digest-api.txt
-
-  bot:
-    name: Build & Push Bot
-    runs-on: ubuntu-24.04
-    concurrency:
-      group: miniapp-bot-${{ github.ref }}
-      cancel-in-progress: false
-    permissions:
-      contents: read
-      packages: write
-    env:
-      IMAGE: ghcr.io/dmitrybond-tech/ai-avatar-miniapp-bot
-    steps:
-      - name: Checkout
-        uses: actions/checkout@v4.2.2
-
-      - name: Set up Docker Buildx
-        uses: docker/setup-buildx-action@v3.7.1
-
-      - name: Login to GHCR
-        uses: docker/login-action@v3.3.0
-        with:
-          registry: ghcr.io
-          username: ${{ github.actor }}
-          password: ${{ secrets.GITHUB_TOKEN }}
-
-      - name: Build and Push (apps/miniapp-bot if exists)
-        if: ${{ hashFiles('apps/miniapp-bot/Dockerfile') != '' }}
-        uses: docker/build-push-action@v6.9.0
-        with:
-          context: .
-          file: ./apps/miniapp-bot/Dockerfile
-          push: true
-          tags: |
-            ${{ env.IMAGE }}:sha-${{ github.sha }}
-            ${{ env.IMAGE }}:main
-          labels: |
-            org.opencontainers.image.source=${{ github.repository }}
-            org.opencontainers.image.revision=${{ github.sha }}
-            org.opencontainers.image.title=miniapp-bot
-          provenance: false
-          sbom: false
-
-      - name: Build and Push (apps/miniapp_bot fallback)
-        if: ${{ hashFiles('apps/miniapp-bot/Dockerfile') == '' }}
-        uses: docker/build-push-action@v6.9.0
-        with:
-          context: .
-          file: ./apps/miniapp_bot/Dockerfile
-          push: true
-          tags: |
-            ${{ env.IMAGE }}:sha-${{ github.sha }}
-            ${{ env.IMAGE }}:main
-          labels: |
-            org.opencontainers.image.source=${{ github.repository }}
-            org.opencontainers.image.revision=${{ github.sha }}
-            org.opencontainers.image.title=miniapp-bot
-          provenance: false
-          sbom: false
-
-      - name: Export image digest
-        run: |
-          mkdir -p dist
-          echo "${{ env.IMAGE }}@$(docker buildx imagetools inspect ${{ env.IMAGE }}:sha-${{ github.sha }} --format '{{json .Manifest.Digest}}' | sed 's/["}]//g')" > dist/image-digest-bot.txt
-
-      - name: Upload artifact
-        uses: actions/upload-artifact@v4.4.3
-        with:
-          name: miniapp-bot-image-digest
-          path: dist/image-digest-bot.txt

diff --git a/.github/workflows/build-miniapp.yml b/.github/workflows/build-miniapp.yml
new file mode 100644
index 0000000..935a30b
--- /dev/null
+++ b/.github/workflows/build-miniapp.yml
@@ -0,0 +1,117 @@
name: Miniapp — Build & Publish

on:
  push:
    branches:
      - main
    tags:
      - "v*.*.*"
  workflow_dispatch:

permissions:
  contents: read
  packages: write

jobs:
  build:
    name: Build ${{ matrix.service }}
    runs-on: ubuntu-24.04
    strategy:
      fail-fast: false
      matrix:
        service: [api, web, bot]
    concurrency:
      group: miniapp-${{ github.ref_name }}-build
      cancel-in-progress: true
    env:
      IMAGE_NAME: ghcr.io/${{ github.repository_owner }}/ai-avatar-miniapp-${{ matrix.service }}
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4.2.2

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3.2.0

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3.7.1

      - name: Log in to GHCR
        uses: docker/login-action@v3.3.0
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Resolve build context
        id: paths
        run: |
          case "${{ matrix.service }}" in
            api)
              echo "context=apps/miniapp-api" >> "$GITHUB_OUTPUT"
              echo "dockerfile=apps/miniapp-api/Dockerfile" >> "$GITHUB_OUTPUT"
              ;;
            web)
              echo "context=apps/miniapp-web" >> "$GITHUB_OUTPUT"
              echo "dockerfile=apps/miniapp-web/Dockerfile" >> "$GITHUB_OUTPUT"
              ;;
            bot)
              echo "context=apps/miniapp-bot" >> "$GITHUB_OUTPUT"
              echo "dockerfile=apps/miniapp-bot/Dockerfile" >> "$GITHUB_OUTPUT"
              ;;
            *)
              echo "Unknown service" >&2
              exit 1
              ;;
          esac

      - name: Verify briefs upload route exists
        if: ${{ matrix.service == 'api' }}
        run: |
          python - <<'PY'
          from fastapi.routing import APIRoute
          try:
              from apps.miniapp_api.main import app
          except Exception as exc:
              raise SystemExit(f"Failed to import FastAPI app: {exc}")

          paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
          required = "/briefs/upload"
          if required not in paths:
              listing = "\n".join(sorted(paths))
              raise SystemExit(f"Missing required route {required}. Registered routes:\n{listing}")
          PY

      - name: Compute image tags
        id: meta
        env:
          IMAGE_NAME: ${{ env.IMAGE_NAME }}
        run: |
          short_sha="${GITHUB_SHA::7}"
          tags="${IMAGE_NAME}:main\n${IMAGE_NAME}:${short_sha}"
          if [ "${GITHUB_REF_TYPE}" = "tag" ]; then
            tags="${tags}\n${IMAGE_NAME}:${GITHUB_REF_NAME}"
          fi
          {
            echo "tags<<'EOF'"
            echo "$tags"
            echo "EOF"
          } >> "$GITHUB_OUTPUT"

          created=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
          echo "created=${created}" >> "$GITHUB_OUTPUT"

      - name: Build and push image
        uses: docker/build-push-action@v6.9.0
        with:
          context: ${{ steps.paths.outputs.context }}
          file: ${{ steps.paths.outputs.dockerfile }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          labels: |
            org.opencontainers.image.created=${{ steps.meta.outputs.created }}
            org.opencontainers.image.revision=${{ github.sha }}
            org.opencontainers.image.source=${{ github.repository }}
            org.opencontainers.image.version=${{ github.ref_name }}

diff --git a/apps/miniapp-web/nginx/default.conf b/apps/miniapp-web/nginx/default.conf
index edbdc12..5a6a2c8 100644
--- a/apps/miniapp-web/nginx/default.conf
+++ b/apps/miniapp-web/nginx/default.conf
@@ -27,27 +27,25 @@ server {
   }

   location /briefs/ {
-    client_max_body_size 64m;
     proxy_request_buffering off;
     proxy_pass http://api:8080/briefs/;
+    proxy_read_timeout 300s;
+    proxy_connect_timeout 60s;
     proxy_set_header Host $host;
     proxy_set_header X-Real-IP $remote_addr;
     proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
     proxy_set_header X-Forwarded-Proto $scheme;
-    proxy_read_timeout 300s;
-    proxy_connect_timeout 60s;
   }

   location /api/briefs/ {
-    client_max_body_size 64m;
     proxy_request_buffering off;
     proxy_pass http://api:8080/briefs/;
+    proxy_read_timeout 300s;
+    proxy_connect_timeout 60s;
     proxy_set_header Host $host;
     proxy_set_header X-Real-IP $remote_addr;
     proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
     proxy_set_header X-Forwarded-Proto $scheme;
-    proxy_read_timeout 300s;
-    proxy_connect_timeout 60s;
   }

   location /assets/ {

diff --git a/scripts/miniapp-deploy.sh b/scripts/miniapp-deploy.sh
new file mode 100755
index 0000000..3e11eda
--- /dev/null
+++ b/scripts/miniapp-deploy.sh
@@ -0,0 +1,24 @@
#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
COMPOSE_DIR=$(cd -- "${SCRIPT_DIR}/../infra/compose" && pwd)

services=(web api)

if [[ "${1:-}" == "--all" ]]; then
  services=(web api bot)
fi

cd "${COMPOSE_DIR}"

compose_cmd=(
  docker compose --env-file .env.miniapp \
    -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml \
    -f miniapp.notion.override.yml -f miniapp.final.override.yml
)

"${compose_cmd[@]}" pull "${services[@]}"
"${compose_cmd[@]}" up -d "${services[@]}"

diff --git a/DEPLOY.md b/DEPLOY.md
new file mode 100644
index 0000000..f3fb2d3
--- /dev/null
+++ b/DEPLOY.md
@@ -0,0 +1,45 @@
# Miniapp Deploy Notes

1. Ensure the production host has the images published from the `main` branch (or tagged release) in GitHub Container Registry:
   - `ghcr.io/<owner>/ai-avatar-miniapp-{api,web,bot}:main`
   - `ghcr.io/<owner>/ai-avatar-miniapp-{api,web,bot}:<short-sha>`
   - Tagged pushes add `:vX.Y.Z`.
2. On the host, run `scripts/miniapp-deploy.sh` to pull and restart the web and api services, or pass `--all` to include the bot.

```bash
cd /srv/ai-avatar
./scripts/miniapp-deploy.sh
# include the bot as well
./scripts/miniapp-deploy.sh --all
```

The script issues:

```bash
docker compose --env-file .env.miniapp \
  -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml \
  -f miniapp.notion.override.yml -f miniapp.final.override.yml \
  pull web api && \
docker compose --env-file .env.miniapp \
  -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml \
  -f miniapp.notion.override.yml -f miniapp.final.override.yml \
  up -d web api
```

3. Operators can run the same flow remotely from Windows PowerShell (note escaped newlines):

```powershell
ssh deploy@<host> 'cd /srv/ai-avatar/infra/compose;
  docker compose --env-file .env.miniapp `
    -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml `
    -f miniapp.notion.override.yml -f miniapp.final.override.yml pull web api;
  docker compose --env-file .env.miniapp `
    -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml `
    -f miniapp.notion.override.yml -f miniapp.final.override.yml up -d web api'
```

4. Post-deploy smoke tests:
   - POST `https://miniapp.dmitrybond.tech/briefs/upload` with a small file and expect `{"ok":true,"dedup":false,...}`.
   - Repeat the same payload; expect `dedup:true` with identical `request_id`.
   - Verify the Telegram admin receives the document and Notion Backlog gets a new page.

