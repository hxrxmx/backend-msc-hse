import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(autouse=True)
def mock_lifespan_dependencies():
    with patch(
        "main.repo.connect",
        new_callable=AsyncMock,
    ), patch(
        "main.repo.disconnect",
        new_callable=AsyncMock,
    ), patch(
        "main.kafka_producer.start",
        new_callable=AsyncMock,
    ), patch(
        "main.kafka_producer.stop",
        new_callable=AsyncMock,
    ), patch(
        "main.cache.connect",
        new_callable=AsyncMock,
    ), patch(
        "main.cache.disconnect",
        new_callable=AsyncMock,
    ):
        yield


def test_predict_unit_cache_hit():
    with patch(
        "main.cache.get_prediction",
        new_callable=AsyncMock
    ) as mock_get, TestClient(app) as client:
        mock_get.return_value = {"is_violation": False, "probability": 0.05}

        response = client.post("/predict", json={
            "seller_id": 1, "is_verified_seller": True, "item_id": 1,
            "name": "n", "description": "d", "category": 1, "images_qty": 1
        })

        assert response.status_code == 200
        assert response.json()["is_violation"] is False
        mock_get.assert_called_once()


def test_close_item_unit():
    with patch(
        "main.repo.item_exists",
        new_callable=AsyncMock
    ) as mock_exists, patch(
        "main.repo.delete_item",
        new_callable=AsyncMock
    ) as mock_del_db, patch(
        "main.cache.delete_prediction",
        new_callable=AsyncMock
    ) as mock_del_cache, TestClient(app) as client:

        mock_exists.return_value = True
        response = client.post("/close?item_id=1")

        assert response.status_code == 200
        mock_del_db.assert_called_once_with(1)
        mock_del_cache.assert_called_once_with(1)


def test_simple_predict_cache():
    with patch(
        "main.cache.get_prediction",
        new_callable=AsyncMock
    ) as mock_get, TestClient(app) as client:
        mock_get.return_value = {"is_violation": True, "probability": 0.9}

        response = client.post("/simple_predict?item_id=1")

        assert response.status_code == 200
        assert response.json()["is_violation"] is True
