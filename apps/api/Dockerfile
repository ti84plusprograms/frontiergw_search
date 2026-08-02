FROM python:3.10.20-alpine3.23

WORKDIR /app

COPY pyproject.toml requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock \
    && pip uninstall --yes setuptools wheel

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY data ./data

RUN addgroup -S -g 10001 appuser \
    && adduser -S -D -H -u 10001 -G appuser appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
