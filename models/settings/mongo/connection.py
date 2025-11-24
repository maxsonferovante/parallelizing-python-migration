import motor.motor_asyncio

from models.settings.config import MONGO_CONFIG


class MongoConnectionHandler:
    def __init__(self):
        self.__connection_string = self.create_connection_string()
        self.__client = None
        self.__db = None

    def connect_to_db(self):
        self.__client = motor.motor_asyncio.AsyncIOMotorClient(
            self.__connection_string,
        )

        self.__db = self.__client.get_database(MONGO_CONFIG["MONGO_DB"])

    async def close_connection(self):
        pass

    def create_connection_string(self) -> str:
        return f"mongodb://{MONGO_CONFIG['MONGO_USER']}:{MONGO_CONFIG['MONGO_PASSWORD']}@{MONGO_CONFIG['MONGO_HOST']}:{MONGO_CONFIG['MONGO_PORT']}/{MONGO_CONFIG['MONGO_DB']}?authSource=admin"

    def get_cliente(self) -> motor.motor_asyncio.AsyncIOMotorClient:
        return self.__client

    def get_db_collenction(
        self, collenction
    ) -> motor.motor_asyncio.AsyncIOMotorDatabase:
        return self.__db.get_collection(collenction)

    async def __enter__(self) -> motor.motor_asyncio.AsyncIOMotorClient:
        return self


db_mongo_connection_handler = MongoConnectionHandler()
