import asyncio
import queue
from typing import Union, Any

from models.settings.postgres.connection import PostgresConnectionHandler
from models.repository.user_postgres_repository import UserPostgresRepository


async def backend_task(communication_channel: Union[Any, queue.Queue]):
    """
    Perform a background task to insert user data into a PostgreSQL database.
    Otimizado para usar conexão persistente e inserção em massa (bulk insert).
    Suporta tanto multiprocessing.Pipe quanto queue.Queue (threading).

    Args:
        communication_channel: Pode ser um multiprocessing.Pipe ou queue.Queue
                              para comunicação com o processo/thread pai.

    Returns:
        None

    Raises:
        Exception: If an error occurs during the database connection or user insertion.
    """
    # Abre conexão UMA VEZ no início do worker (evita churn de conexões)
    connection = PostgresConnectionHandler()
    await connection.connect_to_db()
    conn = connection.get_connection()
    repository = UserPostgresRepository(conn)

    # Detecta o tipo de canal de comunicação
    is_queue = isinstance(communication_channel, queue.Queue)

    try:
        while True:
            # Recebe mensagem do canal (operação bloqueante executada em executor)
            if is_queue:
                # Para threading: usa queue.Queue.get()
                message = await asyncio.get_event_loop().run_in_executor(
                    None, communication_channel.get
                )
            else:
                # Para multiprocessing: usa Pipe.recv()
                message = await asyncio.get_event_loop().run_in_executor(
                    None, communication_channel.recv
                )

            if message == []:
                break

            try:
                # Inserção em massa: 1 única ida ao banco para todo o lote
                await repository.insert_many_users(message)
            except Exception as e:
                print(f"Erro ao inserir lote: {e}")

    finally:
        # Fecha conexão apenas quando o worker terminar
        await connection.close_connection()
