FROM mcr.microsoft.com/playwright:v1.62.0-noble

ENV PNPM_HOME=/pnpm
ENV PATH=${PNPM_HOME}:${PATH}
ENV E2E_ARTIFACT_DIR=/artifacts/e2e

WORKDIR /workspace

RUN npm install --global pnpm@11.4.0 \
    && mkdir -p /workspace /artifacts/e2e \
    && chown -R pwuser:pwuser /workspace /artifacts

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/e2e/package.json ./apps/e2e/package.json

RUN pnpm install --frozen-lockfile --filter @freecoinalert/e2e...

COPY apps/e2e ./apps/e2e

RUN chown -R pwuser:pwuser /workspace /artifacts

USER pwuser
