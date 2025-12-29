from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from app.domain.models import ChatMessage, Operation, Settings
from app.domain.repositories import InMemoryStore
from app.services.devices import DeviceManager
from app.services.nlu import RuleNLU
from app.services.utils import new_id, normalize


class Pipeline:
    """
    A stub of the "collection -> processing -> analysis -> decision -> response" flow.
    """

    def __init__(self, store: InMemoryStore) -> None:
        self.store = store
        self.nlu = RuleNLU()
        self.devices = DeviceManager(store.devices)
        self.active_operation_id: Optional[str] = None

    def handle_user_text(self, text: str) -> Dict[str, Any]:
        text = normalize(text)
        self._add_chat("user", text)

        # 1) "collect" (stub)
        self._op("Сбор данных", "done", {"input": "text"})

        # 2) "process" (stub)
        if self.store.settings.noise_suppression:
            self._op("Обработка данных", "done", {"noise_suppression": True})
        else:
            self._op("Обработка данных", "done", {"noise_suppression": False})

        # 3) "analysis" (NLU)
        intent = self.nlu.parse(text)
        self._op("Анализ данных", "done", {"intent": asdict(intent)})

        # 4) "decision"
        messages: List[str] = []
        messages.append("[бип]")  # activation sound in UI mockups

        # Emergency commands
        if intent.name in ("emergency_stop", "emergency_pause") and self.store.settings.emergency_commands:
            return self._handle_emergency(intent.name, messages)

        # Special sequences (by exact name)
        seq = self.store.sequences.get(text)
        if seq:
            return self._handle_sequence(seq.name, seq.steps, messages)

        # Device actions
        result = self._apply_intent(intent, messages)

        # 5) "response"
        for m in result["messages"]:
            self._add_chat("system", m)

        return result

    def _handle_emergency(self, kind: str, messages: List[str]) -> Dict[str, Any]:
        if self.active_operation_id:
            # cancel the last active operation
            for op in reversed(self.store.operations):
                if op.id == self.active_operation_id and op.status == "running":
                    op.status = "canceled"
                    op.details["reason"] = kind
                    break
            self.active_operation_id = None

        if kind == "emergency_pause":
            messages.append("Пауза. Я остановил текущие действия.")
        else:
            messages.append("Стоп. Я отменил текущие действия.")

        self._op("Принятие решений", "done", {"emergency": kind})

        return {"messages": messages, "action": {"type": kind}}

    def _handle_sequence(self, name: str, steps: List[str], messages: List[str]) -> Dict[str, Any]:
        self._op("Принятие решений", "done", {"sequence": name, "steps": steps})
        op_id = new_id("op")
        self.active_operation_id = op_id
        self.store.operations.append(Operation(id=op_id, name=f"Выполнение последовательности: {name}", status="running", details={"steps": steps}))

        for step in steps:
            # Re-run step via NLU to reuse logic
            intent = self.nlu.parse(step)
            self._apply_intent(intent, messages, add_bip=False)

        # finish
        for op in reversed(self.store.operations):
            if op.id == op_id:
                op.status = "done"
                break
        self.active_operation_id = None

        messages.append(f"Готово. Последовательность «{name}» выполнена.")
        return {"messages": messages, "action": {"type": "sequence", "name": name}}

    def _apply_intent(self, intent, messages: List[str], add_bip: bool = False) -> Dict[str, Any]:
        action: Dict[str, Any] = {"type": "none"}

        # A tiny resolver: pick first device by type if multiple.
        def first_device_of_type(t: str):
            for d in self.devices.list_devices():
                if d.type.value == t:
                    return d
            return None

        if intent.name == "set_temperature":
            d = first_device_of_type("ac") or first_device_of_type("thermostat")
            if not d:
                messages.append("Не нашёл устройство для управления температурой. Открой «Устройства» и добавь его.")
            else:
                self._op("Принятие решений", "done", {"device_id": d.id, "action": "set_temperature", "value": intent.value})
                op_id = new_id("op")
                self.active_operation_id = op_id
                self.store.operations.append(Operation(id=op_id, name="Изменение температуры", status="running", details={"device": d.name, "value": intent.value}))

                self.devices.toggle(d.id, True)
                self.devices.set_value(d.id, float(intent.value or 22))
                messages.append(f"Температура понижается до {int(intent.value or 22)} °C. Ожидайте охлаждения помещения в течение 5 минут.")
                action = {"type": "set_temperature", "device_id": d.id, "value": d.value}

                # finish
                for op in reversed(self.store.operations):
                    if op.id == op_id:
                        op.status = "done"
                        break
                self.active_operation_id = None

        elif intent.name == "light_on":
            d = first_device_of_type("light")
            if not d:
                messages.append("Не нашёл «умный свет». Открой «Устройства» и добавь его.")
            else:
                self._op("Принятие решений", "done", {"device_id": d.id, "action": "light_on"})
                self.devices.toggle(d.id, True)
                messages.append(f"Устройство «{d.name}» включено.")
                action = {"type": "device_toggle", "device_id": d.id, "is_on": True}

        elif intent.name == "light_off":
            d = first_device_of_type("light")
            if not d:
                messages.append("Не нашёл «умный свет». Открой «Устройства» и добавь его.")
            else:
                self._op("Принятие решений", "done", {"device_id": d.id, "action": "light_off"})
                self.devices.toggle(d.id, False)
                messages.append(f"Устройство «{d.name}» выключено.")
                action = {"type": "device_toggle", "device_id": d.id, "is_on": False}

        elif intent.name == "make_tea":
            # demo: just respond, no real robotics
            self._op("Принятие решений", "done", {"action": "make_tea"})
            messages.append("Уточнение: вы хотите зелёный чай как обычно или другой?")
            action = {"type": "ask_clarification", "topic": "tea_type"}

        else:
            self._op("Принятие решений", "done", {"action": "unknown"})
            messages.append("Я не понял команду. Попробуй: «включи свет» или «уменьшить температуру до 22».")

        return {"messages": messages, "action": action, "intent": intent.name}

    def _add_chat(self, role: str, text: str) -> None:
        self.store.chat.append(ChatMessage(role=role, text=text))

    def _op(self, name: str, status: str, details: Dict[str, Any]) -> None:
        self.store.operations.append(Operation(id=new_id("op"), name=name, status=status, details=details))
