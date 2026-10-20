# lexflow: pipeline, dashboard and API in one image.  See docker-compose.yml for the services around it.
# Node 22 comes from the official image: bpmnlint loads ES modules with require(), which Node 18 cannot.
FROM node:22-bookworm-slim AS node

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LEXFLOW_DATA=/data

# node: bpmnlint, dmnlint, bpmn-auto-layout and the README chart renderer
# graphviz + cairo: POWL drawings and SVG-to-PNG; tini: clean signals for job subprocesses
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && apt-get update \
 && apt-get install -y --no-install-recommends graphviz libcairo2 curl tini poppler-utils \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY tools/bpmnlint-plugin-lexipedia tools/bpmnlint-plugin-lexipedia
COPY tools/node/package.json tools/node/package-lock.json tools/node/.bpmnlintrc tools/node/.dmnlintrc tools/node/
RUN cd tools/node && npm ci --install-links --no-audit --no-fund
COPY tools/node-alpha/package.json tools/node-alpha/package-lock.json tools/node-alpha/
RUN cd tools/node-alpha && npm ci --no-audit --no-fund
COPY tools/web/package.json tools/web/package-lock.json tools/web/
RUN cd tools/web && npm ci --no-audit --no-fund

COPY . .
RUN printf '#!/bin/sh\nexec python -m lexflow "$@"\n' > /usr/local/bin/lexflow && chmod +x /usr/local/bin/lexflow

EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD curl -fsS http://localhost:8000/api/health || exit 1
ENTRYPOINT ["tini", "--"]
CMD ["python", "-m", "lexflow", "serve"]
