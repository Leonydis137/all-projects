# Build from the merged/ folder:  docker build -f platform/Dockerfile -t omnis merged/
# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
FROM python:3.12-slim
WORKDIR /app
COPY platform/requirements.txt platform/requirements.txt
RUN pip install --no-cache-dir -r platform/requirements.txt
COPY platform /app/platform
# only the source folders the gateway actually imports or serves (not the 200 MB of web apps)
COPY sources/services/covenant/backend/src /app/sources/services/covenant/backend/src
COPY sources/tools/self-improving-code-analyzer /app/sources/tools/self-improving-code-analyzer
COPY sources/research/circuit-lower-bounds /app/sources/research/circuit-lower-bounds
COPY sources/apps/sites/portfolio /app/sources/apps/sites/portfolio
COPY sources/apps/sites/jacobsbay-site /app/sources/apps/sites/jacobsbay-site
COPY sources/apps/web/hybrid-sat-solver-portal /app/sources/apps/web/hybrid-sat-solver-portal
ENV OMNIS_SOURCES=/app/sources PYTHONPATH=/app/platform
WORKDIR /app/platform
EXPOSE 8080
CMD ["uvicorn", "omnis.api:app", "--host", "0.0.0.0", "--port", "8080"]
