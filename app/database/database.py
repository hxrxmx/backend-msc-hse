import time
from typing import Optional
import asyncpg
from hashlib import sha256


from app.metrics.metrics import DB_QUERY_DURATION


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
            SELECT i.images_qty, i.description,
                i.category, u.is_verified_seller
            FROM items i
            JOIN users u ON i.seller_id = u.id
            WHERE i.id = $1
        """
        start_time = time.time()
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(query, item_id)

        DB_QUERY_DURATION.labels(
            query_type="get_item_with_seller"
        ).observe(time.time() - start_time)
        return result

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
            INSERT INTO items (seller_id, name,
                description, category, images_qty)
            VALUES ($1, $2, $3, $4, $5) RETURNING id
        """

        start_time = time.time()
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                query,
                seller_id,
                name,
                description,
                category,
                images_qty
            )

        DB_QUERY_DURATION.labels(
            query_type="create_item"
        ).observe(time.time() - start_time)
        return result

    async def create_moderation_task(self, item_id: int):
        query = """
            INSERT INTO moderation_results (item_id, status)
            VALUES ($1, 'pending') RETURNING id
        """
        start_time = time.time()
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, item_id)

        DB_QUERY_DURATION.labels(
            query_type="create_moderation_task"
        ).observe(time.time() - start_time)

    async def get_moderation_result(self, task_id: int):
        query = """
            SELECT * FROM moderation_results WHERE id = $1
        """
        start_time = time.time()
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, task_id)

        DB_QUERY_DURATION.labels(
            query_type="get_moderation_result"
        ).observe(time.time() - start_time)

    async def update_moderation_result(
        self,
        task_id: int,
        status: str,
        is_violation: Optional[bool] = None,
        probability: Optional[float] = None,
        error_message: Optional[str] = None,
    ):
        query = """
            UPDATE moderation_results
            SET status = $2, is_violation = $3, probability = $4,
                error_message = $5, processed_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """
        start_time = time.time()
        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                task_id,
                status,
                is_violation,
                probability,
                error_message,
            )
        DB_QUERY_DURATION.labels(
            query_type="update"
        ).observe(time.time() - start_time)

    async def item_exists(self, item_id: int):
        query = "SELECT 1 FROM items WHERE id = $1"
        start_time = time.time()

        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, item_id) is not None

        DB_QUERY_DURATION.labels(
            query_type="item_exists"
        ).observe(time.time() - start_time)

    async def delete_item(self, item_id: int):
        start_time = time.time()
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM moderation_results WHERE item_id = $1", item_id)
                await conn.execute("DELETE FROM items WHERE id = $1", item_id)

        DB_QUERY_DURATION.labels(
            query_type="delete"
        ).observe(time.time() - start_time)


class AccountRepository:
    def __init__(self, pool):
        self.pool = pool

    def _hash_password(self, password: str) -> str:
        return sha256(password.encode()).hexdigest()

    async def create(self, login, password):
        hashed = self._hash_password(password)
        query = """
            INSERT INTO account (login, password) VALUES ($1, $2) RETURNING id
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, login, hashed)

    async def find_by_id(self, account_id):
        query = "SELECT * FROM account WHERE id = $1"
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, account_id)

    async def find_by_login(self, login):
        query = "SELECT * FROM account WHERE login = $1"
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, login)

    async def delete(self, account_id):
        query = "DELETE FROM account WHERE id = $1"
        async with self.pool.acquire() as conn:
            await conn.execute(query, account_id)

    async def block(self, account_id):
        query = "UPDATE account SET is_blocked = True WHERE id = $1"
        async with self.pool.acquire() as conn:
            await conn.execute(query, account_id)

    async def verify_password(self, login, password):
        account = await self.find_by_login(login)
        if not account or account['is_blocked']:
            return None
        if self._hash_password(password) == account['password']:
            return account
        return None


repo = AdRepository()
account_repo = AccountRepository(repo.pool)
