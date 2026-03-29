FROM ghcr.io/astral-sh/uv:python3.12-trixie

ENV PYTHONUNBUFFERED=1
ENV RUN_INSTALL=true

RUN apt-get update && apt-get install -y \
    curl \
    cron \
    build-essential \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev

WORKDIR /app

COPY requirements.txt .

RUN uv venv backend_venv

ENV VIRTUAL_ENV=/app/backend_venv
RUN uv pip install -r requirements.txt

COPY . .

RUN chmod +x INSTALL.sh data/DMG/*.sh data/MKG/*.sh

RUN mkdir -p /etc/crontabs && \
    echo "0 0 * * 1 root /app/INSTALL.sh >> /var/log/cron.log 2>&1" > /etc/crontabs/root

VOLUME ["/app/data"]

EXPOSE 8080

CMD ["sh", "-c", "if [ \"$RUN_INSTALL\" = \"true\" ]; then /app/INSTALL.sh; fi && cron && /app/backend_venv/bin/uvicorn app:app --host 0.0.0.0 --port 8080"]
