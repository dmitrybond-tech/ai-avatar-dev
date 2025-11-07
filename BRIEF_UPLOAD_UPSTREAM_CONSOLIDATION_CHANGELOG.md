# Brief Upload Upstream Consolidation Changelog

## Summary

- Unified nginx upstream for `/briefs/*` and `/api/briefs/*`, enforcing `client_max_body_size 64m` and disabling buffering for streaming uploads.
- Added FastAPI briefs router with idempotency (Redis/FS), `/briefs/upload` + alias, file persistence under `/data/uploads/{request_id}`.
- Implemented Telegram + Notion helpers and upload flow response schema `{ok, request_id, notion_page_id, dedup}` with no PII logging.
- Updated local compose override to build the miniapp API from `apps/miniapp-api` and pinned required dependencies (`redis`, `ulid-py`).

## Testing

- `python -m compileall apps/miniapp_api`


