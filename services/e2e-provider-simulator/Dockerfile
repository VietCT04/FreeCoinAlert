FROM node:24.18.0-bookworm-slim

WORKDIR /app

COPY services/e2e-provider-simulator/package.json ./package.json
RUN npm install --omit=dev --ignore-scripts --no-audit --no-fund

COPY services/e2e-provider-simulator/src ./src

RUN mkdir -p /e2e && chmod 0777 /e2e

USER node
EXPOSE 9000
CMD ["node", "src/server.mjs"]
