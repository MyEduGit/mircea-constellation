# OpenClaw@URANTiOS-ingest — deployable scaffold
# Build context: repo root (so cognee_config.py and openclaw_ingest/ are both reachable)
# Build from repo root:
#   docker build -f openclaw_ingest/Dockerfile \
#     --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) .
# Or via compose (context already set to repo root in docker-compose.yml).

FROM python:3.12-slim

ARG USER_ID=1000
ARG GROUP_ID=1000

# curl only — required for the compose healthcheck probe.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${GROUP_ID} openclaw \
    && useradd -u ${USER_ID} -g ${GROUP_ID} -m -s /bin/bash openclaw

WORKDIR /app

# Install pinned deps first for layer caching.
COPY openclaw_ingest/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the module + the single-source-of-truth Cognee config from repo root.
COPY openclaw_ingest /app/openclaw_ingest
COPY cognee_config.py /app/cognee_config.py

# Pre-create data dirs (volume mount will override contents; structure stays).
RUN mkdir -p /data/ingest/chatcode /data/ingested/chatcode \
             /data/classified /data/canon /data/logs /data/evidence \
    && chown -R ${USER_ID}:${GROUP_ID} /data /app

USER ${USER_ID}

# Package-style execution — matches actual module layout (openclaw_ingest/main.py).
CMD ["python", "-m", "openclaw_ingest.main", "--mode=ingest-daemon"]
