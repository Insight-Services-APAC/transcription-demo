FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=5000 \
    ACCEPT_EULA=Y

# Set working directory
WORKDIR /app

# Install system dependencies including supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-transport-https \
    curl \
    gnupg \
    gcc \
    g++ \
    build-essential \
    supervisor \
    unixodbc \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Add Microsoft repository for ODBC drivers
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update

# Install ODBC Driver 17 for SQL Server only
RUN ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
    msodbcsql17 \
    mssql-tools \
    && rm -rf /var/lib/apt/lists/*

# Add SQL Server tools to PATH
ENV PATH="$PATH:/opt/mssql-tools/bin"

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Create necessary directories
RUN mkdir -p instance uploads logs

# Copy application code
COPY . /app/

# Set up supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set permissions for directories
RUN chmod -R 755 /app/uploads /app/logs /app/instance

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user but preserve access to ODBC drivers
USER appuser

# Make ODBC configuration accessible to non-root user
ENV ODBCSYSINI=/etc

# Expose port
EXPOSE $PORT

# Start supervisor to manage both web and worker processes
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]