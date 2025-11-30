import asyncio
import queue
from typing import Union, Any

from models.settings.postgres.connection import PostgresConnectionHandler
from models.repository.user_postgres_repository import UserPostgresRepository


async def backend_task(communication_channel: Union[Any, queue.Queue, asyncio.Queue]):
    """
    Perform a background task to insert user data into a PostgreSQL database.
    Otimizado para usar conexão persistente e inserção em massa (bulk insert).
    Suporta multiprocessing.Pipe, queue.Queue (threading) e asyncio.Queue (asyncio).

    Args:
        communication_channel: Pode ser um multiprocessing.Pipe, queue.Queue
                              ou asyncio.Queue para comunicação.

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

    try:
        while True:
            # Detecta o tipo de canal e recebe mensagem
            if isinstance(communication_channel, asyncio.Queue):
                # Para asyncio: usa await diretamente (nativo assíncrono)
                message = await communication_channel.get()
            elif isinstance(communication_channel, queue.Queue):
                # Para threading: usa executor (operação bloqueante)
                message = await asyncio.get_event_loop().run_in_executor(
                    None, communication_channel.get
                )
            else:
                # Para multiprocessing: usa executor (operação bloqueante)
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
