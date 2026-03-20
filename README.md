```markdown
# Ad Moderation Service (Final Project)

## Prerequisites
- Docker & Docker Compose
- Python 3.10+

## Setup Infrastructure
Starts PostgreSQL (port 5435), Redis, Redpanda (Kafka), Prometheus, Grafana, and MLflow:
```bash
docker compose up -d
```

## Database Migrations
Apply migrations to the `hw` database on port `5435`:
```bash
pgmigrate -c "host=localhost user=postgres password=postgres dbname=hw port=5435" -d . -t latest migrate
```

## Running the Application

### 1. Start the FastAPI Service
```bash
uvicorn app.main.main:app --reload
```

### 2. Start the Moderation Worker
```bash
python -m app.workers.moderation_worker
```

## Running Tests
- Unit tests:
  ```bash
  pytest -m "not integration"
  ```
- Integration tests:
  ```bash
  pytest -m integration
  ```

## Key API Endpoints
- `POST /login` - Get JWT token (sets cookies).
- `POST /predict` - Synchronous moderation (Protected).
- `POST /async_predict?item_id={id}` - Submit for async moderation (Protected).
- `GET /moderation_result/{task_id}` - Check async task status.
- `POST /close?item_id={id}` - Delete item and invalidate cache.
- `GET /metrics` - Prometheus metrics.

## Monitoring
- Prometheus: [http://localhost:9090](http://localhost:9090)
- Grafana: [http://localhost:3000](http://localhost:3000) (login: `admin` / pass: `admin`)
- Kafka Console: [http://localhost:8080](http://localhost:8080)
```