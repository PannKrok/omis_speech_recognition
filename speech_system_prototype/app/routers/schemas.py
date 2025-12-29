from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatSendRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class ChatSendResponse(BaseModel):
    messages: List[str]
    action: Dict[str, Any] = {}
    intent: Optional[str] = None


class SettingsUpdateRequest(BaseModel):
    voice_answers: Optional[bool] = None
    auto_confirm: Optional[bool] = None
    noise_suppression: Optional[bool] = None
    emergency_commands: Optional[bool] = None

    voice_timbre: Optional[str] = None
    speech_speed: Optional[float] = None
    volume: Optional[int] = None
    tone: Optional[str] = None


class DeviceAddRequest(BaseModel):
    name: str
    type: str
    is_on: bool = False
    value: Optional[float] = None


class DeviceToggleRequest(BaseModel):
    is_on: bool


class DeviceValueRequest(BaseModel):
    value: float


class ServiceWordAddRequest(BaseModel):
    word: str


class SequenceAddRequest(BaseModel):
    name: str
    description: str = ""
    steps: List[str]
