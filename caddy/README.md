# Caddy reverse proxy (local development)

This project includes a `Caddyfile` in the `caddy/` directory for local development. It proxies requests as follows:

- `/` → Frontend dev server (SvelteKit / Vite) on `127.0.0.1:5173`
- `/api/*` → Rust Axum backend on `127.0.0.1:8000`
- `/inference` → Python FastAPI inference service on `127.0.0.1:8001` (internal)

Run Caddy locally (requires Caddy installed):

```bash
# from repository root
caddy run --config caddy/Caddyfile --adapter caddyfile
```

Notes:
- The `Caddyfile` in `caddy/` is configured for local development using `localhost` as the site label. Change this if you want to use a custom local domain.
- The `/inference` route forwards to the inference service; for production you should restrict access to this path or make it internal-only behind a service mesh or private network.
- If your frontend dev server runs on a different port, update the `Caddyfile` accordingly.

Troubleshooting:
- If `caddy run` fails due to port binding (permission or port in use), run with a different hostname/port or use `sudo` only if necessary.
