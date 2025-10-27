FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements directory
COPY requirements/ /app/requirements/

# Install production requirements
RUN pip install --no-cache-dir -r requirements/production.txt

# Copy project
COPY . /app/

# Expose port
EXPOSE 8000


CMD python manage.py collectstatic --noinput && \
    gunicorn --bind 0.0.0.0:8000 --workers 3 config.wsgi:application