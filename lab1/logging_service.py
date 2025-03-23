from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()

messages = {}

class LogMessage(BaseModel):
    id: str
    msg: str

@app.post("/log")
def log_message(log_msg: LogMessage):
 
    if log_msg.id in messages:
        return {"detail": "Повідомлення з таким ID вже існує, "}
    messages[log_msg.id] = log_msg.msg
    print(f"Отримано повідомлення: {log_msg.msg} з id: {log_msg.id}")
    return {"detail": "Повідомлення успішно збережено"}

@app.get("/logs")
def get_logs():
 
    return list(messages.values())

if __name__ == "__main__":
    uvicorn.run("logging_service:app", host="0.0.0.0", port=8001, reload=True)
