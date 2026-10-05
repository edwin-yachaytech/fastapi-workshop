from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TaskStatus = Literal["pending", "in_progress", "done"]


class TaskCreate(BaseModel):
    """Nota: NO incluye user_id. El dueno se obtiene del JWT, no del cliente."""

    title: str = Field(min_length=1, max_length=150, examples=["Prepare FastAPI workshop"])
    description: str | None = Field(default=None, examples=["Finish JWT and Swagger tests"])
    status: TaskStatus = "pending"


class TaskUpdate(BaseModel):
    """Para PATCH: todos los campos son opcionales."""

    title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    status: TaskStatus | None = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    status: str
    created_at: datetime
    user_id: int

    model_config = ConfigDict(from_attributes=True)
