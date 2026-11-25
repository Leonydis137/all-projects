# Build from the merged/ folder: docker build -f platform/Dockerfile -t omnis merged/
# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY platform/requirements.txt platform/requirements.txt
RUN python -m pip install --no-cache-dir -r platform/requirements.txt \
    && groupadd --system --gid 10001 omnis \
    && useradd --system --uid 10001 --gid 10001 --no-create-home \
       --home-dir /nonexistent --shell /usr/sbin/nologin omnis \
    && mkdir -p /data \
    && chown 10001:10001 /data

COPY platform /app/platform
# Only source folders the gateway imports or serves; do not copy the full monorepo.
COPY sources/services/covenant/backend/src /app/sources/services/covenant/backend/src
COPY sources/tools/self-improving-code-analyzer /app/sources/tools/self-improving-code-analyzer
COPY sources/research/circuit-lower-bounds /app/sources/research/circuit-lower-bounds
COPY sources/apps/sites/portfolio /app/sources/apps/sites/portfolio
COPY sources/apps/sites/jacobsbay-site /app/sources/apps/sites/jacobsbay-site
COPY sources/apps/web/hybrid-sat-solver-portal /app/sources/apps/web/hybrid-sat-solver-portal

ENV OMNIS_SOURCES=/app/sources \
    PYTHONPATH=/app/platform \
    OMNIS_EVIDENCE_DB=/data/evidence.sqlite3

WORKDIR /app/platform
USER 10001:10001
VOLUME ["/data"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"]
CMD ["uvicorn", "omnis.api:app", "--host", "0.0.0.0", "--port", "8080"]
