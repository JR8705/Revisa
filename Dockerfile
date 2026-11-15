FROM python:3.14-slim AS dependencias

WORKDIR /app
COPY requirements.txt .
RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.14-slim

ENV PATH="/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd --system --no-create-home --uid 10001 revisa

WORKDIR /app
COPY --from=dependencias /venv /venv
COPY alembic.ini .
COPY alembic alembic
COPY api api

USER 10001
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
