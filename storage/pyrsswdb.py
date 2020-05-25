from pymongo import MongoClient, database

from config.config import Config, Singleton


@Singleton
class PyRSSWDB:

    def __init__(self):
        self.database: database.Database = MongoClient(
            Config.instance().get_mongodb_url()).pyrssw
        
    def get_db(self):
        return self.database
