# MiniApp FRONT (VPS:15173 -> VM:5173)
miniapp.dmitrybond.tech {
    encode zstd gzip
    header @static Cache-Control "public, max-age=600"
    @api {
        path /api/*
    }
    reverse_proxy @api http://127.0.0.1:18080
    reverse_proxy http://127.0.0.1:15173
}

# MiniApp API (VPS:18080 -> VM:8080)
api-miniapp.dmitrybond.tech {
    encode zstd gzip
    reverse_proxy 127.0.0.1:18080
}

