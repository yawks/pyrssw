import datetime
import pickle
from typing import Optional

import requests
from dateutil.relativedelta import relativedelta

from config.config import Config, Singleton
from storage.pyrsswdb import PyRSSWDB


@Singleton
class SessionStore:
    """ Handle storage of sessions.
    Clean old entries before doing anything.
    """

    def upsert_session(self, sessionid: str, session: requests.Session):
        self._clean_old_entries()
        PyRSSWDB.instance().get_db().sessions.update_one({"sessionid": sessionid},
                                                         {"$set": {"session": pickle.dumps(session),
                                                                   "date": datetime.datetime.now()}},
                                                         True)

    def _clean_old_entries(self):
        PyRSSWDB.instance().get_db().sessions.delete_many({"date": {"$lt":
                                                                    (datetime.datetime.now() - relativedelta(minutes=Config.instance().get_storage_sessions_duration()))}})  # type: ignore

    def get_session(self, sessionid: str) -> requests.Session:
        """Get a session from sessionid.
        If none found in storage, create a new one.

        Arguments:
            sessionid {str} -- session identifier

        Returns:
            requests.Session -- A session found in the storage or a new one.
        """
        self._clean_old_entries()
        entry = PyRSSWDB.instance().get_db().sessions.find_one(
            {"sessionid": sessionid})
        if not entry is None:
            session: requests.Session = pickle.loads(entry["session"])
        else:
            session: requests.Session = requests.Session()

        return session
