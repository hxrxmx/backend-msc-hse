from main import app
from fastapi.testclient import TestClient
import main
import model as ml_logic


if main.ml_model is None:
    main.ml_model = ml_logic.load_model("model.pkl") or ml_logic.train_model()

client = TestClient(app)


def test_predict_success():
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


def test_missing_field():
    response = client.post(
        "/predict",
        json={
            "seller_id": 1,
            "is_verified_seller": True
        }
    )
    assert response.status_code == 422


def test_wrong_type():
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


def test_model_error_503():
    tmp_model = main.ml_model
    main.ml_model = None
    response = client.post(
        "/predict",
        json={
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 1,
            "name": "test",
            "description": "test",
            "category": 1,
            "images_qty": 1
        }
    )
    assert response.status_code == 503
    main.ml_model = tmp_model
