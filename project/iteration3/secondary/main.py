import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import time
import threading
import random
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("secondary3")

app = FastAPI()


store = {}

last_delivered_id = 0

lock = threading.Lock()

def update_last_delivered():
    global last_delivered_id
    sorted_ids = sorted(store.keys())
    while True:
        next_expected = last_delivered_id + 1
        if sorted_ids and sorted_ids[0] == next_expected:
            last_delivered_id = next_expected
            sorted_ids.pop(0)
        else:
            break

class ReplicateRequest(BaseModel):
    msg_id: int
    message: str

@app.post("/replicate")
def replicate(req: ReplicateRequest):
    global store, last_delivered_id

    with lock:
        if random.random() < 0.1:
            logger.warning(f"Secondary3 ({os.getenv('SECONDARY_ID')}): simulated error for msg_id={req.msg_id}")
            raise HTTPException(status_code=500, detail="Random internal error")

        delay = float(os.getenv("REPLICATION_DELAY", "2"))
        logger.info(f"Secondary3 ({os.getenv('SECONDARY_ID')}): received msg_id={req.msg_id}, sleeping {delay}s")
        time.sleep(delay)

        if req.msg_id in store:
            logger.info(f"Secondary3 ({os.getenv('SECONDARY_ID')}): msg_id={req.msg_id} already exists, ignoring")
        else:
            store[req.msg_id] = req.message
            logger.info(f"Secondary3 ({os.getenv('SECONDARY_ID')}): stored msg_id={req.msg_id}")

        update_last_delivered()

    return {"status": "ACK"}

@app.get("/messages")
def get_messages():
    with lock:
        ordered = [{"msg_id": i, "message": store[i]} for i in sorted(store.keys()) if i <= last_delivered_id]
    return {"messages": ordered}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
