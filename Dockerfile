# Prefect Worker on Snowflake SPCS with UV
# Based on: https://github.com/sfc-gh-jkang/cortex-cost-app-spcs/blob/main/Dockerfile

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    UV_SYSTEM_PYTHON=1 \
    PATH="/root/.local/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install UV - ultra-fast Python package installer
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies using UV
RUN /root/.local/bin/uv pip install --system -e .

# Copy application code
COPY main.py ./

# Copy entrypoint script (optional - only if you need pre-startup commands)
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Expose port for Prefect worker
EXPOSE 8080

# Health check (optional, for monitoring)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run as non-root user for security (optional but recommended)
# RUN useradd -m -u 1000 prefect && chown -R prefect:prefect /app
# USER prefect

# Use entrypoint script for any pre-startup commands
# ENTRYPOINT ["./entrypoint.sh"]

# Start Prefect worker
CMD ["python", "-u", "main.py"]

