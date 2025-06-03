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

ENV PIP_INDEX_URL=https://aws:eyJ2ZXIiOjEsImlzdSI6MTc0ODk0MzQ4MywiZW5jIjoiQTEyOEdDTSIsInRhZyI6IjQ0ZlBHeTBmc2V4MEVaQjRCZVl5MlEiLCJleHAiOjE3NDg5ODY2ODMsImFsZyI6IkExMjhHQ01LVyIsIml2IjoiSHNja3dSNzc4TGE1aDFMLSJ9.dh6lhu93sZu-FY6t4r71bA.urSuG5rRx1V2ugne.cKGdaPOAkc_GPyKC1NXE7W-VUxY8yv2fwo8dLtsbfOpzPiA7_6Ull9I2Di2mOGGbDE_9trx34ErajnQDIm-UnMrpFq1TOtd6sXYnhFe7Q-EN7P9-G08x2bG-Dd_gsC9rSWpfsYb4-KO80k2ozYb5fent48X9hP59uiCXFKGPwutwZLMEJKgf_zVt82DvhDD_PHq1RVs1G506KgINdCO0CdNvDXOiet9aDalXbKXBOZ6bMRvU_F2f33sY7JpFkM1qYTl7bYfuIIM4nxUWCgQBTfy5a7pS5bTu3ClBC7G8q61Wi2lGz6TCMJTLQpf5uCFpImV-8luhvCkpEYErymWlv7VOxYSO7O0z59Of8ci-MoqFkJ_hrjqlKzF3hza89w-UFOvAGAGcj0EniZjiO1bcFkmDmAyGKqNaXygwtTGc-X_bVJn2KWUB-SCCS2fizL_wX-dwi8t-xQBxQeJkt3n5tcoG5Vp9jm6mzGVR9a6ddZBTgznIrScMin7u8uzLdI6Bx3HOTtqlt97TuxmGL_7Ta5Ocf-hQGmTuYbrS7scsLffI_7GqAVb2_l6CzNH5KgPpYlp0e8918FY3EC7MW5WjpbnC0n4Ymias_PP9Q0HUTvza5aglwLUpX7Z_Qd9R9BPEj-dcYo9hes88c-xWvpWXQsmpBmiv3BIn4dVlwN7_Asa-m9pQ0_mftq1e_JlF6RWikQo-U0dcAUTTBonVTZpB7tYhsXl4WtClHTseXVFRb99ylyP1kULdiD39bci7tzxDCUy1UVdFh-3Wzx8jIs2iON2CCiRUh3TXEyEk9Bd7b7GLwbaqQkfXttM0HzvaRtfvAuZjw_XRJ83NAkJ23eyVfP5iS57HE-bh5_Hcm7rNEAT7jpocIpKhAQ4ubyU8O9WyehFjqqQR3nETKGb5nmUe65AdW8pBcTiYamiFff9AuegeqMrI_L8pR6-THu97IRTCVHKbPMEO99S9zQwILv0kmHhfCgpiKl6Dp6rGLPXX7N1DgOzsBdQ-g1v0d6jmUxx6FNWshp8965M_ck117ROqrKJjtaYrxGf-a4zCB21-LZO_b2haR4U9A9u30E5mCWAhBvR3q0qUEhGssPv9EmAJyW5MfWkofp1JmpWM8asaG4giCpA4Lo_QqSeiB4WMxPNJkBNJylSbCt746vqPdr8JOGjiG-08EYMcYTvOBuDxhTP3E8rU2MB9QTLYOo9jv9QT2Zu11MfKEuDbpqEfvUt6nI5y8DU9to1aD0Zq7Wi0euukdzO97W2IjKwFg6ItLDPrLAkN_3i-Zx8eNsCWYcdtd5yp67qp8gLkjRI.8Zt87Q4FqVBVS0V8l9ls0w@praxis-688567299207.d.codeartifact.eu-west-1.amazonaws.com/pypi/praxis/simple/
ENV PIP_EXTRA_INDEX_URL="https://aws:eyJ2ZXIiOjEsImlzdSI6MTc0ODk0MzQ4MywiZW5jIjoiQTEyOEdDTSIsInRhZyI6IjQ0ZlBHeTBmc2V4MEVaQjRCZVl5MlEiLCJleHAiOjE3NDg5ODY2ODMsImFsZyI6IkExMjhHQ01LVyIsIml2IjoiSHNja3dSNzc4TGE1aDFMLSJ9.dh6lhu93sZu-FY6t4r71bA.urSuG5rRx1V2ugne.cKGdaPOAkc_GPyKC1NXE7W-VUxY8yv2fwo8dLtsbfOpzPiA7_6Ull9I2Di2mOGGbDE_9trx34ErajnQDIm-UnMrpFq1TOtd6sXYnhFe7Q-EN7P9-G08x2bG-Dd_gsC9rSWpfsYb4-KO80k2ozYb5fent48X9hP59uiCXFKGPwutwZLMEJKgf_zVt82DvhDD_PHq1RVs1G506KgINdCO0CdNvDXOiet9aDalXbKXBOZ6bMRvU_F2f33sY7JpFkM1qYTl7bYfuIIM4nxUWCgQBTfy5a7pS5bTu3ClBC7G8q61Wi2lGz6TCMJTLQpf5uCFpImV-8luhvCkpEYErymWlv7VOxYSO7O0z59Of8ci-MoqFkJ_hrjqlKzF3hza89w-UFOvAGAGcj0EniZjiO1bcFkmDmAyGKqNaXygwtTGc-X_bVJn2KWUB-SCCS2fizL_wX-dwi8t-xQBxQeJkt3n5tcoG5Vp9jm6mzGVR9a6ddZBTgznIrScMin7u8uzLdI6Bx3HOTtqlt97TuxmGL_7Ta5Ocf-hQGmTuYbrS7scsLffI_7GqAVb2_l6CzNH5KgPpYlp0e8918FY3EC7MW5WjpbnC0n4Ymias_PP9Q0HUTvza5aglwLUpX7Z_Qd9R9BPEj-dcYo9hes88c-xWvpWXQsmpBmiv3BIn4dVlwN7_Asa-m9pQ0_mftq1e_JlF6RWikQo-U0dcAUTTBonVTZpB7tYhsXl4WtClHTseXVFRb99ylyP1kULdiD39bci7tzxDCUy1UVdFh-3Wzx8jIs2iON2CCiRUh3TXEyEk9Bd7b7GLwbaqQkfXttM0HzvaRtfvAuZjw_XRJ83NAkJ23eyVfP5iS57HE-bh5_Hcm7rNEAT7jpocIpKhAQ4ubyU8O9WyehFjqqQR3nETKGb5nmUe65AdW8pBcTiYamiFff9AuegeqMrI_L8pR6-THu97IRTCVHKbPMEO99S9zQwILv0kmHhfCgpiKl6Dp6rGLPXX7N1DgOzsBdQ-g1v0d6jmUxx6FNWshp8965M_ck117ROqrKJjtaYrxGf-a4zCB21-LZO_b2haR4U9A9u30E5mCWAhBvR3q0qUEhGssPv9EmAJyW5MfWkofp1JmpWM8asaG4giCpA4Lo_QqSeiB4WMxPNJkBNJylSbCt746vqPdr8JOGjiG-08EYMcYTvOBuDxhTP3E8rU2MB9QTLYOo9jv9QT2Zu11MfKEuDbpqEfvUt6nI5y8DU9to1aD0Zq7Wi0euukdzO97W2IjKwFg6ItLDPrLAkN_3i-Zx8eNsCWYcdtd5yp67qp8gLkjRI.8Zt87Q4FqVBVS0V8l9ls0w@praxis-688567299207.d.codeartifact.eu-west-1.amazonaws.com/pypi/agents/simple/ https://aws:eyJ2ZXIiOjEsImlzdSI6MTc0ODk0MzQ4MywiZW5jIjoiQTEyOEdDTSIsInRhZyI6IjQ0ZlBHeTBmc2V4MEVaQjRCZVl5MlEiLCJleHAiOjE3NDg5ODY2ODMsImFsZyI6IkExMjhHQ01LVyIsIml2IjoiSHNja3dSNzc4TGE1aDFMLSJ9.dh6lhu93sZu-FY6t4r71bA.urSuG5rRx1V2ugne.cKGdaPOAkc_GPyKC1NXE7W-VUxY8yv2fwo8dLtsbfOpzPiA7_6Ull9I2Di2mOGGbDE_9trx34ErajnQDIm-UnMrpFq1TOtd6sXYnhFe7Q-EN7P9-G08x2bG-Dd_gsC9rSWpfsYb4-KO80k2ozYb5fent48X9hP59uiCXFKGPwutwZLMEJKgf_zVt82DvhDD_PHq1RVs1G506KgINdCO0CdNvDXOiet9aDalXbKXBOZ6bMRvU_F2f33sY7JpFkM1qYTl7bYfuIIM4nxUWCgQBTfy5a7pS5bTu3ClBC7G8q61Wi2lGz6TCMJTLQpf5uCFpImV-8luhvCkpEYErymWlv7VOxYSO7O0z59Of8ci-MoqFkJ_hrjqlKzF3hza89w-UFOvAGAGcj0EniZjiO1bcFkmDmAyGKqNaXygwtTGc-X_bVJn2KWUB-SCCS2fizL_wX-dwi8t-xQBxQeJkt3n5tcoG5Vp9jm6mzGVR9a6ddZBTgznIrScMin7u8uzLdI6Bx3HOTtqlt97TuxmGL_7Ta5Ocf-hQGmTuYbrS7scsLffI_7GqAVb2_l6CzNH5KgPpYlp0e8918FY3EC7MW5WjpbnC0n4Ymias_PP9Q0HUTvza5aglwLUpX7Z_Qd9R9BPEj-dcYo9hes88c-xWvpWXQsmpBmiv3BIn4dVlwN7_Asa-m9pQ0_mftq1e_JlF6RWikQo-U0dcAUTTBonVTZpB7tYhsXl4WtClHTseXVFRb99ylyP1kULdiD39bci7tzxDCUy1UVdFh-3Wzx8jIs2iON2CCiRUh3TXEyEk9Bd7b7GLwbaqQkfXttM0HzvaRtfvAuZjw_XRJ83NAkJ23eyVfP5iS57HE-bh5_Hcm7rNEAT7jpocIpKhAQ4ubyU8O9WyehFjqqQR3nETKGb5nmUe65AdW8pBcTiYamiFff9AuegeqMrI_L8pR6-THu97IRTCVHKbPMEO99S9zQwILv0kmHhfCgpiKl6Dp6rGLPXX7N1DgOzsBdQ-g1v0d6jmUxx6FNWshp8965M_ck117ROqrKJjtaYrxGf-a4zCB21-LZO_b2haR4U9A9u30E5mCWAhBvR3q0qUEhGssPv9EmAJyW5MfWkofp1JmpWM8asaG4giCpA4Lo_QqSeiB4WMxPNJkBNJylSbCt746vqPdr8JOGjiG-08EYMcYTvOBuDxhTP3E8rU2MB9QTLYOo9jv9QT2Zu11MfKEuDbpqEfvUt6nI5y8DU9to1aD0Zq7Wi0euukdzO97W2IjKwFg6ItLDPrLAkN_3i-Zx8eNsCWYcdtd5yp67qp8gLkjRI.8Zt87Q4FqVBVS0V8l9ls0w@praxis-688567299207.d.codeartifact.eu-west-1.amazonaws.com/pypi/tools/simple/"


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
COPY src/base_agent/ /serve_app/base_agent/
COPY entrypoint.py /serve_app/entrypoint.py

COPY --from=builder /build/docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]
