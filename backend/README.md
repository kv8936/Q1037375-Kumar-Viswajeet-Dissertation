# Backend (Rust + Axum)

This folder contains a minimal Axum backend that exposes `POST /api/chat` and forwards requests to the Python inference service.

Features:
- Accepts multipart/form-data with `scenario` (required), `location` (optional), and `image` (optional).
- Forwards the same fields to the inference service configured by `INFERENCE_URL`.
- Optionally logs interactions to PostgreSQL when `DATABASE_URL` is set.

Quick start

1. Install Rust toolchain (stable) and `cargo`.

2. Copy `.env.example` to `.env` and set values (optional `DATABASE_URL`):

```bash
cp backend/.env.example backend/.env
# edit backend/.env
```

3. Build and run the backend:

```bash
cd backend
cargo run --release
```

By default the server listens on `http://127.0.0.1:8000` and forwards to `INFERENCE_URL` (default `http://127.0.0.1:8001`).

Database setup

Create the `chatbot_logs` table in your Postgres database using the schema below:

```sql
CREATE TABLE chatbot_logs (
  id SERIAL PRIMARY KEY,
  scenario TEXT NOT NULL,
  location TEXT,
  image_uploaded BOOLEAN DEFAULT FALSE,
  image_caption TEXT,
  final_model_input TEXT,
  predicted_hazard_category TEXT,
  predicted_risk_level TEXT,
  decision_support_recommendation TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

If `DATABASE_URL` is not set or the connection fails, the backend continues to operate but will not persist logs.

CORS / Proxy

For local development with the SvelteKit frontend, run both frontend and backend on the same origin or configure a proxy in Bun/Vite to forward `/api` to `http://127.0.0.1:8000`.
