import json
from datetime import datetime, timezone
from aiokafka import AIOKafkaProducer

KAFKA_SERVERS = "localhost:9092"
TOPIC_MODERATION = "moderation"


class KafkaProducer:
    def __init__(self):
        self.producer = None

    async def start(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_SERVERS
        )
        await self.producer.start()

    async def stop(self):
        if self.producer:
            await self.producer.stop()

    async def send_moderation_request(self, item_id: int, task_id: int):
        message = {
            "item_id": item_id,
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        value = json.dumps(message).encode("utf-8")
        await self.producer.send_and_wait(TOPIC_MODERATION, value)


kafka_producer = KafkaProducer()
