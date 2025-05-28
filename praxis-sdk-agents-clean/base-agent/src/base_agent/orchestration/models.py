from pydantic import BaseModel


class WorkflowSettings(BaseModel):
    enabled: bool = True
