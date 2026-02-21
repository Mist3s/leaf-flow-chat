FROM python:3.12-slim AS builder

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

FROM python:3.12-slim

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

USER app

CMD ["uvicorn", "chat_service.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
