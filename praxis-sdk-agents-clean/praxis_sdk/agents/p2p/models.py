import pydantic


class HandOffRequest(pydantic.BaseModel):
    method: str
    path: str
    params: dict = pydantic.Field(default={})
    input_data: str | None = pydantic.Field(default=None)
