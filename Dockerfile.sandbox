# ═══════════════════════════════════════════════════════════════
#  Creation Engine — Sandbox Dockerfile
#  Auto-generated template for isolated build execution
# ═══════════════════════════════════════════════════════════════

FROM python:3.12-slim AS base

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl && \
    rm -rf /var/lib/apt/lists/*

# Non-root user for safety
RUN useradd -m -s /bin/bash builder
WORKDIR /workspace
RUN chown builder:builder /workspace

# Copy and install dependencies first (layer caching)
COPY requirements.txt* ./
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true

# Copy project files
COPY . /workspace
RUN chown -R builder:builder /workspace

# Switch to non-root
USER builder

# Default: run main.py, override via docker run args
CMD ["python", "main.py"]
