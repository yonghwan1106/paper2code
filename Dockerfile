# Paper2Code - Scientific Paper to Executable Code
# Multi-stage Dockerfile for production deployment

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Stage 2: Runtime
FROM python:3.11-slim as runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Create output directory
RUN mkdir -p /app/output

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash paper2code && \
    chown -R paper2code:paper2code /app
USER paper2code

# Default command
ENTRYPOINT ["python", "-m", "src.main"]
CMD ["--help"]


# Stage 3: Sandbox - Minimal image for running generated code
FROM python:3.11-slim as sandbox

WORKDIR /app

# Install common scientific computing packages
RUN pip install --no-cache-dir \
    numpy>=1.24.0 \
    scipy>=1.10.0 \
    pandas>=2.0.0 \
    scikit-learn>=1.2.0 \
    matplotlib>=3.7.0 \
    torch>=2.0.0 \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Security: No network access, limited resources
# These are enforced at runtime via Docker run flags

# Create non-root user
RUN useradd --create-home --shell /bin/bash runner && \
    chown -R runner:runner /app
USER runner

# Default command - run main.py in /app
CMD ["python", "main.py"]
