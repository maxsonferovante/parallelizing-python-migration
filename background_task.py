import asyncio

from models.settings.postgres.connection import PostgresConnectionHandler
from models.repository.user_postgres_repository import UserPostgresRepository

async def backend_task(child_conn):
    while True:
        message = await asyncio.get_event_loop().run_in_executor(None, child_conn.recv)
        
        if message == []:
            break
        try:
            connection = PostgresConnectionHandler()
            await connection.connect_to_db()
            for user in message:
                await UserPostgresRepository(
                connection.get_connection()
                ).insert_user(
                                username=user["username"],
                                email=user["email"],
                                age=user["age"]
                )     
            await connection.close_connection()
        except Exception as e:
            print(f"Aqui está sendo gerado um erro: {e}")
