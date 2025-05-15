from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()

SERVICES = {
    "logging-service": [
        "http://127.0.0.1:8011",
        "http://127.0.0.1:8012",
        "http://127.0.0.1:8013",
    ],
    "messages-service": [
        "http://127.0.0.1:8004"
    ]
}


class ServiceList(BaseModel):
    instances: list[str]

@app.get("/services/{service_name}", response_model=ServiceList)
async def get_service_list(service_name: str):
    instances = SERVICES.get(service_name, [])
    return ServiceList(instances=instances)



if __name__ == "__main__":
    uvicorn.run("config_service:app", host="0.0.0.0", port=8000, reload=True)
