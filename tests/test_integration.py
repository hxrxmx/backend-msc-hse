import pytest
import main
from main import app
from fastapi.testclient import TestClient
from database import repo
from app.clients.redis import cache


@pytest.mark.integration
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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_integration():
    await cache.connect()
    item_id = 2893475610
    test_data = {"is_violation": True, "probability": 0.99}

    await cache.set_prediction(item_id, test_data)
    result = await cache.get_prediction(item_id)
    assert result == test_data

    await cache.delete_prediction(item_id)
    assert await cache.get_prediction(item_id) is None
    await cache.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_delete_logic():
    await repo.connect()

    user_id = await repo.create_user(True)
    item_id = await repo.create_item(user_id, "oefhga", "asidjfad", 1, 1)

    await repo.delete_item(item_id)

    item = await repo.get_item_with_seller(item_id)
    assert item is None
    await repo.disconnect()


@pytest.mark.integration
def test_predict_success():
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            json={
                "seller_id": 1,
                "is_verified_seller": True,
                "item_id": 1,
                "name": "test",
                "description": "test description long enough",
                "category": 1,
                "images_qty": 5
            }
        )
        assert response.status_code == 200
        assert isinstance(response.json()["is_violation"], bool)
        assert isinstance(response.json()["probability"], float)


@pytest.mark.integration
def test_missing_field():
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            json={
                "seller_id": 1,
                "is_verified_seller": True
            }
        )
        assert response.status_code == 422


@pytest.mark.integration
def test_wrong_type():
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            json={
                "seller_id": "aaaa",
                "is_verified_seller": True,
                "item_id": 1,
                "name": "test",
                "description": "test",
                "category": 1,
                "images_qty": 1
            }
        )
        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_model_error_503():
    await cache.connect()
    await cache.client.flushdb()
    with TestClient(app) as client:
        tmp_model = main.ml_model
        main.ml_model = None
        response = client.post(
            "/predict",
            json={
                "seller_id": 1,
                "is_verified_seller": True,
                "item_id": 975876586,
                "name": "test",
                "description": "test",
                "category": 1,
                "images_qty": 1
            }
        )
        assert response.status_code == 503
        main.ml_model = tmp_model


@pytest.mark.integration
def test_simple_predict_success():
    with TestClient(app) as client:
        response = client.post("/simple_predict?item_id=1")  # ожидается, что в бд есть объявление с id=1

        assert response.status_code == 200
        data = response.json()
        assert "is_violation" in data
        assert "probability" in data


@pytest.mark.integration
def test_simple_predict_not_found():
    with TestClient(app) as client:
        response = client.post("/simple_predict?item_id=99999999")
        assert response.status_code == 404


@pytest.mark.integration
def test_async_predict_success():
    with TestClient(app) as client:
        response = client.post("/async_predict?item_id=2")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert "task_id" in data


@pytest.mark.integration
def test_get_moderation_result_status():
    with TestClient(app) as client:
        res = client.post("/async_predict?item_id=3")
        task_id = res.json()["task_id"]

        status_res = client.get(f"/moderation_result/{task_id}")
        assert status_res.status_code == 200
        assert status_res.json()["task_id"] == task_id
