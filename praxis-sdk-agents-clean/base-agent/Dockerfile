ARG BASE_IMAGE=rayproject/ray:2.42.1-py310-cpu

FROM ${BASE_IMAGE} as builder

USER root

RUN pip install poetry poetry-plugin-export && \
    poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock* /build/
WORKDIR /build

RUN poetry export -f requirements.txt --without-hashes --output requirements.txt
COPY docker-entrypoint.sh /build/docker-entrypoint.sh
RUN chmod +x /build/docker-entrypoint.sh

FROM ${BASE_IMAGE}

ARG PIP_EXTRA_INDEX_URL
ENV PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL}

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    python3-dev \
    libgmp-dev \
    && rm -rf /var/lib/apt/lists/*


COPY --from=builder /build/requirements.txt ./requirements.txt
# Сначала устанавливаем protobuf нужной версии
RUN pip install --no-cache-dir protobuf==5.29.4

# Затем устанавливаем остальные зависимости с флагом --no-deps для protobuf
RUN pip install --no-cache-dir -r ./requirements.txt && \
    rm ./requirements.txt

RUN pip install keyring keyrings.codeartifact

RUN pip install poetry


ENV ***REMOVED***
ENV ***REMOVED******REMOVED***


WORKDIR /serve_app

COPY py-libp2p /serve_app/py-libp2p

RUN pip install --index-url https://pypi.org/simple/ --no-cache-dir \
    setuptools wheel \
    build \
    trio-asyncio \
    httpx \
    loguru \
    tenacity \
    pydantic-settings \
    base58>=1.0.3 \
    coincurve>=10.0.0 \
    fastecdsa>=1.7.5 \
    grpcio>=1.41.0 \
    lru-dict>=1.1.6 \
    multiaddr>=0.0.9 \
    mypy-protobuf>=3.0.0 \
    noiseprotocol>=0.3.0 \
    protobuf==5.29.4 \
    pycryptodome>=3.9.2 \
    pymultihash>=0.8.2 \
    pynacl>=1.3.0 \
    rpcudp>=3.0.0 \
    trio-typing>=0.0.4 \
    trio>=0.26.0 \
    uvicorn

RUN chmod -R ugo+rwx /serve_app/py-libp2p
WORKDIR /serve_app/py-libp2p
RUN python -m build --wheel --no-isolation --skip-dependency-check .
RUN pip install --no-deps --no-index --find-links=dist/ libp2p

# Force reinstall protobuf 5.29.4 after all dependencies
RUN pip install --force-reinstall protobuf==5.29.4

WORKDIR /serve_app

COPY pyproject.toml /serve_app/pyproject.toml
COPY README.md /serve_app/README.md
COPY src /serve_app/src
COPY entrypoint.py /serve_app/entrypoint.py

COPY --from=builder /build/docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]
