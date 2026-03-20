import time
from app.metrics.metrics import PREDICTIONS_TOTAL, \
    PREDICTION_DURATION, MODEL_PROBABILITY


def calculate_prediction(
    ml_model,
    is_verified,
    images_qty,
    description,
    category
):
    features = [
        float(is_verified),
        images_qty / 10.0,
        len(description) / 1000.0,
        category / 100.0
    ]
    start_time = time.time()
    prob = float(ml_model.predict_proba([features])[0][1])
    is_violation = bool(ml_model.predict([features])[0])

    PREDICTION_DURATION.observe(time.time() - start_time)
    MODEL_PROBABILITY.observe(prob)
    PREDICTIONS_TOTAL.labels(
        result="violation" if is_violation else "no_violation"
    ).inc()

    return {"is_violation": is_violation, "probability": prob}
