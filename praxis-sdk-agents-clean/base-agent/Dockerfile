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

ENV PIP_INDEX_URL=https://aws:eyJ2ZXIiOjEsImlzdSI6MTc0ODg2NjE5MiwiZW5jIjoiQTEyOEdDTSIsInRhZyI6Ik0tNEpNckFXM19IR19XWUVqM3Z2ZnciLCJleHAiOjE3NDg5MDkzOTIsImFsZyI6IkExMjhHQ01LVyIsIml2IjoiX2xuUXY1QmtCaDR5ZXlFdiJ9.1OOyXXtXjsDVn16BIOlHXw.PDR7wOOTUT8YxgTt.VL8dWgSckwjdbnOvgfI1acOeV6Z9Bu5jxx5MuKULfphp1SGR7VUGld5C3AEjybu3TuZu5OQE1Y6tX5R_FM5f-cQ0MeKK_QVyFJ1Du8nHV2F6q9EM8j1xagMZlrDarWNYNj_L22zNCLYlh_pK_DwnZl4p05oTsql6JUh0vyvP2U5TYBuqrZ6hw_5QGo12eYwyGOoJ1w_Bnz-HoR9oee4RGP1PMFPvsZ5DoOoREWjO8xIFLUrGUBUCjNjzrZEMgcuLiVc_CHxKd-Q005p5zdI7YEeoRGyMC-px3lEN5k1BZ18gbD4Rw0wqU8FUR-JPCWtdh4rrk7mjwjI5STvlR3N2xTRnMmZ1zW34BM3E2r4uUTb4NPl_r0ndFBLWnDT2kVHmCZONFvN4HbUvYgTV48O_CSCRpTLl7z9qxXhe-hWhIikrWIeFM7qjZr9kYFIi9dDPF9CE8uuQ1MklvGMvS2fglVr4BiVk1qgnLyNtdCSldLpe8_Dlsx8BlztkeE6di-cXxGqcw6C3oX5SjxWg1WK5godkdDT-Yr4Gxwvy-A3wRfaJUq0bWASxV_LGyxvPpoR7tv2QwN_LMsJSTSChn_CnkjABOP5vJavsk8rZgBaOPpIfLyk5v7G4T_uusYsO92zT7PZPTMQsCbTWYj5XeNcw4w5eIPEDu8LPu_rqUU1IVkUOAaQVtvJZqYwWPZmRoRj6gPO5T0PAn2LDYfEUMs29xOkh3Z9mKTXGKsY_ioNEUtJ5bp2H0NtrVZgVkCQ-fUjvZujNQPb3_IlmZvblMrkKe8hZ4dZbKX0bTifa4UWXH-jlYqwydDw6QPzw1r0Sgw9KWkRm3bgw2qnfp-sA2yQP1dEu_uJVs4z4nLv3d2As8pHJrhnLUuuDuEJJk35afMtvkuhviWqjJ3f6seZutApJc9UYIQP3sDiI7BO8seF1fKhc2UYaQK36ttpxvONpOhFr7DC3gimWGQkIe_sSPwfdGzhb7ANNX1TH_mZZaqdzE_zNwaX97jaALYgNh_RfhaxR2OLWHVFGetOyYuTHXykcUlcbcN-qI9JzeNnRK1yV-aS7vcHXRhVa2CJInLZEKwnce0Skk0CdKil7kyLIPtQUcu3sKSp7MoZUHQtNB7PMfKjMKBChx_e62U7Uftin2RMIdUxCVW2uSPLdU-JgwdL9wun1U-LkMi_jFPeVxDcMKt0y1ljhTQXpiBDGVy0_hYD2fgPkpa6Wc27Tahi6RkWUBcONJunBEkjgvrDLil2k9a6EamYEamodXnFIEoAdBbifIaBtMfKITj0GW-M7EQBiqpa9UuisvA.uKq7TZAxXl-5wKGQlVMeSg@praxis-688567299207.d.codeartifact.eu-west-1.amazonaws.com/pypi/praxis/simple/
ENV PIP_EXTRA_INDEX_URL=https://aws:eyJ2ZXIiOjEsImlzdSI6MTc0ODg2NjE5MiwiZW5jIjoiQTEyOEdDTSIsInRhZyI6Ik0tNEpNckFXM19IR19XWUVqM3Z2ZnciLCJleHAiOjE3NDg5MDkzOTIsImFsZyI6IkExMjhHQ01LVyIsIml2IjoiX2xuUXY1QmtCaDR5ZXlFdiJ9.1OOyXXtXjsDVn16BIOlHXw.PDR7wOOTUT8YxgTt.VL8dWgSckwjdbnOvgfI1acOeV6Z9Bu5jxx5MuKULfphp1SGR7VUGld5C3AEjybu3TuZu5OQE1Y6tX5R_FM5f-cQ0MeKK_QVyFJ1Du8nHV2F6q9EM8j1xagMZlrDarWNYNj_L22zNCLYlh_pK_DwnZl4p05oTsql6JUh0vyvP2U5TYBuqrZ6hw_5QGo12eYwyGOoJ1w_Bnz-HoR9oee4RGP1PMFPvsZ5DoOoREWjO8xIFLUrGUBUCjNjzrZEMgcuLiVc_CHxKd-Q005p5zdI7YEeoRGyMC-px3lEN5k1BZ18gbD4Rw0wqU8FUR-JPCWtdh4rrk7mjwjI5STvlR3N2xTRnMmZ1zW34BM3E2r4uUTb4NPl_r0ndFBLWnDT2kVHmCZONFvN4HbUvYgTV48O_CSCRpTLl7z9qxXhe-hWhIikrWIeFM7qjZr9kYFIi9dDPF9CE8uuQ1MklvGMvS2fglVr4BiVk1qgnLyNtdCSldLpe8_Dlsx8BlztkeE6di-cXxGqcw6C3oX5SjxWg1WK5godkdDT-Yr4Gxwvy-A3wRfaJUq0bWASxV_LGyxvPpoR7tv2QwN_LMsJSTSChn_CnkjABOP5vJavsk8rZgBaOPpIfLyk5v7G4T_uusYsO92zT7PZPTMQsCbTWYj5XeNcw4w5eIPEDu8LPu_rqUU1IVkUOAaQVtvJZqYwWPZmRoRj6gPO5T0PAn2LDYfEUMs29xOkh3Z9mKTXGKsY_ioNEUtJ5bp2H0NtrVZgVkCQ-fUjvZujNQPb3_IlmZvblMrkKe8hZ4dZbKX0bTifa4UWXH-jlYqwydDw6QPzw1r0Sgw9KWkRm3bgw2qnfp-sA2yQP1dEu_uJVs4z4nLv3d2As8pHJrhnLUuuDuEJJk35afMtvkuhviWqjJ3f6seZutApJc9UYIQP3sDiI7BO8seF1fKhc2UYaQK36ttpxvONpOhFr7DC3gimWGQkIe_sSPwfdGzhb7ANNX1TH_mZZaqdzE_zNwaX97jaALYgNh_RfhaxR2OLWHVFGetOyYuTHXykcUlcbcN-qI9JzeNnRK1yV-aS7vcHXRhVa2CJInLZEKwnce0Skk0CdKil7kyLIPtQUcu3sKSp7MoZUHQtNB7PMfKjMKBChx_e62U7Uftin2RMIdUxCVW2uSPLdU-JgwdL9wun1U-LkMi_jFPeVxDcMKt0y1ljhTQXpiBDGVy0_hYD2fgPkpa6Wc27Tahi6RkWUBcONJunBEkjgvrDLil2k9a6EamYEamodXnFIEoAdBbifIaBtMfKITj0GW-M7EQBiqpa9UuisvA.uKq7TZAxXl-5wKGQlVMeSg@praxis-688567299207.d.codeartifact.eu-west-1.amazonaws.com/pypi/agents/simple/https://aws:eyJ2ZXIiOjEsImlzdSI6MTc0ODg2NjE5MiwiZW5jIjoiQTEyOEdDTSIsInRhZyI6Ik0tNEpNckFXM19IR19XWUVqM3Z2ZnciLCJleHAiOjE3NDg5MDkzOTIsImFsZyI6IkExMjhHQ01LVyIsIml2IjoiX2xuUXY1QmtCaDR5ZXlFdiJ9.1OOyXXtXjsDVn16BIOlHXw.PDR7wOOTUT8YxgTt.VL8dWgSckwjdbnOvgfI1acOeV6Z9Bu5jxx5MuKULfphp1SGR7VUGld5C3AEjybu3TuZu5OQE1Y6tX5R_FM5f-cQ0MeKK_QVyFJ1Du8nHV2F6q9EM8j1xagMZlrDarWNYNj_L22zNCLYlh_pK_DwnZl4p05oTsql6JUh0vyvP2U5TYBuqrZ6hw_5QGo12eYwyGOoJ1w_Bnz-HoR9oee4RGP1PMFPvsZ5DoOoREWjO8xIFLUrGUBUCjNjzrZEMgcuLiVc_CHxKd-Q005p5zdI7YEeoRGyMC-px3lEN5k1BZ18gbD4Rw0wqU8FUR-JPCWtdh4rrk7mjwjI5STvlR3N2xTRnMmZ1zW34BM3E2r4uUTb4NPl_r0ndFBLWnDT2kVHmCZONFvN4HbUvYgTV48O_CSCRpTLl7z9qxXhe-hWhIikrWIeFM7qjZr9kYFIi9dDPF9CE8uuQ1MklvGMvS2fglVr4BiVk1qgnLyNtdCSldLpe8_Dlsx8BlztkeE6di-cXxGqcw6C3oX5SjxWg1WK5godkdDT-Yr4Gxwvy-A3wRfaJUq0bWASxV_LGyxvPpoR7tv2QwN_LMsJSTSChn_CnkjABOP5vJavsk8rZgBaOPpIfLyk5v7G4T_uusYsO92zT7PZPTMQsCbTWYj5XeNcw4w5eIPEDu8LPu_rqUU1IVkUOAaQVtvJZqYwWPZmRoRj6gPO5T0PAn2LDYfEUMs29xOkh3Z9mKTXGKsY_ioNEUtJ5bp2H0NtrVZgVkCQ-fUjvZujNQPb3_IlmZvblMrkKe8hZ4dZbKX0bTifa4UWXH-jlYqwydDw6QPzw1r0Sgw9KWkRm3bgw2qnfp-sA2yQP1dEu_uJVs4z4nLv3d2As8pHJrhnLUuuDuEJJk35afMtvkuhviWqjJ3f6seZutApJc9UYIQP3sDiI7BO8seF1fKhc2UYaQK36ttpxvONpOhFr7DC3gimWGQkIe_sSPwfdGzhb7ANNX1TH_mZZaqdzE_zNwaX97jaALYgNh_RfhaxR2OLWHVFGetOyYuTHXykcUlcbcN-qI9JzeNnRK1yV-aS7vcHXRhVa2CJInLZEKwnce0Skk0CdKil7kyLIPtQUcu3sKSp7MoZUHQtNB7PMfKjMKBChx_e62U7Uftin2RMIdUxCVW2uSPLdU-JgwdL9wun1U-LkMi_jFPeVxDcMKt0y1ljhTQXpiBDGVy0_hYD2fgPkpa6Wc27Tahi6RkWUBcONJunBEkjgvrDLil2k9a6EamYEamodXnFIEoAdBbifIaBtMfKITj0GW-M7EQBiqpa9UuisvA.uKq7TZAxXl-5wKGQlVMeSg@praxis-688567299207.d.codeartifact.eu-west-1.amazonaws.com/pypi/tools/simple/


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
