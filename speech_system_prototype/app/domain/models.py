from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DeviceType(str, Enum):
    THERMOSTAT = "thermostat"
    VACUUM = "vacuum"
    CAMERA = "camera"
    COFFEE = "coffee"
    AC = "ac"
    LIGHT = "light"
    TV = "tv"


@dataclass
class Device:
    id: str
    name: str
    type: DeviceType
    is_on: bool = False
    # Optional numeric parameter, e.g., temperature for AC/thermostat
    value: Optional[float] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Settings:
    voice_answers: bool = True
    auto_confirm: bool = False
    noise_suppression: bool = True
    emergency_commands: bool = True

    voice_timbre: str = "Женский"
    speech_speed: float = 1.0  # 0.5..1.5
    volume: int = 80  # 0..100
    tone: str = "Стандартный"


@dataclass
class ChatMessage:
    role: str  # "user" | "system"
    text: str
    ts: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Operation:
    id: str
    name: str
    status: str  # "running" | "done" | "failed" | "canceled"
    details: Dict[str, Any] = field(default_factory=dict)
    ts: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SpecialCommandSequence:
    name: str
    description: str
    steps: List[str]
    ts: datetime = field(default_factory=datetime.utcnow)
