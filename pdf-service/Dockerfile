FROM node:24-bookworm-slim

WORKDIR /app

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY package.json ./
RUN npm install
RUN npx playwright install --with-deps chromium

COPY src ./src

EXPOSE 3001

CMD ["npm", "start"]
