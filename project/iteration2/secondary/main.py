import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import time
import threading
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("secondary2")

app = FastAPI()

store = {}
last_delivered_id = 0

REPLICATION_DELAY = int(os.getenv("REPLICATION_DELAY", "3"))

lock = threading.Lock()

class ReplicateRequest(BaseModel):
    msg_id: int
    message: str

@app.post("/replicate")
def replicate(req: ReplicateRequest):
    
    global store, last_delivered_id

    with lock:
        if req.msg_id % 5 == 0:
            logger.warning(
                f"Secondary2 ({os.getenv('SECONDARY_ID')}): "
                f"simulated error for msg_id={req.msg_id}"
            )
            raise HTTPException(status_code=500, detail="Simulated internal error")

        logger.info(
            f"Secondary2 ({os.getenv('SECONDARY_ID')}): "
            f"received msg_id={req.msg_id}, sleeping {REPLICATION_DELAY}s"
        )
        time.sleep(REPLICATION_DELAY)

        if req.msg_id in store:
            logger.info(
                f"Secondary2 ({os.getenv('SECONDARY_ID')}): "
                f"msg_id={req.msg_id} already exists, ignoring"
            )
        else:
            store[req.msg_id] = req.message
            logger.info(
                f"Secondary2 ({os.getenv('SECONDARY_ID')}): "
                f"stored msg_id={req.msg_id}"
            )

        sorted_ids = sorted(k for k in store.keys() if k > last_delivered_id)
        while True:
            next_expected = last_delivered_id + 1
            if sorted_ids and sorted_ids[0] == next_expected:
                last_delivered_id = next_expected
                sorted_ids.pop(0)
                continue
            break

    return {"status": "ACK"}

@app.get("/messages")
def get_messages():
   
    with lock:
        sorted_ids = sorted(k for k in store.keys() if k <= last_delivered_id)
        ordered = [{"msg_id": i, "message": store[i]} for i in sorted_ids]
    return {"messages": ordered}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
