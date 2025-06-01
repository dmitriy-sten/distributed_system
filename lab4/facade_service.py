from contextlib import asynccontextmanager
import os
import random
import uuid
import json
from aiokafka import AIOKafkaProducer
import requests
from fastapi import FastAPI, HTTPException

CONFIG_SERVER_URL = os.getenv("CONFIG_SERVER_URL", "http://localhost:8000")
LOGGING_SERVICE_NAME = "logging-service"
MESSAGES_SERVICE_NAME = "messages-service"

KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "messages")

KAFKA_BOOTSTRAP_SERVICES = ["localhost:9092", "localhost:9093", "localhost:9094"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVICES,
        value_serializer=lambda m: json.dumps(m).encode("utf-8"),
        
    )
    await producer.start()
    app.state.producer = producer
    yield
    await producer.stop()


app = FastAPI(lifespan=lifespan)


def get_service_instances(service_name: str) -> list[str]:
    try:
        r = requests.get(f"{CONFIG_SERVER_URL}/services/{service_name}", timeout=3)
        r.raise_for_status()
        return r.json().get("instances", [])
    except Exception as e:
        raise HTTPException(503, f"Не вдалося отримати інстанси '{service_name}': {e}")


@app.post("/message")
async def post_message(message: dict):
    message_id = str(uuid.uuid4())
    payload = {"id": message_id, "msg": message.get("msg")}

    try:
        await app.state.producer.send_and_wait(KAFKA_TOPIC, payload)
    except Exception as e:
        raise HTTPException(500, f"Помилка публікації в Kafka: {e}")

    print("br")

    instances = get_service_instances(LOGGING_SERVICE_NAME)
    if not instances:
        raise HTTPException(503, "Немає доступних інстансів logging-service")

    last_err = None
    for inst in random.sample(instances, len(instances)):
        try:
            r = requests.post(f"{inst}/log", json=payload, timeout=3)
            r.raise_for_status()
            break
        except Exception as e:
            last_err = e
    else:
        raise HTTPException(500, f"Не вдалося записати лог: {last_err}")

    return {"message_id": message_id, "message": message.get("msg")}


@app.get("/message")
def get_message():
    log_instances = get_service_instances(LOGGING_SERVICE_NAME)
    if not log_instances:
        raise HTTPException(503, "Немає доступних інстансів logging-service")
    log_resp = None
    for inst in random.sample(log_instances, len(log_instances)):
        try:
            r = requests.get(f"{inst}/logs", timeout=10)
            r.raise_for_status()
            log_resp = r.json()
            break
        except:
            continue
    else:
        log_resp = "Помилка отримання логів"

    msg_instances = get_service_instances(MESSAGES_SERVICE_NAME)
    if not msg_instances:
        raise HTTPException(503, "Немає доступних інстансів messages-service")
    msg_resp = None
    for inst in random.sample(msg_instances, len(msg_instances)):
        try:
            r = requests.get(f"{inst}/messages", timeout=10)
            r.raise_for_status()
            msg_resp = r.json()
            break
        except:
            continue
    else:
        msg_resp = "Помилка отримання повідомлень"

    return {"logging_service": log_resp, "messages_service": msg_resp}
