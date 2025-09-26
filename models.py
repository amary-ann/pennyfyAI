from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    user_id: str
    user_query: str

class ChatResponse(BaseModel):
    response: str