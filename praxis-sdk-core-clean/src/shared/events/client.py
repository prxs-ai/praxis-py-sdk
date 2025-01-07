from typing import Final

from confluent_kafka.schema_registry import SchemaRegistryClient  # type: ignore

_Arg2ConfKey: Final[dict[str, str]] = {
    "url": "url",
    "auth": "basic.auth.user.info",
    "timeout": "timeout",
    "max_retries": "max.retries",
}


def init_client(
    url: str,
    auth: str | None = None,
    timeout: int | None = None,
    max_retries: int | None = None,
) -> SchemaRegistryClient:
    conf = {_Arg2ConfKey[key]: val for key, val in vars().items() if val is not None}
    return SchemaRegistryClient(**conf)
