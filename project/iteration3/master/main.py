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
logger = logging.getLogger("master3")

app = FastAPI()

messages = []
current_id = 0


SECONDARIES = os.getenv(
    "SECONDARIES",
    "http://secondary1:8001,http://secondary2:8001,http://secondary3:8001"
).split(",")


RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))

class AppendRequest(BaseModel):
    message: str
    w: int  

async def replicate_until_success(url: str, msg_id: int, message: str):
   
    attempt = 0
    while attempt < MAX_RETRIES:
        attempt += 1
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{url}/replicate",
                    json={"msg_id": msg_id, "message": message}
                )
                resp.raise_for_status()
                logger.info(
                    f"Master3: replicate_until_success succeeded for msg_id={msg_id} → {url} "
                    f"(attempt {attempt}/{MAX_RETRIES})"
                )
                return
        except Exception as e:
            logger.warning(
                f"Master3: replicate_until_success attempt {attempt}/{MAX_RETRIES} "
                f"failed for msg_id={msg_id} → {url}: {e}"
            )
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)

    logger.error(
        f"Master3: replicate_until_success gave up for msg_id={msg_id} → {url} "
        f"after {MAX_RETRIES} attempts"
    )

async def replicate_and_count_once(url: str, msg_id: int, message: str) -> bool:
   
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{url}/replicate",
                json={"msg_id": msg_id, "message": message}
            )
            resp.raise_for_status()
            logger.info(f"Master3: synchronous sent msg_id={msg_id} to {url} (ACK)")
            return True
    except Exception as e:
        logger.error(f"Master3: replicate_and_count_once error for msg_id={msg_id} → {url}: {e}")
        return False

@app.post("/append")
async def append_message(req: AppendRequest):
    
    global current_id

    new_id = current_id + 1
    current_id = new_id
    messages.append((new_id, req.message))
    logger.info(f"Master3: received '{req.message}' with msg_id={new_id}, w={req.w}")

    if req.w == 1:
        for url in SECONDARIES:
            logger.info(
                f"Master3: scheduling background replicate_until_success for msg_id={new_id} → {url}"
            )
            asyncio.create_task(replicate_until_success(url, new_id, req.message))
        return {"status": "OK", "msg_id": new_id}

    required_acks = min(req.w - 1, len(SECONDARIES))
    ack_count = 0

    tasks = {
        asyncio.create_task(replicate_and_count_once(url, new_id, req.message)): url
        for url in SECONDARIES
    }

    for coro in asyncio.as_completed(tasks):
        success = await coro
        if success:
            ack_count += 1
            if ack_count >= required_acks:
                break

    if ack_count < required_acks:
        raise HTTPException(
            status_code=500,
            detail=f"Got only {ack_count} ACKs (required {required_acks})"
        )

    logger.info(f"Master3: received {ack_count} ACKs (required {required_acks}), replying to client")

    for url in SECONDARIES:
        logger.info(
            f"Master3: scheduling background replicate_until_success for msg_id={new_id} → {url} (post-sync)"
        )
        asyncio.create_task(replicate_until_success(url, new_id, req.message))

    return {"status": "OK", "msg_id": new_id}

@app.get("/messages")
def get_messages():
  
    return {"messages": [{"msg_id": mid, "message": m} for mid, m in messages]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
