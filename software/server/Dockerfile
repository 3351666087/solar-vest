# SolarVest console server: Python stdlib only, no pip installs.
FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SV_DB=/data/solarvest.db \
    PORT=8790

RUN addgroup -S -g 10001 solarvest \
 && adduser -S -D -H -u 10001 -G solarvest solarvest \
 && mkdir -p /app /data \
 && chown solarvest:solarvest /data

WORKDIR /app
COPY --chown=root:root server.py console.html ./

USER solarvest
EXPOSE 8790
VOLUME /data

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O- http://127.0.0.1:8790/healthz >/dev/null || exit 1

CMD ["python", "server.py"]
