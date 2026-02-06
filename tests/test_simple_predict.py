import pytest
from fastapi.testclient import TestClient
from main import app
from database import repo

client = TestClient(app)


@pytest.mark.asyncio
async def test_db_creation():
    await repo.connect()
    try:
        user_id = await repo.create_user(is_verified_seller=True)
        assert isinstance(user_id, int)

        item_id = await repo.create_item(
            seller_id=user_id,
            name="test",
            description="aodshfi",
            category=1,
            images_qty=2
        )
        assert isinstance(item_id, int)
    finally:
        await repo.disconnect()


def test_simple_predict_success():
    with TestClient(app) as client:
        response = client.post("/simple_predict?item_id=1")  # ожидается, что в бд есть объявление с id=1

        assert response.status_code == 200
        data = response.json()
        assert "is_violation" in data
        assert "probability" in data


def test_simple_predict_not_found():
    with TestClient(app) as client:
        response = client.post("/simple_predict?item_id=99999999")
        assert response.status_code == 404


def test_simple_predict_invalid_id():
    response = client.post("/simple_predict?item_id=abc")
    assert response.status_code == 422
