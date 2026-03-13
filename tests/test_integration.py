import pytest
import uuid
import asyncio
import asyncpg
from fastapi.testclient import TestClient

import app.main.main as main
from app.main.main import app
from app.database.database import repo, AccountRepository
from app.clients.redis import cache
from app.account.current import get_current_account

app.dependency_overrides[get_current_account] = lambda: {
    "id": 1, "login": "test_user", "is_blocked": False
}


DB_URL = "postgresql://postgres:postgres@localhost:5435/hw"


def setup_db_sync():
    async def _async_setup():
        conn = await asyncpg.connect(DB_URL)
        await conn.execute("INSERT INTO users (id, is_verified_seller) VALUES (1, true) ON CONFLICT (id) DO NOTHING")
        await conn.execute("""
            INSERT INTO items (id, seller_id, name, description, category, images_qty) 
            VALUES (1, 1, 'test', 'desc', 1, 1) ON CONFLICT (id) DO NOTHING
        """)
        await conn.close()
    asyncio.run(_async_setup())


@pytest.fixture(scope="module", autouse=True)
def db_data():
    setup_db_sync()
    yield


@pytest.mark.integration
@pytest.mark.asyncio
async def test_account_repo_lifecycle():
    pool = await asyncpg.create_pool(DB_URL)
    acc_repo = AccountRepository(pool)
    login = f"u_{uuid.uuid4().hex[:6]}"
    try:
        acc_id = await acc_repo.create(login, "password")
        assert isinstance(acc_id, int)
        acc = await acc_repo.verify_password(login, "password")
        assert acc is not None
    finally:
        await pool.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_db_creation():
    await repo.connect()
    try:
        user_id = await repo.create_user(is_verified_seller=True)
        item_id = await repo.create_item(user_id, "test", "desc", 1, 2)
        assert isinstance(item_id, int)
    finally:
        await repo.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_integration():
    await cache.connect()
    item_id = 999111
    await cache.set_prediction(item_id, {"is_violation": False, "probability": 0.1})
    assert (await cache.get_prediction(item_id)) is not None
    await cache.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_delete_logic():
    await repo.connect()
    uid = await repo.create_user(True)
    iid = await repo.create_item(uid, "del", "del", 1, 1)
    await repo.delete_item(iid)
    assert (await repo.get_item_with_seller(iid)) is None
    await repo.disconnect()


@pytest.mark.integration
def test_predict_success():
    with TestClient(app) as client:
        response = client.post("/predict", json={
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 1,
            "name": "test",
            "description": "long description text here",
            "category": 1,
            "images_qty": 5,
        })
        assert response.status_code == 200


@pytest.mark.integration
def test_simple_predict_success():
    with TestClient(app) as client:
        response = client.post("/simple_predict?item_id=1")
        assert response.status_code == 200


@pytest.mark.integration
def test_async_predict_success():
    with TestClient(app) as client:
        response = client.post("/async_predict?item_id=1")
        assert response.status_code == 200
        assert "task_id" in response.json()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_moderation_result_status():
    await repo.connect()
    iid = await repo.create_item(1, "temp_name", "temp_desc", 1, 1)

    with TestClient(app) as client:
        res = client.post(f"/async_predict?item_id={iid}")
        task_id = res.json().get("task_id")

        assert task_id is not None
        assert client.get(f"/moderation_result/{task_id}").status_code == 200
    await repo.disconnect()


@pytest.mark.integration
def test_model_error_503():
    with TestClient(app) as client:
        old_model = main.ml_model
        main.ml_model = None
        try:
            response = client.post("/predict", json={
                "seller_id": 1, "is_verified_seller": True, "item_id": 888777,
                "name": "n", "description": "d", "category": 1, "images_qty": 1
            })
            assert response.status_code == 503
        finally:
            main.ml_model = old_model
