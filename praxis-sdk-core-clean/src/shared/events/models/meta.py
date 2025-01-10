from datetime import datetime

from services.shared.events.proto import EventMeta as _EventMeta

from .base import Model
from .utils import register


@register(_EventMeta)
class EventMeta(Model):
    id: bytes | None
    created_at: datetime | None
