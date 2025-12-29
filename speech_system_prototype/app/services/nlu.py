from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Intent:
    name: str
    device: Optional[str] = None  # device type hint
    value: Optional[float] = None
    raw: str = ""


class RuleNLU:
    """
    Very small rule-based NLU stub:
    - detect device control commands
    - detect emergency commands
    - detect special command sequence by name
    """

    _re_temp = re.compile(r"(уменьши|понизь|поставь|установи).*(температур\w*).*(до)\s*(\d{1,2})", re.IGNORECASE)
    _re_light_on = re.compile(r"(включи|вруби)\s+(свет|ламп\w*)", re.IGNORECASE)
    _re_light_off = re.compile(r"(выключи|выруби)\s+(свет|ламп\w*)", re.IGNORECASE)
    _re_pause = re.compile(r"\b(пауза|pause)\b", re.IGNORECASE)
    _re_stop = re.compile(r"\b(стоп|stop)\b", re.IGNORECASE)
    _re_tea = re.compile(r"\b(хочу чай|сделай чай|чай)\b", re.IGNORECASE)

    def parse(self, text: str) -> Intent:
        t = text.strip()

        m = self._re_stop.search(t)
        if m:
            return Intent(name="emergency_stop", raw=t)

        m = self._re_pause.search(t)
        if m:
            return Intent(name="emergency_pause", raw=t)

        m = self._re_temp.search(t)
        if m:
            value = float(m.group(4))
            return Intent(name="set_temperature", device="ac", value=value, raw=t)

        if self._re_light_on.search(t):
            return Intent(name="light_on", device="light", raw=t)

        if self._re_light_off.search(t):
            return Intent(name="light_off", device="light", raw=t)

        if self._re_tea.search(t):
            return Intent(name="make_tea", device="kettle", raw=t)

        return Intent(name="unknown", raw=t)
