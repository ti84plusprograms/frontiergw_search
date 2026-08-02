FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY data ./data

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
