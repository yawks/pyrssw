from storage.pyrsswdb import PyRSSWDB
import datetime
from config.config import Singleton, Config
from dateutil.relativedelta import relativedelta


@Singleton
class ArticleStore:
    """ Handle storage of read articles.
    Clean old entries before doing anything.
    """

    def insert_article_as_read(self, user_id: str, url: str):
        if not self.has_article_been_read(user_id, url):
            PyRSSWDB.instance().get_db().read_articles.insert({"id": user_id, "url": url,
                                                               "date": datetime.datetime.now()})

    def _clean_old_entries(self):
        PyRSSWDB.instance().get_db().read_articles.delete_many({"date": {"$lt":
                                                                         (datetime.datetime.now() - relativedelta(days=Config.instance().get_storage_articlesread_age()))}})  # type: ignore

    def has_article_been_read(self, user_id: str, url: str) -> bool:
        self._clean_old_entries()
        return not PyRSSWDB.instance().get_db().read_articles.find_one({"id": user_id, "url": url}) is None
