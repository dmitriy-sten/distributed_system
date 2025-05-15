import os
import random
import requests
import uuid
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

CONFIG_SERVER_URL = os.getenv("CONFIG_SERVER_URL", "http://127.0.0.1:8000")
LOGGING_SERVICE_NAME = "logging-service"
MESSAGES_SERVICE_NAME = "messages-service"

class Message(BaseModel):
    msg: str

def get_service_instances(service_name: str) -> list[str]:
    try:
        resp = requests.get(f"{CONFIG_SERVER_URL}/services/{service_name}", timeout=5)
        resp.raise_for_status()
        
        print('Отримано налаштування')
        return resp.json().get("instances", [])
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Не вдалося отримати список `{service_name}`: {e}",
        )

@app.post("/message")
def post_message(message: Message):
    message_id = str(uuid.uuid4())
    payload = {"id": message_id, "msg": message.msg}

    instances = get_service_instances(LOGGING_SERVICE_NAME)
    print(f'Обрано - {instances}')
    
    if not instances:
        raise HTTPException(status_code=503, detail="Немає доступних інстансів logging-service")

    last_error = None
    for inst in random.sample(instances, len(instances)):
        for attempt in range(3):
            try:
                r = requests.post(f"{inst}/log", json=payload, timeout=5)
                r.raise_for_status()
                return {"message_id": message_id, "message": message.msg}
            except Exception as e:
                last_error = e
                time.sleep(2)
    raise HTTPException(status_code=500, detail=f"Не вдалося надіслати повідомлення: {last_error}")

@app.get("/message")
def get_message():
    log_instances = get_service_instances(LOGGING_SERVICE_NAME)
    print(f'Обрано - {log_instances}')
    if not log_instances:
        raise HTTPException(status_code=503, detail="Немає інстансів logging-service")
    logs_str = ""
    for _ in range(len(log_instances)):
        inst = random.choice(log_instances)
        try:
            r = requests.get(f"{inst}/logs", timeout=5)
            r.raise_for_status()
            data = r.json()
            logs_str = ", ".join(data) if isinstance(data, list) else str(data)
            break
        except Exception:
            continue
    else:
        logs_str = "Помилка отримання логів від logging-service"

    msg_instances = get_service_instances(MESSAGES_SERVICE_NAME)
    if not msg_instances:
        raise HTTPException(status_code=503, detail="Немає інстансів messages-service")
    static_msg = ""
    for _ in range(len(msg_instances)):
        inst = random.choice(msg_instances)
        try:
            r = requests.get(f"{inst}/static", timeout=5)
            r.raise_for_status()
            static_msg = r.text
            break
        except Exception:
            continue
    else:
        static_msg = "Помилка отримання повідомлення від messages-service"

    combined = f"{logs_str} | {static_msg}"
    return {"combined": combined}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("facade_service:app", host="0.0.0.0", port=int(os.getenv("PORT", 8010)), reload=True)
