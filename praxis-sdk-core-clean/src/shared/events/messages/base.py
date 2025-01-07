from typing import Any, Self

from pydantic import BaseModel


class Message(BaseModel):
    @classmethod
    def from_dict(cls, **kwargs: Any) -> Self:
        return cls(**kwargs)
