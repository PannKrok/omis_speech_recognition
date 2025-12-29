from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.domain.models import ChatMessage, Device, DeviceType, SpecialCommandSequence
from app.domain.repositories import InMemoryStore
from app.services.asr_vosk import VoskTranscriber
from app.routers.schemas import (
    ChatSendRequest,
    ChatSendResponse,
    DeviceAddRequest,
    DeviceToggleRequest,
    DeviceValueRequest,
    SequenceAddRequest,
    ServiceWordAddRequest,
    SettingsUpdateRequest,
)
from app.services.devices import DeviceManager
from app.services.pipeline import Pipeline
from app.services.utils import clamp, new_id, normalize


def build_router(store: InMemoryStore, pipeline: Pipeline) -> APIRouter:
    router = APIRouter(prefix="/api")

    transcriber = VoskTranscriber()

    devices = DeviceManager(store.devices)

    @router.get("/state")
    def state():
        return store.dump_state()

    @router.get("/history")
    def history():
        return {
            "chat": [{"role": m.role, "text": m.text, "ts": m.ts.isoformat()} for m in store.chat[-200:]],
            "operations": [{"id": o.id, "name": o.name, "status": o.status, "details": o.details, "ts": o.ts.isoformat()} for o in store.operations[-200:]],
        }

    @router.post("/chat/send", response_model=ChatSendResponse)
    def chat_send(req: ChatSendRequest):
        result = pipeline.handle_user_text(req.text)
        return ChatSendResponse(messages=result.get("messages", []), action=result.get("action", {}), intent=result.get("intent"))

    @router.post("/settings")
    def update_settings(req: SettingsUpdateRequest):
        s = store.settings
        data = req.model_dump(exclude_none=True)

        for k, v in data.items():
            if k == "speech_speed":
                v = float(clamp(float(v), 0.5, 1.5))
            if k == "volume":
                v = int(clamp(int(v), 0, 100))
            setattr(s, k, v)

        return {"ok": True, "settings": asdict(store.settings)}

    @router.get("/devices")
    def list_devices():
        return [asdict(d) for d in devices.list_devices()]

    @router.post("/devices")
    def add_device(req: DeviceAddRequest):
        try:
            dt = DeviceType(req.type)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Unknown device type: {req.type}") from e

        d = Device(id=new_id("dev"), name=req.name, type=dt, is_on=req.is_on, value=req.value)
        devices.add_device(d)
        store.chat.append(ChatMessage(role="system", text=f"Устройство «{d.name}» добавлено."))
        return asdict(d)

    @router.delete("/devices/{device_id}")
    def remove_device(device_id: str):
        devices.remove_device(device_id)
        return {"ok": True}

    @router.post("/devices/{device_id}/toggle")
    def toggle_device(device_id: str, req: DeviceToggleRequest):
        try:
            d = devices.toggle(device_id, req.is_on)
        except KeyError:
            raise HTTPException(status_code=404, detail="Device not found")
        return asdict(d)

    @router.post("/devices/{device_id}/value")
    def set_device_value(device_id: str, req: DeviceValueRequest):
        try:
            d = devices.set_value(device_id, req.value)
        except KeyError:
            raise HTTPException(status_code=404, detail="Device not found")
        return asdict(d)

    @router.post("/special/service-word")
    def add_service_word(req: ServiceWordAddRequest):
        word = normalize(req.word)
        if not word:
            raise HTTPException(status_code=400, detail="Empty word")
        if word not in store.service_words:
            store.service_words.append(word)
        return {"ok": True, "service_words": store.service_words}

    @router.post("/special/sequence")
    def add_sequence(req: SequenceAddRequest):
        name = normalize(req.name)
        if not name:
            raise HTTPException(status_code=400, detail="Empty name")
        seq = SpecialCommandSequence(name=name, description=req.description, steps=req.steps)
        store.sequences[name] = seq
        return {"ok": True, "sequence": asdict(seq)}


    @router.post("/asr/transcribe")
    async def asr_transcribe(file: UploadFile = File(...)):
        """Transcribe uploaded mono 16kHz PCM WAV via offline Vosk."""
        try:
            data = await file.read()
            res = transcriber.transcribe_wav_bytes(data)
            if not res.text:
                return {"ok": True, "text": "", "confidence": res.confidence, "message": "Пустая расшифровка. Попробуйте говорить ближе к микрофону."}
            return {"ok": True, "text": res.text, "confidence": res.confidence}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ASR error: {e}")

    return router
