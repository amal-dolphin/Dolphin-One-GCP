# Use an official Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set the working directory
WORKDIR /app

# Install system dependencies (for psycopg2, Pillow, etc.)
RUN apt-get update && apt-get install -y \
    libpq-dev gcc python3-dev musl-dev \
    && apt-get clean

# Install dependencies
COPY requirements/ /app/requirements/
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the project code
COPY . /app/

# Collect static files (optional: you can skip if S3 is handling it)
RUN python manage.py collectstatic --noinput

# Expose the port Cloud Run expects
EXPOSE 8080

# Run the app with Gunicorn
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8080"]