FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=5000

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Create necessary directories
RUN mkdir -p instance uploads logs

# Copy application code
COPY . /app/

# Set permissions for uploads and logs directories
RUN chmod -R 755 /app/uploads /app/logs /app/instance

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE $PORT

# Set entrypoint to gunicorn server
CMD gunicorn --bind 0.0.0.0:$PORT --workers 3 --timeout 120 --access-logfile - --error-logfile - "app:create_app('production')"