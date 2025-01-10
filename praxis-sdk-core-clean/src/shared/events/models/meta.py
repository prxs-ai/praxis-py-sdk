from datetime import datetime

from .base import Model


class EventMeta(Model):
    id: bytes | None = None
    created_at: datetime | None = None
