# GHCR Deploy Flow Refresh

1. Replaced the legacy per-service GitHub Actions jobs with a matrix-based workflow that builds `api`, `web`, and `bot`, publishes `:main`, `:<short-sha>`, and optional tag images, and performs a FastAPI route guard for `/briefs/upload` before pushing.
2. Removed the obsolete `.github/workflows/miniapp-images.yml` workflow to prevent duplicate image builds and conflicts with the new tagging rules.
3. Refined the baked Nginx config in `apps/miniapp-web/nginx/default.conf` so `/briefs/*` and `/api/briefs/*` always proxy to `api:8080/briefs/` with buffering disabled and long timeouts.
4. Added `scripts/miniapp-deploy.sh` to provide a deterministic `docker compose` pull + up flow for `web` and `api`, with `--all` support for including the bot.
5. Documented the deploy procedure, remote PowerShell invocation, and smoke tests in `DEPLOY.md`.

