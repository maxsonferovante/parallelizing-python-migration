import asyncio


class UserPostgresRepository:
    def __init__(self, conn):
        self.conn = conn

    async def create_table(self):
        create_table_query = """CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(50) NOT NULL,
            age INT NOT NULL,
            registed_at TIMESTAMP NOT NULL DEFAULT NOW()        
        )"""
        await self.conn.fetch(create_table_query)

    async def insert_user(self, username, email, age):
        insert_query = (
            """INSERT INTO users (username, email, age) VALUES ($1, $2, $3)"""
        )
        await self.conn.fetch(insert_query, username, email, age)

    async def get_users(self):
        return await self.conn.fetch("""SELECT * FROM users""")

    async def drop_table(self):
        await self.conn.fetch("""DROP TABLE IF EXISTS users""")

    async def count_users(self):
        return await self.conn.fetchval("""SELECT COUNT(*) FROM users""")
