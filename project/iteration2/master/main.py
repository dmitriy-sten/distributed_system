import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import asyncio
import logging
import os


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("master2")


app = FastAPI()

messages = []
current_id = 0

SECONDARIES = os.getenv(
    "SECONDARIES",
    "http://secondary1:8001,http://secondary2:8001"
).split(",")

class AppendRequest(BaseModel):
    message: str
    w: int  

async def send_to_secondary_background(url: str, msg_id: int, message: str):
   
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{url}/replicate",
                json={"msg_id": msg_id, "message": message}
            )
            resp.raise_for_status()
            logger.info(f"Master2: background sent msg_id={msg_id} to {url}")
    except Exception as e:
        logger.warning(f"Master2: background replication to {url} failed: {e}")

async def replicate_and_count(url: str, msg_id: int, message: str) -> bool:

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{url}/replicate",
                json={"msg_id": msg_id, "message": message}
            )
            resp.raise_for_status()
            logger.info(f"Master2: synchronous sent msg_id={msg_id} to {url} (ACK)")
            return True
    except Exception as e:
        logger.error(f"Master2: replication error to {url}: {e}")
        return False

@app.post("/append")
async def append_message(req: AppendRequest):
    
    global current_id

    new_id = current_id + 1
    current_id = new_id
    messages.append((new_id, req.message))
    logger.info(f"Master2: received '{req.message}' with msg_id={new_id}, w={req.w}")

    if req.w == 1:
        for url in SECONDARIES:
            logger.info(f"Master2: scheduling background task for msg_id={new_id} → {url}")
            asyncio.create_task(send_to_secondary_background(url, new_id, req.message))
        return {"status": "OK", "msg_id": new_id}

    required_acks = min(req.w - 1, len(SECONDARIES))
    ack_count = 0

    tasks = [replicate_and_count(url, new_id, req.message) for url in SECONDARIES]
    results = await asyncio.gather(*tasks)

    for success in results:
        if success:
            ack_count += 1
            if ack_count >= required_acks:
                break

    if ack_count < required_acks:
        raise HTTPException(
            status_code=500,
            detail=f"Got only {ack_count} ACKs, required {required_acks}"
        )

    logger.info(f"Master2: received {ack_count} ACKs (required {required_acks}), replying to client")

    for url in SECONDARIES:
        logger.info(f"Master2: scheduling background task for msg_id={new_id} → {url} (post-sync)")
        asyncio.create_task(send_to_secondary_background(url, new_id, req.message))

    return {"status": "OK", "msg_id": new_id}

@app.get("/messages")
def get_messages():
    
    return {"messages": [{"msg_id": mid, "message": m} for mid, m in messages]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
