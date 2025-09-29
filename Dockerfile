# Simple Dockerfile following working reference approach
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# Install system dependencies needed for libp2p, health checks, Docker CLI and Dagger CLI
RUN apt-get update && apt-get install -y \
    build-essential \
    libgmp-dev \
    libssl-dev \
    libffi-dev \
    pkg-config \
    curl \
    wget \
    net-tools \
    ca-certificates \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI (required by Dagger Engine)
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# Install Dagger CLI manually with specific version to align with Python SDK
ARG DAGGER_VERSION=0.18.14
RUN curl -L "https://dl.dagger.io/dagger/releases/${DAGGER_VERSION}/dagger_v${DAGGER_VERSION}_linux_$(dpkg --print-architecture | sed 's/amd64/amd64/; s/arm64/arm64/').tar.gz" -o /tmp/dagger.tar.gz && \
    tar -xzf /tmp/dagger.tar.gz -C /tmp && \
    mv /tmp/dagger /usr/local/bin/ && \
    chmod +x /usr/local/bin/dagger && \
    rm /tmp/dagger.tar.gz && \
    dagger version

WORKDIR /app

# Copy all source files
COPY . .

# Install core dependencies without problematic packages for basic P2P testing
RUN pip install --no-cache-dir \
    libp2p \
    trio \
    trio-asyncio \
    multiaddr \
    loguru \
    pydantic \
    pydantic-settings \
    fastapi \
    uvicorn \
    httpx \
    pyyaml \
    openai \
    websockets \
    aiofiles \
    jinja2 \
    click \
    keyring==25.5.0 \
    python-multipart \
    docker \
    gql[all]==3.5.0 \
    dagger-io==0.18.14

# Create required directories  
RUN mkdir -p logs data

# Expose ports for HTTP API and P2P
EXPOSE 8000 4001

# Default command
CMD ["python", "-m", "praxis_sdk.main"]
