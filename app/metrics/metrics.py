from prometheus_client import Counter, Histogram


PREDICTIONS_TOTAL = Counter(
    "predictions_total",
    "Total number of predictions",
    ["result"],
)

PREDICTION_DURATION = Histogram(
    "prediction_duration_seconds",
    "Time spent on ML model inference",
)

PREDICTION_ERRORS = Counter(
    "prediction_errors_total",
    "Total number of prediction errors",
    ["error_type"],
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Time spent on DB queries",
    ["query_type"],
)

MODEL_PROBABILITY = Histogram(
    "model_prediction_probability",
    "Distribution of violation probabilities"
)
