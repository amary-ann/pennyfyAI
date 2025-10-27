from beanie import Document, Update, Save, SaveChanges, Replace, Insert, before_event
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, timezone
from bson import Decimal128
from typing import Any, List
from decimal import Decimal

def get_utc_now():
    return datetime.now(timezone.utc)

class BaseDocument(Document):
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)

    @before_event(Insert)
    def set_created_at(self) -> None:
        self.created_at = get_utc_now()

    @before_event(Update, Save, SaveChanges, Replace)
    def set_updated_at(self) -> None:
        self.updated_at = get_utc_now()


class Message(BaseDocument):
    message: str
    is_user: bool

class Request(BaseModel):
    user_id: str
    message: str

class Session(BaseDocument):
    user_id: str
    chats: List[Message] = []
    is_active: bool = True
    does_user_exist: bool = False
    chat_phase: str = 'default'

    class Settings:
        name = "sessions"