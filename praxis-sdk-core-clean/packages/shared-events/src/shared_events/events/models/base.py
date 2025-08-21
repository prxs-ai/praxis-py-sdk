from typing import Any, ClassVar

from pydantic import BaseModel

from .topic import Topic


class Model(BaseModel):
    __topics__: ClassVar[tuple[Topic, ...] | None] = None

    def dump(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)
