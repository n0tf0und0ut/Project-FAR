# Ephemeral public-test image only. The worker's candidate code is NEVER built
# into the image; it is later mounted read-only with Docker --network none.
# Base image identity is frozen. Debian package index is not; retain the
# resulting image ID, apt versions and build log as Research provenance.
FROM python:3.12-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
# The current repository declares PyYAML >=6,<7 and jsonschema >=4.22,<5.
# Pin a compatible concrete choice so public test discovery has both modules.
RUN python -m pip install --disable-pip-version-check --no-cache-dir \
    'PyYAML==6.0.2' 'jsonschema==4.23.0'
