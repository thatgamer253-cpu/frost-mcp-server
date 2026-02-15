FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV APP_HOME /app

# Create app directory
WORKDIR $APP_HOME

# Install system dependencies
# We need build-essential for some python packages (e.g., psycopg2-binary)
# and libpq-dev for PostgreSQL client libraries.
# curl is useful for health checks.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
# This step is separated to leverage Docker's layer caching.
# If requirements.txt doesn't change, this layer won't be rebuilt.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . $APP_HOME

# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run the application
# Using Uvicorn with Gunicorn for production-ready deployment.
# --host 0.0.0.0 makes the server accessible from outside the container.
# --workers can be adjusted based on CPU cores (2-4 * CPU_CORES + 1 is a common heuristic).
# --bind 0.0.0.0:8000 specifies the address and port for Gunicorn.
# main:app refers to the FastAPI application instance named 'app' in 'main.py'.
# --worker-class uvicorn.workers.UvicornWorker ensures Uvicorn handles ASGI.
CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]