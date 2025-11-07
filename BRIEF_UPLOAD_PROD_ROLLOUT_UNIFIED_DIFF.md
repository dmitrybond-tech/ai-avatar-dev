```diff
diff --git a/infra/compose/miniapp.final.override.yml b/infra/compose/miniapp.final.override.yml
index dc4fb7d..f7fb44b 100644
--- a/infra/compose/miniapp.final.override.yml
+++ b/infra/compose/miniapp.final.override.yml
@@ -21,7 +21,7 @@ services:
       TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:-}
       TELEGRAM_ADMIN_CHAT_ID: ${TELEGRAM_ADMIN_CHAT_ID:-}
       UPLOAD_DIR: /app/uploads/briefs
-      MAX_UPLOAD_MB: ${MAX_UPLOAD_MB:-25}
+      MAX_UPLOAD_MB: ${MAX_UPLOAD_MB:-64}
       ALLOWED_EXT: ${ALLOWED_EXT:-pdf,doc,docx,txt,png,jpg,jpeg,zip}

     volumes:

diff --git a/infra/compose/miniapp.localbuild.override.yml b/infra/compose/miniapp.localbuild.override.yml
new file mode 100644
index 0000000..cc2c297
--- /dev/null
+++ b/infra/compose/miniapp.localbuild.override.yml
@@
+services:
+  api:
+    build:
+      context: ../../apps/api
+      dockerfile: Dockerfile
+    image: local/miniapp-api:dev
+
+  web:
+    build:
+      context: ../../apps/miniapp-web
+      dockerfile: Dockerfile
+    image: local/miniapp-web:dev
```

