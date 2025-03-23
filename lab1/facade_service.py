from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import uuid
import time
import requests
import grpc
import logging_service_pb2
import logging_service_pb2_grpc

app = FastAPI()

LOGGING_SERVICE_URL = "http://localhost:8001"
MESSAGES_SERVICE_URL = "http://localhost:8002"
GRPC_LOGGING_SERVICE_ADDRESS = "localhost:50051" 


class Message(BaseModel):
    msg: str


@app.post("/message")
def post_message(message: Message):
    msg = message.msg
    message_id = str(uuid.uuid4())
    payload = {"id": message_id, "msg": msg}

    retries = 3
    for attempt in range(retries):
        try:
            response = requests.post(
                f"{LOGGING_SERVICE_URL}/log", json=payload, timeout=5
            )
            response.raise_for_status()
            break
        except Exception as e:
            print(f"Спроба {attempt+1} не вдалася: {e}")
            if attempt == retries - 1:
                raise HTTPException(
                    status_code=500,
                    detail="Не вдалося надіслати повідомлення до logging-service після декількох спроб",
                )
            time.sleep(2)
    return {"message_id": message_id, "message": msg}


@app.get("/message")
def get_message():
 
    try:
        resp_logging = requests.get(f"{LOGGING_SERVICE_URL}/logs", timeout=5)
        resp_logging.raise_for_status()
        log_messages = resp_logging.json() 
    except Exception as e:
        log_messages = f"Помилка при отриманні даних від logging-service: {e}"

    try:
        resp_messages = requests.get(f"{MESSAGES_SERVICE_URL}/static", timeout=5)
        resp_messages.raise_for_status()
        static_msg = resp_messages.text
    except Exception as e:
        static_msg = f"Помилка при отриманні даних від messages-service: {e}"

    if isinstance(log_messages, list):
        log_str = ", ".join(log_messages)
    else:
        log_str = str(log_messages)

    combined = f"{log_str} | {static_msg}"
    return {"combined": combined}


@app.post("/grpc_message")
def grpc_post_message(message: Message):

    msg = message.msg
    message_id = str(uuid.uuid4())
    request_proto = logging_service_pb2.LogRequest(id=message_id, msg=msg)
    
    retries = 5
    for attempt in range(retries):
        try:
            channel = grpc.insecure_channel(GRPC_LOGGING_SERVICE_ADDRESS)
            stub = logging_service_pb2_grpc.LoggingServiceStub(channel)
            response = stub.LogMessage(request_proto, timeout=5)
            print(f"gRPC POST: Відповідь від logging-service: {response.detail}")
            channel.close()
            break
        except Exception as e:
            print(f"gRPC POST: Спроба {attempt+1} не вдалася: {e}")
            if attempt == retries - 1:
                raise HTTPException(
                    status_code=500,
                    detail="gRPC POST: Не вдалося надіслати повідомлення до logging-service після декількох спроб"
                )
            time.sleep(2)
            
    return {"message_id": message_id, "message": msg}

@app.get("/grpc_message")
def grpc_get_message():

    try:
        resp_messages = requests.get(f"{MESSAGES_SERVICE_URL}/static", timeout=5)
        resp_messages.raise_for_status()
        static_msg = resp_messages.text
    except Exception as e:
        static_msg = f"Помилка при отриманні даних від messages-service: {e}"
    
    retries = 5
    for attempt in range(retries):
        try:
            channel = grpc.insecure_channel(GRPC_LOGGING_SERVICE_ADDRESS)
            stub = logging_service_pb2_grpc.LoggingServiceStub(channel)
            response = stub.GetLogs(logging_service_pb2.Empty(), timeout=5)
            logs = list(response.logs)
            channel.close()
            combined = ' '.join(logs) + ' ' + static_msg
            return {"combined": combined}
        except Exception as e:
            print(f"gRPC GET: Спроба {attempt+1} не вдалася: {e}")
            if attempt == retries - 1:
                raise HTTPException(
                    status_code=500,
                    detail=f"gRPC GET: Помилка виклику logging-service через gRPC: {e}"
                )
            time.sleep(2)





if __name__ == "__main__":
    import uvicorn

    uvicorn.run("facade_service:app", host="0.0.0.0", port=8000, reload=True)
