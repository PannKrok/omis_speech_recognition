from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Optional

from .models import ChatMessage, Device, Operation, Settings, SpecialCommandSequence


class InMemoryStore:
    """
    Simple in-memory storage. This is intentionally a stub to match the project "design"
    without bringing a real DB.
    """

    def __init__(self) -> None:
        self.settings: Settings = Settings()
        self.devices: Dict[str, Device] = {}
        self.chat: List[ChatMessage] = []
        self.operations: List[Operation] = []
        self.service_words: List[str] = ["Система", "Алиса"]
        self.sequences: Dict[str, SpecialCommandSequence] = {}

    def dump_state(self) -> dict:
        return {
            "settings": asdict(self.settings),
            "devices": [asdict(d) for d in self.devices.values()],
            "service_words": list(self.service_words),
            "sequences": {k: asdict(v) for k, v in self.sequences.items()},
            "chat": [{"role": m.role, "text": m.text, "ts": m.ts.isoformat()} for m in self.chat[-200:]],
            "operations": [{"id": o.id, "name": o.name, "status": o.status, "details": o.details, "ts": o.ts.isoformat()} for o in self.operations[-200:]],
        }
