import json
import asyncio

from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI
from contextlib import asynccontextmanager
from typing import List, Dict, Any

KAFKA_TOPIC = "messages"
KAFKA_BOOTSTRAP_SERVERS = [
    "localhost:9092",
    "localhost:9093",
    "localhost:9094",
]

messages: List[Dict[str, Any]] = []

async def consume_messages(consumer: AIOKafkaConsumer):
  
    try:
        async for msg in consumer:
            print('Отримано', msg.value)
            messages.append(msg.value)
    except asyncio.CancelledError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):

    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="group"
    )

    try:
        await consumer.start()
    except Exception as e:
        print(f"Не вдалося запустити Консюмер {e}")
        await consumer.stop()
        raise e

    app.state.consumer = consumer
    task = asyncio.create_task(consume_messages(consumer))

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await consumer.stop()


app = FastAPI(lifespan=lifespan)


@app.get("/messages")
async def get_messages():
   
    return messages
