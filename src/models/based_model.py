from datetime import datetime, timezone
from sqlmodel import SQLModel, Field

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class BaseModel(SQLModel):
    id: int | None = Field(default=None, primary_key=True)

    created: datetime = Field(default_factory=utcnow)
    updated: datetime = Field(default_factory=utcnow)

    created_by: int | None = Field(default=None)
    updated_by: int | None = Field(default=None)

    version: int = Field(default=1)
    is_del: bool = Field(default=False)