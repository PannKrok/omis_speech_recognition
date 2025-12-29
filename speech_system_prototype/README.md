# Speech Control Prototype (FastAPI)

Это прототип "интеллектуальной системы распознавания речи" с backend + web UI (заглушки устройств и распознавания).

## Запуск

1) Создать venv и поставь зависимости:
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```
2) Скачать модель Vosk (RU)
Скачать русскую модель и распаковать в папку `models/`, например:
- `models/vosk-model-small-ru-0.22/`

Официальный репозиторий Vosk: см. документацию. [citeturn0search6turn0search9](https://alphacephei.com/vosk/models)

3) Указать путь к модели
Вариант A (env var):
```bash
set VOSK_MODEL_PATH=models\vosk-model-small-ru-0.22
```

Вариант B (PowerShell):
```powershell
$env:VOSK_MODEL_PATH="models\vosk-model-small-ru-0.22"
```


4) Запустить сервер:
```bash
uvicorn app.main:app --reload
```

5) Открыть в браузере:
- http://127.0.0.1:8000

## Что внутри

- `/` — web UI (чат + настройки + устройства)
- `/api/chat/send` — отправка команды
- `/api/state` — текущее состояние (настройки, устройства)
- `/api/devices/*` — управление устройствами (заглушки)
- `/api/history` — история сообщений/операций

## Примеры команд (ввести в чат)

- "уменьшить температуру до 22"
- "включи свет"
- "выключи свет"
- "пауза"
- "стоп"
- "я хочу чай"








