import asyncio

from typing import AsyncGenerator


class UserMongoRepository:
    def __init__(self, user_collenction):

        self.__collenction = user_collenction

    async def create_user(self, user: dict) -> int:

        result = await self.__collenction.insert_one(user)

        return result.inserted_id

    async def get_user(self, user_id: int) -> dict:
        user = await self.__collenction.find_one({"id": user_id})

    async def count_documents(self) -> int:
        return await self.__collenction.count_documents({})

    async def create_users(self, users: list) -> None:
        await self.__collenction.insert_many(users)

    async def get_all() -> list:
        users_curson = self.__collenction.find().sort("id")
        return await users_curson.to_list()

    async def get_all_paginated(
        self, skip: int, limit: int
    ) -> AsyncGenerator[list, None]:
        users_curson = self.__collenction.find().skip(skip).limit(limit)

        users_list = await users_curson.to_list(length=limit)

        if not users_list:
            return
        yield users_list

        async for more_users in self.get_all_paginated(skip + limit, limit):
            yield more_users

    async def delete_all(self) -> None:
        await self.__collenction.delete_many({})
