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


ENV PIP_INDEX_URL=https://aws:eyJ2ZXIiOjEsImlzdSI6MTc0ODU0NDA1MiwiZW5jIjoiQTEyOEdDTSIsInRhZyI6InBpbXI4SEhYU1dzbkVwNkNTVnEyYUEiLCJleHAiOjE3NDg1ODcyNTIsImFsZyI6IkExMjhHQ01LVyIsIml2IjoiTFpBVGpEOFpzbXd4V0NTSiJ9.HbhvvkLgeUrINsEawC9YQQ.lcpM1iP24RBib7fk.EyEBmXQOqje6JI3WlVVFlRW1prtDtjGcXbHwQIkyPkcj8Mith9AetCHRYUHKHj9jV1izIEju3lu_9XSgtwGzGChN-fb6CtVw0IBGk9d3PU5DVuWPQiYnZd22PD44zp5WPCcZ7_71afWMVYl-yFgb44EKnbNKPqD4Aowv1Ke_JdY6Ll05toeoVnzUqUcVIjT0gtjQjx3h1oQ9YB_vHl2zgTmUMlwbuWbMycDlx2Wl9Q1o2iH5aEtyTQsjh3Nt-30aYWXkuMU_uGnyIaQTIVzczOOK1FSQ10IonpdibuL3iBY6EOH5nyE6fL8kP-kSE2ZQlH0r2yNLNG_uFzyDZFDZNz1xhwK4wXR1Inzinb5movv8wmeGwkQAgPRaqVGc5wGs5fjZ-cWrA8ALW5blziZbYOBf6ixmO6GF7rgzOoXihhKsOhR9QnMQHZfNyTvoZPs3p1BRTHnyqBOslJdxyN7OaqYP-8052XlTfyTXvP3mSbIcJeyLguVvCrWKKjSYjWQlewJTXUE8bqyvdOJIX4tmDqEjfinn-pp87j4XOFf8swvYz019NpOYU-m-qqH7FZ4dNwf74Jth-DPKujTq3ej-Q6_XJdtMpTWnzA0DVXxCj3uDP5SSEVvLJ4uBxJCG0hiAuptFEdgiZIAeKSnuQ_I8EpJtRdfkggB0RtuZq91BQy5r1Xgd97w3rZK9xCOkqqo01s4T73RcoiTf9OeZRpx853HsNFPTNJq76M6xqf_SB7mUy1XqjLuY0xQ_NKzO_58xKo4xK4mnQRj7JQOB3ln0NdAqgPiiapZa7OSXniU04HB5ozZTZ-Huwz7H2xUx_Wf05RzYQuUq8E0grHf1bgc4PmJ0VeKD5EBZoLmuk7J_R3HxDfKmxd_du3tKWgEhXi2B1CdHUhDDGjsbGJpHP9LHeNvcvmHm49RXnrUIXoqoJHOKpjTqpx_Mfc0Nwu6kEmb2L6eKfr3fP6dS1A1EBVSJEmPWf7kK-Tv68gXYiPAgOa-OkLhhrhZzLCNGYzU4hPjg7vXpISOLY1QIZgPwGdPe4d3R_xiaIJimKe39dpKRVfIcxsyeBEK8p2PBZLw_lar1QOxKi-wuGyWtbF9drR673LkaGhsTFe6XsQ8IQPHZGcybOD_Db2hrvYSGS7fhT_2KgnNIDbSpRVeyGEyipr6Sh7cklYBOBkJ4yfsbtmWWIvnLCBi9sjg9WVq-BClyNFfpoCcpqocQBHdte9HO7HqczGAn3uH5Ghozm6N5vWvea0SxVCujfid2d6nr5aSxjqLZrwnB9V7c1L76HS-2wNkRWWigm5yP2sKWOt_vSCeHR__BxJlc6zEwW3Is.Oqhaqvv5mIpjbiWlSRr1qA@praxis-688567299207.d.codeartifact.eu-west-1.amazonaws.com/pypi/praxis/simple/
ENV PIP_EXTRA_INDEX_URL=https://aws:eyJ2ZXIiOjEsImlzdSI6MTc0ODU0NDA1MiwiZW5jIjoiQTEyOEdDTSIsInRhZyI6InBpbXI4SEhYU1dzbkVwNkNTVnEyYUEiLCJleHAiOjE3NDg1ODcyNTIsImFsZyI6IkExMjhHQ01LVyIsIml2IjoiTFpBVGpEOFpzbXd4V0NTSiJ9.HbhvvkLgeUrINsEawC9YQQ.lcpM1iP24RBib7fk.EyEBmXQOqje6JI3WlVVFlRW1prtDtjGcXbHwQIkyPkcj8Mith9AetCHRYUHKHj9jV1izIEju3lu_9XSgtwGzGChN-fb6CtVw0IBGk9d3PU5DVuWPQiYnZd22PD44zp5WPCcZ7_71afWMVYl-yFgb44EKnbNKPqD4Aowv1Ke_JdY6Ll05toeoVnzUqUcVIjT0gtjQjx3h1oQ9YB_vHl2zgTmUMlwbuWbMycDlx2Wl9Q1o2iH5aEtyTQsjh3Nt-30aYWXkuMU_uGnyIaQTIVzczOOK1FSQ10IonpdibuL3iBY6EOH5nyE6fL8kP-kSE2ZQlH0r2yNLNG_uFzyDZFDZNz1xhwK4wXR1Inzinb5movv8wmeGwkQAgPRaqVGc5wGs5fjZ-cWrA8ALW5blziZbYOBf6ixmO6GF7rgzOoXihhKsOhR9QnMQHZfNyTvoZPs3p1BRTHnyqBOslJdxyN7OaqYP-8052XlTfyTXvP3mSbIcJeyLguVvCrWKKjSYjWQlewJTXUE8bqyvdOJIX4tmDqEjfinn-pp87j4XOFf8swvYz019NpOYU-m-qqH7FZ4dNwf74Jth-DPKujTq3ej-Q6_XJdtMpTWnzA0DVXxCj3uDP5SSEVvLJ4uBxJCG0hiAuptFEdgiZIAeKSnuQ_I8EpJtRdfkggB0RtuZq91BQy5r1Xgd97w3rZK9xCOkqqo01s4T73RcoiTf9OeZRpx853HsNFPTNJq76M6xqf_SB7mUy1XqjLuY0xQ_NKzO_58xKo4xK4mnQRj7JQOB3ln0NdAqgPiiapZa7OSXniU04HB5ozZTZ-Huwz7H2xUx_Wf05RzYQuUq8E0grHf1bgc4PmJ0VeKD5EBZoLmuk7J_R3HxDfKmxd_du3tKWgEhXi2B1CdHUhDDGjsbGJpHP9LHeNvcvmHm49RXnrUIXoqoJHOKpjTqpx_Mfc0Nwu6kEmb2L6eKfr3fP6dS1A1EBVSJEmPWf7kK-Tv68gXYiPAgOa-OkLhhrhZzLCNGYzU4hPjg7vXpISOLY1QIZgPwGdPe4d3R_xiaIJimKe39dpKRVfIcxsyeBEK8p2PBZLw_lar1QOxKi-wuGyWtbF9drR673LkaGhsTFe6XsQ8IQPHZGcybOD_Db2hrvYSGS7fhT_2KgnNIDbSpRVeyGEyipr6Sh7cklYBOBkJ4yfsbtmWWIvnLCBi9sjg9WVq-BClyNFfpoCcpqocQBHdte9HO7HqczGAn3uH5Ghozm6N5vWvea0SxVCujfid2d6nr5aSxjqLZrwnB9V7c1L76HS-2wNkRWWigm5yP2sKWOt_vSCeHR__BxJlc6zEwW3Is.Oqhaqvv5mIpjbiWlSRr1qA@praxis-688567299207.d.codeartifact.eu-west-1.amazonaws.com/pypi/agents/simple/https://aws:eyJ2ZXIiOjEsImlzdSI6MTc0ODU0NDA1MiwiZW5jIjoiQTEyOEdDTSIsInRhZyI6InBpbXI4SEhYU1dzbkVwNkNTVnEyYUEiLCJleHAiOjE3NDg1ODcyNTIsImFsZyI6IkExMjhHQ01LVyIsIml2IjoiTFpBVGpEOFpzbXd4V0NTSiJ9.HbhvvkLgeUrINsEawC9YQQ.lcpM1iP24RBib7fk.EyEBmXQOqje6JI3WlVVFlRW1prtDtjGcXbHwQIkyPkcj8Mith9AetCHRYUHKHj9jV1izIEju3lu_9XSgtwGzGChN-fb6CtVw0IBGk9d3PU5DVuWPQiYnZd22PD44zp5WPCcZ7_71afWMVYl-yFgb44EKnbNKPqD4Aowv1Ke_JdY6Ll05toeoVnzUqUcVIjT0gtjQjx3h1oQ9YB_vHl2zgTmUMlwbuWbMycDlx2Wl9Q1o2iH5aEtyTQsjh3Nt-30aYWXkuMU_uGnyIaQTIVzczOOK1FSQ10IonpdibuL3iBY6EOH5nyE6fL8kP-kSE2ZQlH0r2yNLNG_uFzyDZFDZNz1xhwK4wXR1Inzinb5movv8wmeGwkQAgPRaqVGc5wGs5fjZ-cWrA8ALW5blziZbYOBf6ixmO6GF7rgzOoXihhKsOhR9QnMQHZfNyTvoZPs3p1BRTHnyqBOslJdxyN7OaqYP-8052XlTfyTXvP3mSbIcJeyLguVvCrWKKjSYjWQlewJTXUE8bqyvdOJIX4tmDqEjfinn-pp87j4XOFf8swvYz019NpOYU-m-qqH7FZ4dNwf74Jth-DPKujTq3ej-Q6_XJdtMpTWnzA0DVXxCj3uDP5SSEVvLJ4uBxJCG0hiAuptFEdgiZIAeKSnuQ_I8EpJtRdfkggB0RtuZq91BQy5r1Xgd97w3rZK9xCOkqqo01s4T73RcoiTf9OeZRpx853HsNFPTNJq76M6xqf_SB7mUy1XqjLuY0xQ_NKzO_58xKo4xK4mnQRj7JQOB3ln0NdAqgPiiapZa7OSXniU04HB5ozZTZ-Huwz7H2xUx_Wf05RzYQuUq8E0grHf1bgc4PmJ0VeKD5EBZoLmuk7J_R3HxDfKmxd_du3tKWgEhXi2B1CdHUhDDGjsbGJpHP9LHeNvcvmHm49RXnrUIXoqoJHOKpjTqpx_Mfc0Nwu6kEmb2L6eKfr3fP6dS1A1EBVSJEmPWf7kK-Tv68gXYiPAgOa-OkLhhrhZzLCNGYzU4hPjg7vXpISOLY1QIZgPwGdPe4d3R_xiaIJimKe39dpKRVfIcxsyeBEK8p2PBZLw_lar1QOxKi-wuGyWtbF9drR673LkaGhsTFe6XsQ8IQPHZGcybOD_Db2hrvYSGS7fhT_2KgnNIDbSpRVeyGEyipr6Sh7cklYBOBkJ4yfsbtmWWIvnLCBi9sjg9WVq-BClyNFfpoCcpqocQBHdte9HO7HqczGAn3uH5Ghozm6N5vWvea0SxVCujfid2d6nr5aSxjqLZrwnB9V7c1L76HS-2wNkRWWigm5yP2sKWOt_vSCeHR__BxJlc6zEwW3Is.Oqhaqvv5mIpjbiWlSRr1qA@praxis-688567299207.d.codeartifact.eu-west-1.amazonaws.com/pypi/tools/simple/


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
