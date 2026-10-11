FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
LABEL org.opencontainers.image.title="NVR Watch" \
      org.opencontainers.image.description="Independent Blue Iris playback portal" \
      org.opencontainers.image.source="https://github.com/TTdriver/nvr-watch"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 NVR_WATCH_DATA_DIR=/data
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --create-home watch \
    && mkdir /data && chown watch:watch /data
COPY server.py exports.py settings.py ./
COPY web ./web
USER watch
EXPOSE 8090
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/healthz',timeout=3).read()" || exit 1
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8090", "--data-dir", "/data"]
