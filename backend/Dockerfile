FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for psycopg2 build are covered by psycopg2-binary; keep image lean.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Default command runs the API. The worker overrides this in docker-compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
