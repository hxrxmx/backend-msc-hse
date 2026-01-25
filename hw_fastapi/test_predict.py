from hw_fastapi.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_verified_seller():
    response = client.post(
        "/predict",
        json={
            "seller_id": 0,
            "is_verified_seller": True,
            "item_id": 0,
            "name": "",
            "description": "",
            "category": 0,
            "images_qty": 0
        }
    )
    assert response.status_code == 200
    assert response.json()["result"] is True


def test_unverified_seller_w_imgs():
    response = client.post(
        "/predict",
        json={
            "seller_id": 0,
            "is_verified_seller": False,
            "item_id": 0,
            "name": "",
            "description": "",
            "category": 0,
            "images_qty": 1
        }
    )
    assert response.status_code == 200
    assert response.json()["result"] is True


def test_unverified_seller_wo_imgs():
    response = client.post(
        "/predict",
        json={
            "seller_id": 0,
            "is_verified_seller": False,
            "item_id": 0,
            "name": "",
            "description": "",
            "category": 0,
            "images_qty": 0
        }
    )
    assert response.status_code == 200
    assert response.json()["result"] is False


def test_missing_field():
    response = client.post(
        "/predict",
        json={
            "seller_id": 2,
            "is_verified_seller": False,

            "name": "",
            "description": "",
            "category": 0,
            "images_qty": 0,
        },
    )
    assert response.status_code == 422


def test_wrong_type():
    response = client.post(
        "/predict",
        json={
            "seller_id": "aaaAAA",
            "is_verified_seller": False,
            "item_id": 0,
            "name": "",
            "description": "",
            "category": 0,
            "images_qty": 0,
        },
    )
    assert response.status_code == 422
