from abc import ABCMeta, abstractmethod
from typing import Optional
from pyrssw_handlers.email_handlers.real_estate import Assets


class AbstractEmailHandler(metaclass=ABCMeta):

    def __init__(self, url_prefix: Optional[str], assets: Assets):
        self.url_prefix: Optional[str] = url_prefix
        self.assets: Assets = assets

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, "process_message") and
                callable(subclass.process_message)
                or NotImplemented)

    @abstractmethod
    def process_message(self, msg):
        """Process the email and feed the assets

        Arguments:
            msg {[type]} -- Email to parse
        """
