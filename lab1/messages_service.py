
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/static")
def get_static_message():
    return "not implemented yet"

if __name__ == "__main__":
    uvicorn.run("messages_service:app", host="0.0.0.0", port=8002, reload=True)
