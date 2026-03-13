import pytest
from unittest.mock import AsyncMock, patch
from app.main.main import app
from app.account.current import get_current_account


@pytest.fixture(autouse=True, scope="session")
def setup_global_mocks():
    app.dependency_overrides[get_current_account] = lambda: {
        "id": 1, "login": "test_user", "is_blocked": False
    }

    with patch("app.main.main.kafka_producer.start", new_callable=AsyncMock), \
         patch("app.main.main.kafka_producer.stop", new_callable=AsyncMock), \
         patch("app.main.main.cache.connect", new_callable=AsyncMock), \
         patch("app.main.main.cache.disconnect", new_callable=AsyncMock), \
         patch("app.main.main.repo.connect", new_callable=AsyncMock), \
         patch("app.main.main.repo.disconnect", new_callable=AsyncMock):
        yield

    app.dependency_overrides = {}


@pytest.fixture(autouse=True)
def mock_infra(request):
    if "integration" in request.keywords:
        with patch("main.kafka_producer.start", new_callable=AsyncMock), \
             patch("main.kafka_producer.stop", new_callable=AsyncMock), \
             patch("main.cache.connect", new_callable=AsyncMock):
            yield
    else:
        with patch("main.kafka_producer.start", new_callable=AsyncMock), \
             patch("main.repo.connect", new_callable=AsyncMock), \
             patch("main.cache.connect", new_callable=AsyncMock):
            yield
