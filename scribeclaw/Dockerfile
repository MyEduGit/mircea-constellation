# ScribeClaw — deployable scaffold (media edit + Romanian transcription).
# Build context: repo root.
# Build from repo root:
#   docker build -f scribeclaw/Dockerfile \
#     --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) .
# Or via compose (context set to repo root in docker-compose.yml).

FROM python:3.12-slim

ARG USER_ID=1000
ARG GROUP_ID=1000

# ffmpeg is the load-bearing system dependency; curl is for the healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${GROUP_ID} scribeclaw \
    && useradd -u ${USER_ID} -g ${GROUP_ID} -m -s /bin/bash scribeclaw

WORKDIR /app

COPY scribeclaw/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY scribeclaw /app/scribeclaw

# Pre-create data dirs (volume mount contents take precedence at runtime).
RUN mkdir -p /data/media/in /data/media/edited /data/media/audio \
             /data/transcripts /data/youtube /data/logs /data/evidence \
    && chown -R ${USER_ID}:${GROUP_ID} /data /app

USER ${USER_ID}

CMD ["python", "-m", "scribeclaw.main", "--mode=daemon"]
