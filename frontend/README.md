# Frontend (SvelteKit + Bun)

This folder contains a localized SvelteKit frontend scaffold (English + German) for the SCARP Hazard Chatbot.

Recommended approach: use Bun's Svelte helper to create or run the app, then use this `src`.

Create and run with Bun (example):

```bash
bunx sv create my-app
cd my-app
bun install
bun run dev
```

Or run this scaffold directly:

```bash
cd frontend
bun install
bun run dev
```

Localization:

- The UI supports English (`en`) and German (`de`). Use the language buttons in the header to switch languages.

Notes:

- The frontend sends form POSTs to `/api/chat`. For development, either run the Axum backend at the same origin or update the fetch URL in `src/routes/+page.svelte` to point to your backend/inference endpoint.
- The UI is intentionally minimal for academic screenshots and evaluation.
