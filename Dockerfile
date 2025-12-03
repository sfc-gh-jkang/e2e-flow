# Multi-stage build for Prefect Worker on Snowflake SPCS
# Based on: https://github.com/sfc-gh-jkang/cortex-cost-app-spcs/blob/main/Dockerfile
# Format reference: https://github.com/sfc-gh-jkang/snowflake-cortex-agents-with-slack/blob/master/Dockerfile

# Stage 1: Build stage
FROM python:3.13-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager using official installer
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    /root/.local/bin/uv --version

# Add uv to PATH for subsequent layers
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies using uv (creates .venv by default)
RUN uv sync --frozen --no-cache || uv sync --no-cache

# Stage 2: Runtime stage
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy uv from builder
COPY --from=builder /root/.local/bin/uv /usr/local/bin/uv

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Set environment to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

# Copy application code
COPY main.py .
COPY prefect_flows/ ./prefect_flows/

# Copy entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port for Prefect worker
EXPOSE 8080

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run as non-root user for security (optional but recommended)
# RUN useradd -m -u 1000 prefect && chown -R prefect:prefect /app
# USER prefect

# Use entrypoint script for any pre-startup commands
# ENTRYPOINT ["./entrypoint.sh"]

# Start Prefect worker using uv
CMD ["uv", "run", "main.py"]

