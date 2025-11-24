import asyncio

from models.settings.postgres.connection import PostgresConnectionHandler
from models.repository.user_postgres_repository import UserPostgresRepository


async def backend_task(child_conn):
    """
    Perform a background task to insert user data into a PostgreSQL database.
    Otimizado para usar conexão persistente e inserção em massa (bulk insert).

    Args:
        child_conn: A multiprocessing connection object for communication with the parent process.

    Returns:
        None

    Raises:
        Exception: If an error occurs during the database connection or user insertion.

    """
    # Abre conexão UMA VEZ no início do processo (evita churn de conexões)
    connection = PostgresConnectionHandler()
    await connection.connect_to_db()
    conn = connection.get_connection()
    repository = UserPostgresRepository(conn)

    try:
        while True:
            # Recebe mensagem do pipe (operação bloqueante executada em executor)
            message = await asyncio.get_event_loop().run_in_executor(None, child_conn.recv)

            if message == []:
                break

            try:
                # Inserção em massa: 1 única ida ao banco para todo o lote
                await repository.insert_many_users(message)
            except Exception as e:
                print(f"Erro ao inserir lote: {e}")

    finally:
        # Fecha conexão apenas quando o processo terminar
        await connection.close_connection()
