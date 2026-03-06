import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from prometheus_client import \
    Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

import model as ml_logic
from database import repo
from app.clients.kafka import kafka_producer
from app.clients.redis import cache
from app.metrics.metrics import PREDICTIONS_TOTAL, PREDICTION_DURATION, \
    PREDICTION_ERRORS, MODEL_PROBABILITY


REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
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


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        endpoint = request.url.path
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()
        REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        return response


@asynccontextmanager
async def lifespan(app):
    await repo.connect()

    global ml_model
    ml_model = ml_logic.load_model("model.pkl")
    if ml_model is None:
        ml_model = ml_logic.train_model()
        ml_logic.save_model(ml_model, "model.pkl")

    await kafka_producer.start()
    await cache.connect()
    yield

    await cache.disconnect()
    await kafka_producer.stop()
    await repo.disconnect()


app = FastAPI(lifespan=lifespan)
app.add_middleware(PrometheusMiddleware)


@app.post("/predict", response_model=AdResponse)
async def predict(ad: AdRequest):
    cached = await cache.get_prediction(ad.item_id)
    if cached:
        logger.info(f"Cache hit for item {ad.item_id}")
        return AdResponse(**cached)

    if ml_model is None:
        raise HTTPException(status_code=503, detail="model not available")

    features = [
        float(ad.is_verified_seller),
        ad.images_qty / 10.0,
        len(ad.description) / 1000.0,
        ad.category / 100.0
    ]

    logger.info(f"id: {ad.seller_id}/{ad.item_id}, features: {features}")

    start_time = time.time()
    try:
        prob = ml_model.predict_proba([features])[0][1]
        is_violation = bool(ml_model.predict([features])[0])

        PREDICTION_DURATION.observe(time.time() - start_time)
        MODEL_PROBABILITY.observe(prob)
        PREDICTIONS_TOTAL.labels(
            result="violation" if is_violation else "no_violation"
        ).inc()
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="prediction error")
    result = {
        "is_violation": is_violation,
        "probability": prob
    }

    logger.info(f"result: {is_violation}, prob: {prob}")

    await cache.set_prediction(ad.item_id, result)
    return AdResponse(**result)


@app.post("/simple_predict", response_model=AdResponse)
async def simple_predict(item_id: int):
    cached = await cache.get_prediction(item_id)
    if cached:
        logger.info(f"Cache hit for item {item_id}")
        return AdResponse(**cached)

    if ml_model is None:
        raise HTTPException(status_code=503, detail="model not available")

    data = await repo.get_item_with_seller(item_id)
    if not data:
        raise HTTPException(status_code=404, detail="item not found")

    features = [
        float(data["is_verified_seller"]),
        data["images_qty"] / 10.0,
        len(data["description"]) / 1000.0,
        data["category"] / 100.0,
    ]

    logger.info(f"features: {features}")

    start_time = time.time()
    try:
        prob = ml_model.predict_proba([features])[0][1]
        is_violation = bool(ml_model.predict([features])[0])

        PREDICTION_DURATION.observe(time.time() - start_time)
        MODEL_PROBABILITY.observe(prob)
        PREDICTIONS_TOTAL.labels(
            result="violation" if is_violation else "no_violation"
        ).inc()

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="prediction error")

    result = {
        "is_violation": is_violation,
        "probability": prob
    }

    logger.info(f"result: {is_violation}, prob: {prob}")

    await cache.set_prediction(item_id, result)
    return AdResponse(is_violation=is_violation, probability=prob)


@app.post("/async_predict")
async def async_predict(item_id: int):
    cached = await cache.get_prediction(item_id)
    if cached:
        logger.info(f"Cache hit for item {item_id}")
        return {
            "task_id": None,
            "status": "cached",
            "is_violation": cached["is_violation"],
            "probability": cached["probability"],
        }

    if not await repo.item_exists(item_id):
        raise HTTPException(status_code=404, detail="item not found")

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

    if result["status"] == "completed":
        cached = await cache.get_prediction(result["item_id"])
        if not cached:
            result = {
                "is_violation": result["is_violation"],
                "probability": result["probability"],
            }
            await cache.set_prediction(result["item_id"], result)

    return {
        "task_id": result["id"],
        "status": result["status"],
        "is_violation": result["is_violation"],
        "probability": result["probability"]
    }


@app.post("/close")
async def close_item(item_id: int):

    if not await repo.item_exists(item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    await repo.delete_item(item_id)
    await cache.delete_prediction(item_id)

    return {
        "message": f"Item {item_id} and its results deleted from DB and cache"
    }


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": ml_model is not None}
