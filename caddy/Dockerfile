FROM oven/bun:1 AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/bun.lock ./
COPY frontend/svelte.config.js frontend/vite.config.js ./
COPY frontend/src ./src
COPY frontend/static ./static
COPY frontend/README.md ./README.md

RUN bun install && bun run build

FROM alpine:3.20 AS questionnaire-builder

WORKDIR /app

COPY Questionnaire ./Questionnaire

# Build Caddy with the rate-limit plugin (per-client-IP limiting on /api).
FROM caddy:2-builder AS caddy-builder
RUN xcaddy build --with github.com/mholt/caddy-ratelimit

FROM caddy:2-alpine

COPY --from=caddy-builder /usr/bin/caddy /usr/bin/caddy
COPY caddy/Caddyfile /etc/caddy/Caddyfile
COPY --from=frontend-builder /app/frontend/build /srv/chatbot
COPY --from=questionnaire-builder /app/Questionnaire /srv/questionnaire

EXPOSE 80

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]