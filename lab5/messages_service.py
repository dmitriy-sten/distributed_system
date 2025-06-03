import os
import sys
import socket
import uuid
import atexit
import json
import base64
import requests
import asyncio

from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn

SERVICE_NAME = "messages-service"
SERVICE_PORT = int(os.getenv("MESSAGES_PORT", 8002))
CONSUL_ADDRESS = os.getenv("CONSUL_ADDRESS", "http://localhost:8500")
SERVICE_ID = f"{SERVICE_NAME}-{uuid.uuid4()}"

kafka_consumer = None
consumer_task = None
messages = []

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"
    finally:
        s.close()

def register_in_consul():
    ip = get_local_ip()
    url = f"{CONSUL_ADDRESS}/v1/agent/service/register"
    payload = {
        "Name": SERVICE_NAME,
        "ID": SERVICE_ID,
        "Address": ip,
        "Port": SERVICE_PORT,
        "Check": {
            "HTTP": f"http://{ip}:{SERVICE_PORT}/health",
            "Interval": "10s",
            "Timeout": "3s"
        }
    }
    r = requests.put(url, json=payload, timeout=3)
    r.raise_for_status()

def deregister_from_consul():
    url = f"{CONSUL_ADDRESS}/v1/agent/service/deregister/{SERVICE_ID}"
    try:
        r = requests.put(url, timeout=3)
        r.raise_for_status()
    except:
        pass

def load_kafka_config():
    url = f"{CONSUL_ADDRESS}/v1/kv/kafka/config"
    r = requests.get(url, timeout=3)
    r.raise_for_status()
    data = r.json()
    raw = data[0]["Value"]
    return json.loads(base64.b64decode(raw).decode("utf-8"))

async def consume_loop():
    global kafka_consumer, messages
    try:
        async for msg in kafka_consumer:
            print('Отримано', msg.value)
            messages.append(msg.value)
    except asyncio.CancelledError:
        return

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "UP"}


@app.get("/messages")
async def get_messages():
    return messages

@asynccontextmanager
async def lifespan(app: FastAPI):
    global kafka_consumer, consumer_task
    try:
        register_in_consul()
    except:
        sys.exit(1)
    try:
        kc = load_kafka_config()
    except:
        deregister_from_consul()
        sys.exit(1)
    bootstrap_servers = kc.get("bootstrap_servers", [])
    topic = kc.get("topic", "messages")
    if not bootstrap_servers:
        deregister_from_consul()
        sys.exit(1)
    kafka_consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="group"
    )
    try:
        await kafka_consumer.start()
    except:
        deregister_from_consul()
        sys.exit(1)
    consumer_task = asyncio.create_task(consume_loop())
    atexit.register(deregister_from_consul)
    yield
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
    if kafka_consumer:
        await kafka_consumer.stop()
    deregister_from_consul()

app.router.lifespan_context = lifespan

if __name__ == "__main__":
    uvicorn.run("messages_service:app", host="0.0.0.0", port=SERVICE_PORT, reload=False)
