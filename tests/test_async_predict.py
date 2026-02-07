from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_async_predict_success():
    with TestClient(app) as client:
        response = client.post("/async_predict?item_id=1")  # ожидается, что в бд есть объявление с id=1
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert "task_id" in data


def test_get_moderation_result_status():
    with TestClient(app) as client:
        res = client.post("/async_predict?item_id=1")
        task_id = res.json()["task_id"]

        status_res = client.get(f"/moderation_result/{task_id}")
        assert status_res.status_code == 200
        assert status_res.json()["task_id"] == task_id
