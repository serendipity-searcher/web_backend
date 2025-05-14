FROM python:3.10-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN python -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.10-slim

WORKDIR /app

COPY --from=builder /app/venv /app/venv
COPY . .

ENV PATH="/app/venv/bin:$PATH"

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]