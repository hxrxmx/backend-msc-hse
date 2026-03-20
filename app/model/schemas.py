from pydantic import BaseModel, Field


class AdRequest(BaseModel):
    seller_id: int = Field(..., gt=0)
    is_verified_seller: bool = Field(...)
    item_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: int = Field(..., ge=0)
    images_qty: int = Field(..., ge=0)


class AdResponse(BaseModel):
    is_violation: bool
    probability: float


class LoginRequest(BaseModel):
    login: str
    password: str
