from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    history: List[Message] = Field(default=[], max_length=20)


class ChatResponse(BaseModel):
    answer: str
    history: List[Message]
