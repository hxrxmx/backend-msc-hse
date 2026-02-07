# backend-msc-hse (async moderation)


## Setup
Start Redpanda:
```bash
docker compose up -d
```
The Console will be available at [http://localhost:8080](http://localhost:8080).

## db Migrations
Apply migrations to create tables (`users`, `items`, `moderation_results`):
```bash
pgmigrate -c "host=localhost user=postgres dbname=postgres" -d . -t latest migrate
```

## Running

### 1. Start the FastAPI Service
```bash
uvicorn main:app --reload
```

### 2. Start the Moderation Worker
```bash
python -m app.workers.moderation_worker
```

## API Endpoints
- `POST /predict` - Synchronous moderation (legacy).
- `POST /async_predict?item_id={id}` - Submit an item for async moderation.
- `GET /moderation_result/{task_id}` - Poll the status and result of the moderation task.
- `GET /health` - Check service status.
