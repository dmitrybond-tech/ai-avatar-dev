# Miniapp Production Runbook

1. **Build images**
   - Trigger the `Build Miniapp Images` GitHub Action on `main` (runs automatically on push or manually via *Run workflow*).
   - The workflow builds `ghcr.io/dmitrybond-tech/ai-avatar-miniapp-api` and `...-web` for `linux/amd64` with `VITE_API_BASE_URL=/api`.
   - It pushes `:main` and `:<shortsha>-<UTC>` tags and writes the immutable digests to the workflow summary.

2. **Publish tags for deploy**
   - Record the digest reported for each image (e.g. `ghcr.io/...-api@sha256:...`).
   - Optionally update release notes or deployment ticket with the digests for traceability.

3. **Deploy**
   - On the target host, export `IMAGE_API`, `IMAGE_WEB`, and `IMAGE_TAG` (if overriding) to point at the GHCR tags or digests you just built.
   - From `infra/compose/`, run `scripts/miniapp-deploy.sh` (pass `--all` to include the bot service). The script pulls the new tags and recreates the services with health-aware dependencies.

4. **Smoke tests (via Caddy)**
   - `curl -fsS https://miniapp.dmitrybond.tech/api/healthz`
   - `curl -fsS -X POST https://miniapp.dmitrybond.tech/api/ask -H "content-type: application/json" -d '{"text":"ping","lang":"en"}'`
   - `curl -fsS -X POST "https://miniapp.dmitrybond.tech/api/export/telegram?dryRun=true"`
   - Open the Miniapp UI and confirm “What I can do” / Task status load (either Notion data or CSV fallback) without error banners.

5. **Rollback (if needed)**
   - Re-run the deploy script with the previous known-good tags or digests.
   - Healthchecks keep Nginx/Web waiting for the API, so services return 200s during warmup.

