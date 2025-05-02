# Use official Python slim image
FROM python:3.12-slim as builder

LABEL authors="jackhui"

# Build arguments for multi-arch support
ARG TARGETOS
ARG TARGETARCH

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:${PATH}" \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    CHROMIUM_PATH=/usr/bin/chromium \
    PIP_NO_CACHE_DIR=1

WORKDIR /winning-cv

# Install system dependencies in a single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        # Chromium dependencies
        chromium \
        chromium-driver \
        libnss3 \
        libgconf-2-4 \
        libfontconfig1 \
        fonts-liberation \
        fonts-noto-cjk \
        # Python build dependencies
        build-essential \
        python3-dev \
        libssl-dev \
        libffi-dev \
    # Install UV
    && curl -Ls https://astral.sh/uv/install.sh | sh -s -- "$TARGETOS" "$TARGETARCH" \
    && mv /root/.local/bin/uv /usr/local/bin/ \
    # Cleanup
    && apt-get purge -y --auto-remove build-essential python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy requirements first to leverage caching
COPY requirements.in requirements.txt ./

# Install Python packages with UV
RUN uv pip install --system \
    --no-cache-dir \
    -r requirements.txt \
    --force-reinstall \
    --no-deps \
    streamlit==1.45.0

# Create non-root user
RUN useradd -m -U -u 1001 appuser && \
    chown -R appuser:appuser /winning-cv

# Copy application files
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

EXPOSE 8501

# Streamlit command
CMD ["/usr/local/bin/streamlit", "run", "webui_new.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--browser.gatherUsageStats=false"]
