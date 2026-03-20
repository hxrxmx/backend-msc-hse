import os

import numpy as np
from sklearn.linear_model import LogisticRegression
from mlflow.sklearn import load_model as mlflow_sklearn_load_model
import pickle


def train_model():
    np.random.seed(42)
    X = np.random.rand(1000, 4)
    y = (X[:, 0] < 0.3) | (X[:, 1] < 0.2).astype(int)

    model = LogisticRegression()
    model.fit(X, y)
    return model


def save_model(model, path="model.pkl"):
    with open(path, "wb") as f:
        pickle.dump(model, f)


def load_model():
    use_mlflow = os.getenv("USE_MLFLOW", "false").lower() == "true"

    if use_mlflow:
        try:
            model_name = "moderation-model"
            model_uri = f"models:/{model_name}/latest"
            return mlflow_sklearn_load_model(model_uri)
        except Exception as e:
            print(f"MLflow load failed: {e}. Falling back to local.")

    path = "model.pkl"
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)

    model = train_model()
    save_model(model, path)
    return model
