import asyncio
import json
import logging
from datetime import datetime, timezone
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from database import repo
import model as ml_logic


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")


KAFKA_SERVERS = "localhost:9092"
TOPIC_MODERATION = "moderation"
TOPIC_DLQ = "moderation_dlq"
MAX_RETRIES = 3
MIN_RETRY_DELAY = 3


async def send_to_dlq(producer, msg, error):
    dlq_msg = {
        "original_message": msg,
        "error": str(error),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "retry_count": 0
    }
    await producer.send_and_wait(
        TOPIC_DLQ,
        json.dumps(dlq_msg).encode("utf-8")
    )


async def run_worker():
    model = ml_logic.load_model("model.pkl") or ml_logic.train_model()

    consumer = AIOKafkaConsumer(
        TOPIC_MODERATION,
        bootstrap_servers=KAFKA_SERVERS,
        group_id="moderation-group"
    )
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_SERVERS)

    await consumer.start()
    await producer.start()
    await repo.connect()

    logger.info("worker started...")

    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode("utf-8"))
            item_id = data.get("item_id")
            task_id = data.get("task_id")

            last_error = None

            for attempt in range(MAX_RETRIES):
                try:
                    item = await repo.get_item_with_seller(item_id)
                    if not item:
                        raise ValueError(f"{item_id} not found in db")

                    features = [
                        float(item["is_verified_seller"]),
                        item["images_qty"] / 10.0,
                        len(item["description"]) / 1000.0,
                        item["category"] / 100.0
                    ]
                    prob = model.predict_proba([features])[0][1]
                    is_violation = bool(model.predict([features])[0])

                    await repo.update_moderation_result(
                        task_id,
                        "completed",
                        is_violation,
                        prob
                    )
                    logger.info(f"task {task_id} completed on attempt {attempt}")
                    last_error = None
                    break

                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"attempt {attempt + 1} failed for task {task_id}: {e}"
                    )

                    if attempt + 1 < MAX_RETRIES:
                        delay = MIN_RETRY_DELAY * 2**(attempt)
                        logger.info(f"retrying task {task_id} in {delay} seconds..")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"all {MAX_RETRIES} attempts failed for task {task_id}"
                        )

            if last_error:
                await repo.update_moderation_result(
                    task_id,
                    "failed",
                    error_message=str(last_error)
                )
                await send_to_dlq(
                    producer,
                    data,
                    last_error,
                )

    finally:
        await consumer.stop()
        await producer.stop()
        await repo.disconnect()


if __name__ == "__main__":
    asyncio.run(run_worker())
