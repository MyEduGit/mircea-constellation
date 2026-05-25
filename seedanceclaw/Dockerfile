# SeedanceClaw — deployable scaffold (Seedance AI video generation via fal.ai).
# Build context: repo root.
# Build from repo root:
#   docker build -f seedanceclaw/Dockerfile \
#     --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) .
# Or via compose (context set to repo root in docker-compose.yml).

FROM python:3.12-slim

ARG USER_ID=1000
ARG GROUP_ID=1000

# curl is used for the Docker healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${GROUP_ID} seedanceclaw \
    && useradd -u ${USER_ID} -g ${GROUP_ID} -m -s /bin/bash seedanceclaw

WORKDIR /app

COPY seedanceclaw/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY seedanceclaw /app/seedanceclaw

# Pre-create data dirs (volume mount contents take precedence at runtime).
RUN mkdir -p /data/videos /data/images /data/logs /data/evidence \
    && chown -R ${USER_ID}:${GROUP_ID} /data /app

USER ${USER_ID}

CMD ["python", "-m", "seedanceclaw.main", "--mode=daemon"]
