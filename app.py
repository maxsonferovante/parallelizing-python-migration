import asyncio
import time
import multiprocessing

from models.settings.postgres.connection import db_postgres_connection_handler, PostgresConnectionHandler
from models.settings.mongo.connection import db_mongo_connection_handler

from models.repository.user_mongo_repository import UserMongoRepository
from models.repository.user_postgres_repository import UserPostgresRepository
from models.entities.user import User

from cluster.cluster import ClusterMigration

from background_task import backend_task

from utils.print_progress_bar import print_progress_bar
from params import CLUSTER_SIZE, ITEMS_PER_PAGE, AMOUNT_USERS


def start_worker_process(child_conn):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(backend_task(child_conn))
    loop.close()
        

async def main():
    try:
        
        db_mongo_connection_handler.connect_to_db()
                
        user_mongo_repository = UserMongoRepository(
           db_mongo_connection_handler.get_db_collenction(User.__name__)
        )

        await db_postgres_connection_handler.connect_to_db()        
        
        user_postgres_repository = UserPostgresRepository(
            db_postgres_connection_handler.get_connection()
        )              
        await user_postgres_repository.drop_table()
        await user_postgres_repository.create_table()
    
        print (f"Total de usuários cadastrados no MongoDB: {await user_mongo_repository.count_documents()}")                
        
        clusterMigration = ClusterMigration(
            backend_task=backend_task,
            cluster_size=CLUSTER_SIZE
        )
        
        start_time = time.time()

        await clusterMigration.initialize_processes()
                        
        # Usar o MongoDB para pegar páginas de dados
        async for page_of_users in user_mongo_repository.get_all_paginated(skip=0, limit=ITEMS_PER_PAGE):
            users = [user for user in page_of_users]
            
            # Enviar dados para os processos filhos usando o round-robin
            await clusterMigration.start_process(users)
         
        # Enviar uma mensagem vazia para os processos filhos pararem de esperar por dados
        # Esperar que todos os processos filhos terminem
        clusterMigration.awaiting_completion_processes()
                
            
        print(f" Time: { ((time.time() - start_time))}")
        print(f"Total de usuários cadastrados no Postgres: {await user_postgres_repository.count_users()}")
        
    except Exception as e:
        print(e)
    
    finally:
        await db_mongo_connection_handler.close_connection()
        await db_postgres_connection_handler.close_connection()

if __name__ == "__main__":
    asyncio.run(main())