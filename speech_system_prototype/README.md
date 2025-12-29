# Speech Control Prototype (FastAPI)

Это прототип "интеллектуальной системы распознавания речи" с backend + web UI (заглушки устройств и распознавания).

## Запуск

1) Создай venv и поставь зависимости:
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```

2) Запусти сервер:
```bash
uvicorn app.main:app --reload
```

3) Открой в браузере:
- http://127.0.0.1:8000

## Что внутри

- `/` — web UI (чат + настройки + устройства)
- `/api/chat/send` — отправка команды
- `/api/state` — текущее состояние (настройки, устройства)
- `/api/devices/*` — управление устройствами (заглушки)
- `/api/history` — история сообщений/операций

## Примеры команд (вводи в чат)

- "уменьшить температуру до 22"
- "включи свет"
- "выключи свет"
- "пауза"
- "стоп"
- "я хочу чай"


## Offline распознавание речи (Vosk)

UI пишет звук с микрофона и отправляет WAV (моно, 16 кГц) на backend: `POST /api/asr/transcribe`.

### 1) Установи зависимости
```bash
pip install -r requirements.txt
```

### 2) Скачай модель Vosk (RU)
Скачай русскую модель и распакуй в папку `models/`, например:
- `models/vosk-model-small-ru-0.22/`

Официальный репозиторий Vosk: см. документацию. citeturn0search6turn0search9

### 3) Укажи путь к модели
Вариант A (env var):
```bash
set VOSK_MODEL_PATH=models\vosk-model-small-ru-0.22
```

Вариант B (PowerShell):
```powershell
$env:VOSK_MODEL_PATH="models\vosk-model-small-ru-0.22"
```

### 4) Запуск
```bash
uvicorn app.main:app --reload
```

Если модель не указана, backend вернёт ошибку и UI покажет подсказку.
