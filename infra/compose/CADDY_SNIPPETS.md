Add this block to /etc/caddy/Caddyfile on the VPS and reload Caddy:

```
miniapp.dmitrybond.tech {
  encode gzip zstd

  @api path /healthz /rules* /cal/* /cal* /api*
  handle @api {
    reverse_proxy localhost:8080
  }

  handle {
    reverse_proxy localhost:5173
  }

  log
}
```

