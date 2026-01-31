import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import model as ml_logic

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
    global ml_model
    ml_model = ml_logic.load_model("model.pkl")
    if ml_model is None:
        ml_model = ml_logic.train_model()
        ml_logic.save_model(ml_model, "model.pkl")
    yield

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


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": ml_model is not None}
