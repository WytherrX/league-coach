FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_PATH=/data/league-coach.db \
    FORWARDED_ALLOW_IPS=127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,fc00::/7

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .
RUN useradd --system --uid 1000 app && mkdir -p /data && chown app /data
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
# --proxy-headers : l'IP réelle et le HTTPS viennent du reverse proxy. Seuls les proxys listés dans
# FORWARDED_ALLOW_IPS (réseaux privés par défaut, modifiable dans .env) sont crus.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
