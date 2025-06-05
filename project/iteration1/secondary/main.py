import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import logging
import time
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("secondary")

app = FastAPI()

replicated_messages = []

REPLICATION_DELAY = int(os.getenv("REPLICATION_DELAY", "5"))

class ReplicateRequest(BaseModel):
    message: str

@app.post("/replicate")
def replicate(req: ReplicateRequest):
    logger.info(f"Secondary ({os.getenv('SECONDARY_ID', 'unknown')}): received /replicate, sleeping {REPLICATION_DELAY}s")
    time.sleep(REPLICATION_DELAY)
    replicated_messages.append(req.message)
    logger.info(f"Secondary ({os.getenv('SECONDARY_ID', 'unknown')}): stored message '{req.message}'")
    return {"status": "ACK"}

@app.get("/messages")
def get_messages():
    return {"messages": replicated_messages}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
