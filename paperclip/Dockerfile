# Paperclip — evidence bundler.
# Build context: repo root.
# Build from repo root:
#   docker build -f paperclip/Dockerfile \
#     --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) .
# Or via compose (context set to repo root in docker-compose.yml).

FROM python:3.12-slim

ARG USER_ID=1000
ARG GROUP_ID=1000

# curl is required for the healthcheck probe.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${GROUP_ID} paperclip \
    && useradd -u ${USER_ID} -g ${GROUP_ID} -m -s /bin/bash paperclip

WORKDIR /app

COPY paperclip/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY paperclip /app/paperclip

# Pre-create data dirs (volume mount contents take precedence at runtime).
RUN mkdir -p /data/bundles /data/evidence /data/logs \
    && chown -R ${USER_ID}:${GROUP_ID} /data /app

USER ${USER_ID}

CMD ["python", "-m", "paperclip.main", "--mode=daemon"]
