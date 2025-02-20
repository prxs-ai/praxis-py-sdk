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

ARG PIP_EXTRA_INDEX_URL
ENV PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL}

# Install dependencies with a private registry
COPY --from=builder /build/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r ./requirements.txt && \
    rm ./requirements.txt

# Clean the environment variables
ENV PIP_EXTRA_INDEX_URL=

# Install keyring and keyrings.codeartifact
RUN pip install keyring keyrings.codeartifact

WORKDIR /serve_app

COPY src/agent /serve_app/agent
COPY entrypoint.py /serve_app/entrypoint.py
