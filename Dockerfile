FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.prod

# Create and set the working directory
WORKDIR /app

# Install system dependencies (needed for compiling some python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file from the backend folder
COPY backend/requirements/ /app/requirements/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements/prod.txt

# Copy the entire backend source code to the working directory
COPY backend/ /app/

# Collect static files
RUN python manage.py collectstatic --no-input

# Ensure the start script is executable
RUN chmod +x start.sh

# The start script will start Gunicorn, Celery, and the Telegram bot
CMD ["./start.sh"]
