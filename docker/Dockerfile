FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm graphviz libcairo2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# node tooling: bpmnlint (+ Lexipedia legal rules), dmnlint, bpmn-moddle; bpmn-auto-layout 2.x for DI
COPY tools/bpmnlint-plugin-lexipedia tools/bpmnlint-plugin-lexipedia
COPY tools/node/package.json tools/node/package-lock.json tools/node/.bpmnlintrc tools/node/.dmnlintrc tools/node/
RUN cd tools/node && npm ci --install-links
COPY tools/node-alpha/package.json tools/node-alpha/package-lock.json tools/node-alpha/
RUN cd tools/node-alpha && npm ci
COPY . .
CMD ["python", "-m", "pytest", "-q"]
