import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import model as ml_logic
from database import repo
from app.clients.kafka import kafka_producer


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ml_model = None


class AdRequest(BaseModel):
    seller_id: int
    is_verified_seller: bool
    item_id: int
    name: str
    description: str
    category: int
    images_qty: int


class AdResponse(BaseModel):
    is_violation: bool
    probability: float


@asynccontextmanager
async def lifespan(app):
    await repo.connect()

    global ml_model
    ml_model = ml_logic.load_model("model.pkl")
    if ml_model is None:
        ml_model = ml_logic.train_model()
        ml_logic.save_model(ml_model, "model.pkl")

    await kafka_producer.start()
    yield

    await kafka_producer.stop()
    await repo.disconnect()

app = FastAPI(lifespan=lifespan)


@app.post("/predict", response_model=AdResponse)
async def predict(ad: AdRequest):
    if ml_model is None:
        raise HTTPException(status_code=503, detail="model not available")

    features = [
        float(ad.is_verified_seller),
        ad.images_qty / 10.0,
        len(ad.description) / 1000.0,
        ad.category / 100.0
    ]

    logger.info(f"id: {ad.seller_id}/{ad.item_id}, features: {features}")

    try:
        prob = ml_model.predict_proba([features])[0][1]
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="prediction error")

    is_violation = bool(ml_model.predict([features])[0])
    logger.info(f"result: {is_violation}, prob: {prob}")
    return AdResponse(is_violation=is_violation, probability=prob)


@app.post("/simple_predict", response_model=AdResponse)
async def simple_predict(item_id: int):
    if ml_model is None:
        raise HTTPException(status_code=503, detail="model not available")

    data = await repo.get_item_with_seller(item_id)
    if not data:
        raise HTTPException(status_code=404, detail="item not found")

    features = [
        float(data["is_verified_seller"]),
        data["images_qty"] / 10.0,
        len(data["description"]) / 1000.0,
        data["category"] / 100.0
    ]

    logger.info(f"features: {features}")

    try:
        prob = ml_model.predict_proba([features])[0][1]
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="prediction error")

    is_violation = bool(ml_model.predict([features])[0])
    logger.info(f"result: {is_violation}, prob: {prob}")
    return AdResponse(is_violation=is_violation, probability=prob)


@app.post("/async_predict")
async def async_predict(item_id: int):
    # if not await repo.item_exists(item_id):
    #     raise HTTPException(status_code=404, detail="item not found")

    task_id = await repo.create_moderation_task(item_id)
    await kafka_producer.send_moderation_request(item_id, task_id)

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "moderation request accepted",
    }


@app.get("/moderation_result/{task_id}")
async def get_moderation_result(task_id: int):
    result = await repo.get_moderation_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="task not found")

    return {
        "task_id": result["id"],
        "status": result["status"],
        "is_violation": result["is_violation"],
        "probability": result["probability"]
    }


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": ml_model is not None}
