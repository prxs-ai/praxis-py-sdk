# Note: You can use any Debian/Ubuntu based image you want.
FROM mcr.microsoft.com/devcontainers/base:bookworm

# [Optional] Uncomment this section to install additional OS packages.
# RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
#     && apt-get -y install --no-install-recommends <your-package-list-here>

RUN apt update && \
    apt -y --no-install-recommends install libgmp3-dev python3-pip && \
    pip3 install --upgrade pip && \
    pip3 install poetry && \
    rm -rf /var/lib/apt/lists/*
