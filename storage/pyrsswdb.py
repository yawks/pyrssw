from pymongo import MongoClient, database
import logging
from config.config import Config, Singleton


@Singleton
class PyRSSWDB:

    def __init__(self):
        try:
            if Config.instance().get_mongodb_url() == "":
                logging.getLogger().info(
                    "Storage support disabled: No mongo db connection defined, pyrssw will work anyway")
                # in that case we provided a fake db manager as the database only provides non vital features
                self.database: database.Database = FakeDB()
            else:
                self.database: database.Database = MongoClient(
                    Config.instance().get_mongodb_url()).pyrssw

                # this query checks the mongo db link is functional
                self.database.sessions.find_one({"sessionid": "--"})
                logging.getLogger().info("Support storage enabled: the mongo db is up and running")
        except Exception as e:
            logging.getLogger().error(
                "Storage support disabled: Unable to instanciate the mongo db: '%s' pyrssw will work anyway", e)
            # in that case we provided a fake db manager as the database only provides non vital features
            self.database: database.Database = FakeDB()

    def get_db(self):
        return self.database


class FakeDB(database.Database):
    def __init__(self):
        self.sessions = FakeTable()
        self.read_articles = FakeTable()

    def __getitem__(self, name):
        # overrides the __getitem__ of the super class
        pass


class FakeTable():
    def find_one(self, params: dict):
        return None

    def update_one(self, obj: dict, params: dict, b: bool):
        return None

    def delete_many(self, params: dict):
        return None

    def insert(self, params: dict):
        return None
