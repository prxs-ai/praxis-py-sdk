from .base import Model


class Timedelta(Model):
    seconds: float
    nanos: float
