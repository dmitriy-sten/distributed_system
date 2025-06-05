from fastapi import FastAPI, Request
import uvicorn
import logging

app = FastAPI()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@app.post("/echo")
async def echo(request: Request):
    data = await request.json()
    logger.info(f"Received for echo: {data}")
    return {"echo": data}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
