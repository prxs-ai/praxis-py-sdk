ARG BASE_IMAGE=rayproject/ray:2.42.1-py310-cpu

FROM ${BASE_IMAGE} as builder

USER root

# Install poetry and dependencies
RUN pip install poetry poetry-plugin-export && \
    poetry config virtualenvs.create false

# Copy dependency files
COPY pyproject.toml poetry.lock* /build/
WORKDIR /build

# Only generate requirements.txt from poetry
RUN poetry export -f requirements.txt --without-hashes --output requirements.txt

FROM ${BASE_IMAGE}

USER root

RUN apt update && \
    apt -y --no-install-recommends install libgmp3-dev gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies with a private registry
COPY --from=builder /build/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r ./requirements.txt && \
    rm ./requirements.txt

# Set the environment variables
ENV PIP_EXTRA_INDEX_URL="https://packages.pypi.prxs.ai/simple/ https://agents.pypi.prxs.ai/simple/ https://tools.pypi.prxs.ai/simple/"

WORKDIR /serve_app

COPY ./praxis_sdk /serve_app/praxis_sdk
RUN touch /serve_app/praxis_sdk/__init__.py

COPY entrypoint.py /serve_app/entrypoint.py
