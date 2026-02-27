import json
import redis.asyncio as redis


class RedisCache:
    def __init__(self, host="localhost", port=6379, db=0):
        self.client = None
        self.host = host
        self.port = port
        self.db = db
        self.ttl = 1800

    async def connect(self):
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            decode_responses=True
        )

    async def disconnect(self):
        if self.client:
            await self.client.aclose()

    async def get_prediction(self, item_id: int):
        data = await self.client.get(f"pred:{item_id}")
        return json.loads(data) if data else None

    async def set_prediction(self, item_id: int, result: dict):
        await self.client.setex(
            f"pred:{item_id}",
            self.ttl,
            json.dumps(result)
        )

    async def delete_prediction(self, item_id: int):
        await self.client.delete(f"pred:{item_id}")


cache = RedisCache()
