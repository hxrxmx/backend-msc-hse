from fastapi import FastAPI
from pydantic import BaseModel


class PredictRequest(BaseModel):
    seller_id: int
    is_verified_seller: bool
    item_id: int
    name: str
    description: str
    category: int
    images_qty: int


class PredictResponse(BaseModel):
    result: bool


app = FastAPI()


@app.get("/")
async def root():
    return {
        "message": "hello, world"
    }


@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    result = request.images_qty > 0 or request.is_verified_seller
    return PredictResponse(result=result)
