from fastapi import FastAPI
from contextlib import asynccontextmanager
from mqtt_worker import start_mqtt, stop_mqtt
from db import readings_col

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_mqtt()
    yield
    stop_mqtt()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    return {"message": "Server is running"}

@app.get("/latest")
def latest(limit: int = 10):
    limit = min(max(limit, 1), 200)
    docs = list(
        readings_col.find({}, {"_id": 0})
        .sort("ts_ingested", -1)
        .limit(limit)
        
    )
    return {"count": len(docs), "items": docs}

