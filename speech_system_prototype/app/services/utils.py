from __future__ import annotations

import re
import uuid
from typing import Optional


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def normalize(text: str) -> str:
    t = text.strip()
    t = re.sub(r"\s+", " ", t)
    return t
