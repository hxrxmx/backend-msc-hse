import asyncio
import asyncpg


async def seed():
    dsn = "postgresql://postgres:postgres@localhost:5435/hw"

    try:
        conn = await asyncpg.connect(dsn)

        await conn.execute("""
            INSERT INTO users (id, is_verified_seller)
            VALUES (1, true)
            ON CONFLICT (id) DO NOTHING
        """)

        await conn.execute("""
            INSERT INTO items (id, seller_id, name, description, category, images_qty)
            VALUES (100, 1, 'Test Item for Monitoring', 'Some long description', 1, 5)
            ON CONFLICT (id) DO NOTHING
        """)

        print("--- Успех! ---")
        print("В базу добавлены: User ID=1, Item ID=100")
        await conn.close()

    except Exception as e:
        print(f"--- Ошибка: {e} ---")

if __name__ == "__main__":
    asyncio.run(seed())
