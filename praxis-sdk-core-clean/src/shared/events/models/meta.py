from uuid import UUID

from .base import Model
from .timedelta import Timedelta


class EventMeta(Model):
    id: str | None = None
    created_at: Timedelta | None = None

    @property
    def id_as_uuid(self) -> UUID | None:
        return UUID(hex=self.id) if self.id else None
