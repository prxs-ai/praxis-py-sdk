from enum import Enum


class EntrypointGroup(str, Enum):
    APP_ENTRYPOINT = "provider.entrypoint"

    def __str__(self):
        return self.value

    @property
    def group_name(self):
        return str(self)
