FROM python:3.11-slim

ARG DEBIAN_FRONTEND=noninteractive

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/code

# Upgrade pip
RUN pip install --upgrade pip

WORKDIR /code

# Copy requirements file
COPY requirements.docker.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.docker.txt

# Copy application code
COPY app ./app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run Flask app with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "2", "--timeout", "120", "app.main:app"]