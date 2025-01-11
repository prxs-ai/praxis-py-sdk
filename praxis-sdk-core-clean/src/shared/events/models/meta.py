from .base import Model
from .timedelta import Timedelta


class EventMeta(Model):
    id: str | None = None
    created_at: Timedelta | None = None
