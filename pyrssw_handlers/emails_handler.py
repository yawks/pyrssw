import datetime
import email
import email.header
import imaplib
import logging
import os
import pathlib
import tempfile
from datetime import date, datetime, timedelta
from threading import Thread
from typing import Optional
from pyrssw_handlers.email_handlers.logicimmo_email_handler import LogicImmoEmailHandler
from pyrssw_handlers.email_handlers.seloger_email_handler import SeLogerEmailHandler
from pyrssw_handlers.email_handlers.real_estate import Assets

from lxml import etree

from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler

EMAIL_ACCOUNT = ""
EMAIL_PASSWORD = ""
IMAP_HOST = "imap.gmail.com"

DIGEST_LAST_X_DAYS = 7
EMAIL_FOLDER = "INBOX"

TEMP_FILE_NAME = "pyrssw_email.tmp"
LOCK_FILE_NAME = "pyrssw_email_lock.tmp"

DURATION_BEFORE_REMOVING_LOCK_FILE = 5  # in minutes


class EmailsHandler(PyRSSWRequestHandler):
    """Handler reading emails from seloger and transform them in a rss feed

    Handler name: emails

    RSS parameters: TODO
    """

    @staticmethod
    def get_handler_name() -> str:
        return "emails"

    def get_original_website(self) -> str:
        return ""

    def get_rss_url(self) -> str:
        return ""

    def get_feed(self, parameters: dict) -> str:
        feed = Assets().to_rss_feed()
        tmp_file = os.path.join(tempfile.gettempdir(), TEMP_FILE_NAME)
        if os.path.isfile(tmp_file):
            feed = open(tmp_file, 'r').read()

        # refresh file if too old
        # if not os.path.isfile(tmp_file) or datetime.fromtimestamp(pathlib.Path(tmp_file).stat().st_mtime) < datetime.now() - timedelta(minutes=10) :
        url_prefix: str = ""
        if not self.url_prefix is None:
            url_prefix = self.url_prefix[:len(
                self.url_prefix)-len(self.get_handler_name())]
        EmailsRetriever(tmp_file, url_prefix).start()  # update file

        return feed

    def get_content(self, url: str, parameters: dict) -> str:
        return ""


class EmailsRetriever(Thread):
    def __init__(self, tmp_file: str, url_prefix: Optional[str]):
        Thread.__init__(self)
        self.tmp_file: str = tmp_file
        self.url_prefix: Optional[str] = url_prefix

    def run(self):
        tmp_file = os.path.join(tempfile.gettempdir(), LOCK_FILE_NAME)
        if os.path.isfile(tmp_file) and datetime.fromtimestamp(pathlib.Path(tmp_file).stat().st_mtime) > datetime.now() - timedelta(minutes=DURATION_BEFORE_REMOVING_LOCK_FILE):
            logging.getLogger().info("EmailsRetriever: Another process currently working, pass")
        else:
            logging.getLogger().info("EmailsRetriever: start process")
            open(tmp_file, 'w').write("-")  # create locker
            try:
                today = date.today()
                query = '(SINCE "%s")' % (
                        (today - timedelta(days=DIGEST_LAST_X_DAYS)).strftime("%d-%b-%Y"))

                feed: str = self._read_mails(query).to_rss_feed()
                open(self.tmp_file, "w").write(feed)
            except Exception as e:
                logging.getLogger().info("EmailsRetriever: process failed : %s" % str(e))
            finally:
                os.remove(tmp_file)  # release locker
            logging.getLogger().info("EmailsRetriever: process finished")

    def _process_mailbox(self, mailbox, query, must_send_invitations) -> Assets:
        my_assets: Assets = Assets()

        rv, data = mailbox.search(None, query)
        if rv == 'OK':

            for num in data[0].split():
                rv, data = mailbox.fetch(num, '(RFC822)')
                if rv == 'OK':
                    self._process_message(data, my_assets)
                    #M.store(num, '+FLAGS', '\\Deleted')
        return my_assets

    def _process_message(self, data, my_assets: Assets):
        msg = email.message_from_bytes(data[0][1])

        if msg["From"].find("seloger@al.alerteimmo.com") > -1:
            SeLogerEmailHandler(
                self.url_prefix, my_assets).process_message(msg)
        elif msg["From"].find("alerteimmo@logic-immo.com") > -1 or msg["From"].find("news@logicimmo.nmp1.com") > -1:
            LogicImmoEmailHandler(
                self.url_prefix, my_assets).process_message(msg)

    def _read_mails(self, query) -> Assets:
        my_assets: Assets = Assets()
        M = imaplib.IMAP4_SSL(IMAP_HOST)
        try:
            rv, _ = M.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
            rv, _ = M.list()
            rv, _ = M.select(EMAIL_FOLDER)
            if rv == "OK":
                self._process_mailbox(M, query, True)
                M.close()
            else:
                logging.getLogger().error("EmailsRetriever: ERROR: Unable to open mailbox")
        finally:
            M.logout()

        return my_assets
