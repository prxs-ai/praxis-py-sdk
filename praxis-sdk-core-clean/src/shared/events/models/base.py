from typing import ClassVar

from pydantic import BaseModel

from services.shared.events.proto import Proto

from .topic import Topics


class Model(BaseModel):
    __proto__: ClassVar[type[Proto] | None] = None
    __topics__: ClassVar[tuple[Topics, ...] | None] = None
