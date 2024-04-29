import asyncio

from models.settings.postgres.connection import db_postgres_connection_handler
from models.repository.user_postgres_repository import UserPostgresRepository

async def backend_task(data: list):
    try:       
        for user in data:
            await UserPostgresRepository(
                db_postgres_connection_handler.get_connection()
                ).insert_user(
                    username=user["username"],
                    email=user["email"],
                    age=user["age"]
                )        
        return len(data)
    except Exception as e:
        print(e)
        
    