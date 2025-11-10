1. Hardened Miniapp web proxy: `/api` traffic now resolves via Docker DNS with extended timeouts, prefix preservation, and SPA fallback only, ensuring longer-running LLM calls do not 502.
2. Normalized FastAPI service under `/api/*`, removed root aliases, added friendly degraded health payloads, and logged concise Notion secret status at startup.
3. Enabled health-aware orchestration across compose overlays with curl/wget checks, removed host port exposure for API, and enforced `.env.miniapp` as the single source for required Notion IDs.
4. Added reproducible GHCR build workflow tagging `:main` and `:<shortsha>-<UTC>` for API/Web images, with digest reporting for deploy pipelines.
5. Documented production runbook and `.env` expectations so operators deploy from pinned images and run standardized post-deploy smoke tests.

