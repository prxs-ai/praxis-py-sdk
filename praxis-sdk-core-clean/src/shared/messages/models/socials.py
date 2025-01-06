from typing import Any

from .base import Base


class SocialsData(Base):
    source: str
    content: str
    metadata: dict[str, Any] | None = None
