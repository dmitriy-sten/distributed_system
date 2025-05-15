from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import uvicorn
import hazelcast

app = FastAPI()

hz = hazelcast.HazelcastClient(
    cluster_members=["127.0.0.1:5701", "127.0.0.1:5702", "127.0.0.1:5703"]
)
messages_map = hz.get_map("messages").blocking()


class LogMessage(BaseModel):
    id: str
    msg: str


@app.post("/log")
def log_message(log_msg: LogMessage):
    existing = messages_map.get(log_msg.id)
    if existing is not None:
       return {"status": "ok", "id": log_msg.id, "note": "Ігнорування дупліката"}
    messages_map.put(log_msg.id, log_msg.msg)
    print(f"Отримано повідомлення: {log_msg.msg} з id: {log_msg.id}")
    return {"detail": "Повідомлення успішно збережено"}


@app.get("/logs")
def get_logs():

    all_msgs = []
    for key in messages_map.key_set():
        val = messages_map.get(key)
        all_msgs.append(f"{key}: {val}")
    return all_msgs


# if __name__ == "__main__":
#     uvicorn.run("logging_service:app", host="0.0.0.0", port=8001, reload=True)
