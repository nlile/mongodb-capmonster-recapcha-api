import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
import certifi
from dotenv import load_dotenv, find_dotenv

"""
    Hacky MDB for use on the local (Windows) server
"""

# Load env
load_dotenv(find_dotenv())


class MongoDB:
    """
    Hacky class for MongoDB
    """
    def __init__(self,
                 mdb_uri: str = os.getenv("MDB_URI"),
                 database: str = str(os.getenv("MDB_DATABASE")),
                 collection: str = str(os.getenv("MDB_COLLECTION")),
                 ):
        # For Windows
        self.ca = certifi.where()
        self.mdb_uri = mdb_uri
        self.client: AsyncIOMotorClient = AsyncIOMotorClient(self.mdb_uri, tlsCAFile=self.ca)
        self.database_name = database
        # self.database = self.client[f"{self.database_name}"]
        self.collection_name = collection
        # self.collection = self.database[f"{self.collection_name}"]
        self.collection = None

    async def get_db(self) -> AsyncIOMotorClient:
        """
        Return database client instance.
        Returns:
            An instance of AsyncIOMotorClient
        """
        if not self.client:
            self.client = AsyncIOMotorClient(self.mdb_uri, tlsCAFile=self.ca)
        return self.client

    async def get_collection(self, client: AsyncIOMotorClient = None, collection: str = None) -> AsyncIOMotorCollection:
        if not collection:
            collection = self.collection_name
        if not client:
            client = await self.get_db()
        self.collection = client[self.database_name][collection]
        # n = await self.collection.count_documents({})
        # print('%s documents in collection' % n)
        return self.collection
