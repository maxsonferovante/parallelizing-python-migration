import asyncio

from models.settings.postgres.connection import PostgresConnectionHandler
from models.repository.user_postgres_repository import UserPostgresRepository


async def backend_task(child_conn):
    """
    Perform a background task to insert user data into a PostgreSQL database.

    Args:
        child_conn: A multiprocessing connection object for communication with the parent process.

    Returns:
        None

    Raises:
        Exception: If an error occurs during the database connection or user insertion.

    """
    while True:
        message = await asyncio.get_event_loop().run_in_executor(None, child_conn.recv)

        if message == []:
            break
        try:
            connection = PostgresConnectionHandler()
            await connection.connect_to_db()
            for user in message:
                await UserPostgresRepository(connection.get_connection()).insert_user(
                    username=user["username"], email=user["email"], age=user["age"]
                )
            await connection.close_connection()
        except Exception as e:
            print(f"Aqui está sendo gerado um erro: {e}")
