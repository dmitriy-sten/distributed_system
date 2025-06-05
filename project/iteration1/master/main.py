import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("master")

app = FastAPI()

messages = []

SECONDARIES = os.getenv("SECONDARIES", "http://secondary1:8001,http://secondary2:8001").split(",")

class AppendRequest(BaseModel):
    message: str

@app.post("/append")
async def append_message(req: AppendRequest):
    new_msg = req.message
    messages.append(new_msg)
    logger.info(f"Master: received new message '{new_msg}', replicating to {len(SECONDARIES)} secondaries")

    async def send_to_secondary(url: str):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(f"{url}/replicate", json={"message": new_msg})
                resp.raise_for_status()
                logger.info(f"Master: ACK from {url}")
        except Exception as e:
            logger.error(f"Master: error replicating to {url}: {e}")
            raise

    try:
        await asyncio.gather(*(send_to_secondary(sec) for sec in SECONDARIES))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to replicate to all secondaries")

    return {"status": "OK", "message": new_msg}

@app.get("/messages")
def get_messages():
    return {"messages": messages}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
