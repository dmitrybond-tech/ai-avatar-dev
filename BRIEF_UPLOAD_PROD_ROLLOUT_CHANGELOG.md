# Brief Upload Prod Rollout - Changelog

1. `apps/miniapp-web/nginx/default.conf` – confirmed single regex location for `/briefs/` and `/api/briefs/` with `proxy_request_buffering off`, preserved `client_max_body_size 64m`, and ensured `proxy_pass http://api:8080` keeps the upstream URI intact.
2. `infra/compose/miniapp.final.override.yml` – raised the default `MAX_UPLOAD_MB` to 64 so the FastAPI container honours the 64 MB limit expected by nginx and validation logic.
3. `infra/compose/miniapp.localbuild.override.yml` – added build override to allow deterministic local image rebuilds for `api` and `web` services when production compose uses GHCR images.
4. API runtime – verified that `/briefs/upload` and `/api/briefs/upload` routes, Telegram + Notion integrations, and idempotency utilities already match the acceptance criteria; no code changes required beyond env alignment.
5. Frontend runtime – confirmed `/brief` page already performs alias fallback, displays `request_id`, disables resubmits, and keeps iframe auto-resize intact; no changes needed.

