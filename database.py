import asyncpg

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"


class AdRepository:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(DATABASE_URL)

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def get_item_with_seller(self, item_id: int):
        query = """
            SELECT i.images_qty, i.description, i.category, u.is_verified_seller
            FROM items i
            JOIN users u ON i.seller_id = u.id
            WHERE i.id = $1
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, item_id)

    async def create_user(self, is_verified_seller: bool):
        query = """
            INSERT INTO users (is_verified_seller) VALUES ($1) RETURNING id
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, is_verified_seller)

    async def create_item(
                self,
                seller_id: int,
                name: str,
                description: str,
                category: int,
                images_qty: int
            ):
        query = """
            INSERT INTO items (seller_id, name, description, category, images_qty) VALUES ($1, $2, $3, $4, $5) RETURNING id
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                query,
                seller_id,
                name,
                description,
                category,
                images_qty
            )


repo = AdRepository()
