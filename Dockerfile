# Use official Python slim image
FROM python:3.12-slim AS builder

LABEL authors="jackhui"

# Build args & env
ARG TARGETOS
ARG TARGETARCH

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

# Copy in your requirements
COPY requirements.in requirements.txt ./

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        build-essential gcc g++ python3-dev \
        chromium chromium-driver libnss3 \
        libfontconfig1 fonts-liberation fonts-noto-cjk \
        libssl-dev libffi-dev && \
    \
    # Install UV (your faster pip wrapper)
    curl -Ls https://astral.sh/uv/install.sh | sh -s -- "$TARGETOS" "$TARGETARCH" && \
    mv /root/.local/bin/uv /usr/local/bin/ && \
    \
    # Install all Python deps
    uv pip install --system \
       --no-cache-dir \
       --force-reinstall \
       -r requirements.txt && \
    \
    # -------------------------------------------------------------------------
    # ✨ NEW STEP: download & install spaCy English model
    python -m spacy download en_core_web_sm && \
    # (optional) verify it’s really there
    python -m spacy validate && \
    # -------------------------------------------------------------------------
    \
    # Remove build tools & clean up apt caches
    apt-get purge -y --auto-remove \
        build-essential gcc g++ python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create a non-root user and set ownership
RUN useradd -m -U -u 1001 appuser && \
    chown -R appuser:appuser /winning-cv

# Copy in the rest of your code
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8501

# Launch the Streamlit app
CMD ["streamlit", "run", "webui_new.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--browser.gatherUsageStats=false"]