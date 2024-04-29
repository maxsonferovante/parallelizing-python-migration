import asyncio
import logging

from concurrent.futures import ProcessPoolExecutor, as_completed

from faker import Faker

from models.settings.postgres.connection import db_postgres_connection_handler
from models.settings.mongo.connection import MongoConnectionHandler

from models.repository.user_postgres_repository import UserPostgresRepository
from models.repository.user_mongo_repository import UserMongoRepository

from models.entities.user import User

from params import AMOUNT_USERS_SEED

async def seed_mongo(name_process: str):
    """
    Seed MongoDB with user data.

    Args:
        name_process (str): The name of the process.

    Returns:
        str: A message indicating the number of users created in MongoDB.

    Raises:
        Exception: If an error occurs while seeding MongoDB.

    """
    try:
        logging.info(f"Connecting to MongoDB... {name_process}")        
        
        db_mongo_connection_handler = MongoConnectionHandler()
        db_mongo_connection_handler.connect_to_db()
        
        logging.info(f"Connected to MongoDB {name_process}")
        
        user_mongo_repository = UserMongoRepository(
           db_mongo_connection_handler.get_db_collenction(User.__name__)
        )
    
        logging.info(f"Creating users in MongoDB... {name_process}")
        
        part = AMOUNT_USERS_SEED // 100
        for i in range(1,100):
            logging.info(f"Creating users in MongoDB {i} - {part} {name_process}")
            users = [
                {
                    "id": id,
                    "username": Faker().name(),
                    "email": Faker().email(),
                    "age": Faker().random_int(min=18, max=100)
                }
                for id in range(part)
            ]
            await user_mongo_repository.create_users(users)
            users = None
            logging.info(f"Users created in MongoDB {i} - {part*i}/{AMOUNT_USERS_SEED} {name_process}")
            
        
        # logging.info(f"Users created in MongoDB {AMOUNT_USERS} {name_process}")
        return f"Users created in MongoDB {AMOUNT_USERS_SEED} {name_process}"
    except Exception as e:
        logging.error(f"An error occurred while seeding MongoDB {name_process}")
        logging.error(e)
    finally:
        await db_mongo_connection_handler.close_connection()
        logging.info(f"Connection to MongoDB closed {name_process}")
 
async def seed_postgres():
    try:
        logging.info("Connecting to PostgreSQL...")
        
        await db_postgres_connection_handler.connect_to_db()
        
        logging.info("Connected to PostgreSQL")
        
        logging.info("Creating users table...")
        user_postgres_repository = UserPostgresRepository(
            db_postgres_connection_handler.get_connection()
        )
        await user_postgres_repository.create_table()
        
        logging.info("Users table created")
        
    except Exception as e:
        logging.error("An error occurred while seeding PostgreSQL")
        logging.error(e)
    finally:
        await db_postgres_connection_handler.close_connection()       
        logging.info("Connection to PostgreSQL closed")

def run_seed_mongo(name_process: str):
    asyncio.run(seed_mongo(name_process))
    
async def main():
    max_workers = 10
    pool = ProcessPoolExecutor(max_workers=max_workers)

    logging.info("Seeding Mongd DB in parallel with 10 processes...")
    tasks_futures = [pool.submit(run_seed_mongo, f"Process {i}") for i in range(max_workers)]
    
    
    while True:
        await asyncio.sleep(1)
        logging.info("Waiting for tasks to finish")
        if all(task_future.done() for task_future in tasks_futures):
            break       
        
    
    for task_future in as_completed(tasks_futures):
                logging.info(task_future.result())
    
    
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
     
    asyncio.run(main()) 