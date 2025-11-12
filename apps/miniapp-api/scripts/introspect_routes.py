#!/usr/bin/env python3
"""Introspect FastAPI routes to verify skills endpoints."""
from apps.miniapp_api.main import app

skills_routes = sorted(set([r.path for r in app.routes if 'skills' in r.path]))
print("Skills-related routes:")
for route in skills_routes:
    methods = [m for m in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'] if m in [r.methods for r in app.routes if r.path == route][0]]
    print(f"  {route} ({', '.join(methods)})")

