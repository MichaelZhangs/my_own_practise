# motor_db.py
from typing import Any, Dict, List, Optional,Mapping
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
from bson import ObjectId
from fastapi import HTTPException


class CollectionWrapper:
    def __init__(self, motor_db, collection_name: str):
        self.db = motor_db
        self.collection_name = collection_name

    async def insert(self, document: Dict[str, Any]) -> str:
        """插入文档"""
        return await self.db._insert_one(self.collection_name, document)

    async def insert_one(self, document: Dict[str, Any]) -> str:
        await  self.db._insert_one(self.collection_name, document)

    async def find_one(self, query: Dict[str, Any] = None,
                       projection: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """查询单个文档"""
        print(f"collection_name : {self.collection_name}")
        return await self.db._find_one(self.collection_name, query, projection)

    async def find_many(self, query: Dict[str, Any] = None,
                        projection: Dict[str, Any] = None,
                        sort: List[tuple] = None,
                        skip: int = 0,
                        limit: int = 0) -> List[Dict[str, Any]]:
        """查询多个文档"""
        query = query or {}
        if not isinstance(query, Mapping):
            raise TypeError("query must be a mapping type (e.g. dict)")

        if sort and not isinstance(sort, list):
            raise TypeError("sort must be a list of tuples")

        return await self.db._find_many(
            self.collection_name,
            query=query,
            projection=projection,
            sort=sort,
            skip=skip,
            limit=limit
        )

    async def update_one(self, filter: Dict[str, Any], update: Dict[str, Any], upsert: bool = False, **kwargs) -> bool:
        """更新单个文档，支持upsert操作"""
        if not isinstance(filter, Mapping) or not isinstance(update, Mapping):
            raise TypeError("filter and update must be mapping types (e.g. dict)")
        return await self.db._update_one(self.collection_name, filter, update, upsert=upsert, **kwargs)

    async def delete_one(self, filter: Dict[str, Any]) -> bool:
        """删除单个文档"""
        if not isinstance(filter, Mapping):
            raise TypeError("filter must be a mapping type (e.g. dict)")
        return await self.db._delete_one(self.collection_name, filter)


class MotorDB:
    def __init__(self, host: str = "localhost", port: int = 27017,
                 database: str = "article_db", username: str = None,
                 password: str = None, auth_source: str = "admin"):
        self.host = host
        self.port = port
        self.database_name = database
        self.username = username
        self.password = password
        self.auth_source = auth_source
        self.client: AsyncIOMotorClient = None
        self._db = None

    async def connect(self):
        """连接数据库"""
        try:
            uri = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/?charset=utf8" if self.username else f"mongodb://{self.host}:{self.port}/?charset=utf8"
            self.client = AsyncIOMotorClient(uri, authSource=self.auth_source)
            self._db = self.client[self.database_name]
            await self.client.server_info()
        except PyMongoError as e:
            raise HTTPException(500, f"MongoDB连接失败: {str(e)}")

    def __getattr__(self, name):
        """动态获取集合对象"""
        if name.endswith('_db'):
            collection_name = name[:-3]
            print(f"collection : {collection_name}")
            return CollectionWrapper(self, collection_name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    async def _insert_one(self, collection_name: str, document: Dict[str, Any]) -> str:
        """实际插入操作"""
        try:
            result = await self._db[collection_name].insert_one(document)
            return str(result.inserted_id)
        except PyMongoError as e:
            raise HTTPException(500, f"插入文档失败: {str(e)}")

    async def _find_one(self, collection_name: str, query: Dict[str, Any] = None,
                        projection: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """实际查询操作"""
        try:
            query = query or {}
            return await self._db[collection_name].find_one(query, projection)
        except PyMongoError as e:
            raise HTTPException(500, f"查询文档失败: {str(e)}")

    async def _find_many(self, collection_name: str, query: Dict[str, Any] = None,
                         projection: Dict[str, Any] = None, sort: List[tuple] = None,
                         skip: int = 0, limit: int = 0) -> List[Dict[str, Any]]:
        """实际查询多个文档操作"""
        try:
            # 确保 query 是一个有效的字典
            query = query or {}
            if not isinstance(query, dict):
                raise TypeError("query must be a dictionary")

            cursor = self._db[collection_name].find(filter=query, projection=projection)

            if sort:
                if not isinstance(sort, list):
                    raise TypeError("sort must be a list of tuples")
                cursor = cursor.sort(sort)
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)

            return await cursor.to_list(length=None)
        except PyMongoError as e:
            raise HTTPException(500, f"查询多个文档失败: {str(e)}")
        except TypeError as e:
            raise HTTPException(400, f"参数类型错误: {str(e)}")

    async def _update_one(self, collection_name: str, filter: Dict[str, Any], update: Dict[str, Any], upsert: bool = False, **kwargs) -> bool:
        """更新单个文档，支持 upsert 操作"""
        if not isinstance(filter, Mapping) or not isinstance(update, Mapping):
            raise TypeError("filter and update must be mapping types (e.g. dict)")

        result = await self._db[collection_name].update_one(
            filter,
            update,
            upsert=upsert,
            **kwargs
        )
        return result.modified_count > 0 or (upsert and result.upserted_id is not None)

    async def _delete_one(self, collection_name: str, filter: Dict[str, Any]) -> bool:
        """实际删除操作"""
        try:
            result = await self._db[collection_name].delete_one(filter)
            return result.deleted_count > 0
        except PyMongoError as e:
            raise HTTPException(500, f"删除文档失败: {str(e)}")
