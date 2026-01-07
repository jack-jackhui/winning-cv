# =============================================================================
# Stage 1: Build Frontend (React/Vite)
# =============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files first for better caching
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --prefer-offline --no-audit

# Copy frontend source
COPY frontend/ ./

# Build for production
RUN npm run build

# =============================================================================
# Stage 2: Python Backend
# =============================================================================
FROM python:3.12-slim AS backend

LABEL authors="jackhui"

# Build args & env
ARG TARGETOS
ARG TARGETARCH

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:${PATH}" \
    CHROMIUM_PATH=/usr/bin/chromium \
    PIP_NO_CACHE_DIR=1 \
    API_PORT=8000

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
    # Install UV (faster pip)
    curl -Ls https://astral.sh/uv/install.sh | sh -s -- "$TARGETOS" "$TARGETARCH" && \
    mv /root/.local/bin/uv /usr/local/bin/ && \
    \
    # Install all Python deps
    uv pip install --system \
       --no-cache-dir \
       --force-reinstall \
       -r requirements.txt && \
    \
    # Download & install spaCy English model
    python -m spacy download en_core_web_sm && \
    python -m spacy validate && \
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

# Expose FastAPI port
EXPOSE 8000

# Default: Launch FastAPI server
CMD ["python", "run_api.py"]

# =============================================================================
# Stage 3: Frontend with Nginx (for standalone frontend container)
# =============================================================================
FROM nginx:alpine AS frontend

# Copy custom nginx config
COPY nginx/frontend.conf /etc/nginx/conf.d/default.conf

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
