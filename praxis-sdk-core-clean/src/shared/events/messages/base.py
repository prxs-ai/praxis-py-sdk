from typing import Any, ClassVar, Self

from pydantic import BaseModel


class Message(BaseModel):
    __topic__: ClassVar[str]

    def to_dict(self, include_topic: bool = False) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, **kwargs: Any) -> Self:
        return cls(**kwargs)
