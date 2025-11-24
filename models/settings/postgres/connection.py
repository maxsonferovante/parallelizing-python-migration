import asyncio
import asyncpg

from models.settings.config import POSTGRES_CONFIG


class PostgresConnectionHandler:
    def __init__(self) -> None:
        self.__connection_string = self.__connection_string()
        self.__connection = None
        self.pool = None

    def __connection_string(self):
        return f'postgresql://{POSTGRES_CONFIG["POSTGRES_USER"]}:{POSTGRES_CONFIG["POSTGRES_PASSWORD"]}@{POSTGRES_CONFIG["POSTGRES_HOST"]}:{POSTGRES_CONFIG["POSTGRES_PORT"]}/{POSTGRES_CONFIG["POSTGRES_DB"]}'

    async def connect_to_db(self) -> asyncpg.Connection:
        self.__connection = await asyncpg.connect(self.__connection_string)

    def get_connection(self) -> asyncpg.Connection:
        return self.__connection

    async def close_connection(self):
        await self.__connection.close()

    async def __enter__(self) -> asyncpg.Connection:
        return self


db_postgres_connection_handler = PostgresConnectionHandler()
