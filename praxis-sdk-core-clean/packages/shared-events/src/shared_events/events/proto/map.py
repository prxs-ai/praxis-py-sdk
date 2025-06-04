from typing import Final, TypeVar

from services.shared.events import models

from . import schemas

_Model2Message: Final[dict[type[models.Model], type[schemas.Message]]] = {
    models.News: schemas.News,
    models.NewsMeta: schemas.NewsMeta,
    models.EventMeta: schemas.EventMeta,
    models.Source: schemas.Source,
}

C = TypeVar("C", bound=models.Message)


def get_message_type(cls: type[C]) -> type[schemas.Message]:
    try:
        return _Model2Message[cls]
    except KeyError as exc:
        raise ValueError(f"No protobuf message found for model: {cls}") from exc
