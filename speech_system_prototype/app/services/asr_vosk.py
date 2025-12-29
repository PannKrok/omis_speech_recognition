from __future__ import annotations

import json
import os
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from vosk import KaldiRecognizer, Model


@dataclass
class TranscriptionResult:
    text: str
    confidence: float


class VoskTranscriber:
    """Offline ASR via Vosk.

    Notes:
    - Expects mono 16 kHz PCM WAV.
    - Model is loaded lazily on first request (can take a few seconds).
    """

    def __init__(self, model_path: Optional[str] = None, sample_rate: int = 16000):
        self.model_path = model_path or os.getenv("VOSK_MODEL_PATH", "").strip()
        self.sample_rate = sample_rate
        self._model: Optional[Model] = None

    def _load_model(self) -> Model:
        if self._model is not None:
            return self._model

        if not self.model_path:
            raise RuntimeError(
                "VOSK model path is not set. "
                "Set env var VOSK_MODEL_PATH or put model into ./models and set path in README."
            )

        p = Path(self.model_path)
        if not p.exists():
            raise RuntimeError(f"VOSK model path does not exist: {p}")

        self._model = Model(str(p))
        return self._model

    def transcribe_wav_bytes(self, wav_bytes: bytes) -> TranscriptionResult:
        model = self._load_model()

        # Read WAV header + data from bytes using wave module
        import io

        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            channels = wf.getnchannels()
            rate = wf.getframerate()
            sampwidth = wf.getsampwidth()
            if channels != 1 or rate != self.sample_rate or sampwidth != 2:
                raise ValueError(
                    f"Unsupported WAV format: channels={channels}, rate={rate}, sampwidth={sampwidth}. "
                    f"Need mono 16kHz PCM16."
                )

            rec = KaldiRecognizer(model, self.sample_rate)
            rec.SetWords(True)

            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                rec.AcceptWaveform(data)

            final = json.loads(rec.FinalResult() or "{}")

        text = (final.get("text") or "").strip()
        words = final.get("result") or []
        confs = [w.get("conf", 0.0) for w in words if isinstance(w, dict)]
        confidence = float(sum(confs) / max(len(confs), 1)) if confs else 0.0

        return TranscriptionResult(text=text, confidence=confidence)
