# web_backend

SEARCHER backend for the website. Built on the DMG collections (public &amp; private).

# Docker

## Build

```bash
docker build -t web_backend .
```

## Run

```bash
docker run \
    -e AWS_ACCESS_KEY_ID="..." \
    -e AWS_SECRET_ACCESS_KEY="..." \
    -v ./data/DMG/images:/app/data/DMG/images \
    -v ./data/DMG/dumps:/app/data/DMG/dumps \
    -v ./logs/cron.log:/var/log/cron.log \
    -p 8080:8080 \
    web_backend
```
