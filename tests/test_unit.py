import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main.main import app
from app.account.current import get_current_account


client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_lifespan_dependencies():
    with patch(
        "app.main.main.repo.connect",
        new_callable=AsyncMock,
    ), patch(
        "app.main.main.repo.disconnect",
        new_callable=AsyncMock,
    ), patch(
        "app.main.main.kafka_producer.start",
        new_callable=AsyncMock,
    ), patch(
        "app.main.main.kafka_producer.stop",
        new_callable=AsyncMock,
    ), patch(
        "app.main.main.cache.connect",
        new_callable=AsyncMock,
    ), patch(
        "app.main.main.cache.disconnect",
        new_callable=AsyncMock,
    ):
        yield


@pytest.fixture(autouse=True, scope="session")
def setup_infra_and_auth():
    app.dependency_overrides[get_current_account] = lambda: {
        "id": 1, "login": "test_user", "is_blocked": False
    }

    with patch("app.main.main.kafka_producer.start", new_callable=AsyncMock), \
         patch("app.main.main.kafka_producer.stop", new_callable=AsyncMock), \
         patch("app.main.main.cache.connect", new_callable=AsyncMock), \
         patch("app.main.main.repo.connect", new_callable=AsyncMock):
        yield


def test_predict_unit_cache_hit():
    with patch(
        "app.main.main.cache.get_prediction", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = {"is_violation": False, "probability": 0.05}
        response = client.post("/predict", json={
            "seller_id": 1, "is_verified_seller": True, "item_id": 1,
            "name": "n", "description": "d", "category": 1, "images_qty": 1
        })
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_current_account_invalid():
    with patch("app.account.current.decode_access_token") as mock_decode:
        mock_decode.return_value = None
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await get_current_account(access_token="fake_token")
        assert exc.value.status_code == 401


def test_close_item_unit():
    with patch(
        "app.main.main.repo.item_exists",
        new_callable=AsyncMock
    ) as mock_exists, patch(
        "app.main.main.repo.delete_item",
        new_callable=AsyncMock
    ) as mock_del_db, patch(
        "app.main.main.cache.delete_prediction",
        new_callable=AsyncMock
    ) as mock_del_cache, TestClient(app) as client:

        mock_exists.return_value = True
        response = client.post("/close?item_id=1")

        assert response.status_code == 200
        mock_del_db.assert_called_once_with(1)
        mock_del_cache.assert_called_once_with(1)


def test_simple_predict_cache():
    with patch(
        "app.main.main.cache.get_prediction",
        new_callable=AsyncMock
    ) as mock_get, TestClient(app) as client:
        mock_get.return_value = {"is_violation": True, "probability": 0.9}

        response = client.post("/simple_predict?item_id=1")

        assert response.status_code == 200
        assert response.json()["is_violation"] is True


@pytest.mark.asyncio
async def test_get_current_account_valid():
    mock_repo = AsyncMock()
    mock_repo.find_by_id.return_value = {
        "id": 1,
        "login": "asdjhg",
        "is_blocked": False
    }

    with patch("app.account.current.decode_access_token") as mock_decode, \
         patch("app.account.current.account_repo", mock_repo):
        mock_decode.return_value = {"sub": "1"}

        account = await get_current_account(access_token="valid_token")

        assert account["id"] == 1
        mock_repo.find_by_id.assert_called_once_with(1)
