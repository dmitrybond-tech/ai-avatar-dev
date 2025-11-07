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

