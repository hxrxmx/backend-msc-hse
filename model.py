import numpy as np
from sklearn.linear_model import LogisticRegression
import pickle
import os


def train_model():
    np.random.seed(42)
    X = np.random.rand(1000, 4)
    y = (X[:, 0] < 0.3) & (X[:, 1] < 0.2).astype(int)

    model = LogisticRegression()
    model.fit(X, y)
    return model


def save_model(model, path="model.pkl"):
    with open(path, "wb") as f:
        pickle.dump(model, f)


def load_model(path="model.pkl"):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)
