from enum import Enum


class DefaultSinkEntrypointType(str, Enum):
    """Default sink type."""

    BASIC = "basic"
    KAFKA = "kafka"

    def __str__(self) -> str:
        return self.value

    @staticmethod
    def all():
        return {DefaultSinkEntrypointType.BASIC, DefaultSinkEntrypointType.KAFKA}
