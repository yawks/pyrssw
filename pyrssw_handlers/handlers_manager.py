import importlib
import inspect
import logging
import os
from glob import glob
from typing import List

from typing_extensions import Type

from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler

from utils.singleton import Singleton


@Singleton
class HandlersManager:
    """Singleton class which provides handlers list"""

    _handlers: List[Type[PyRSSWRequestHandler]] = []

    def get_handlers(self):
        if len(self._handlers) == 0:
            self._load_handlers()
        
        return self._handlers

    def _load_handlers(self):
        for handler in glob("pyrssw_handlers/*.py"):
            module_name = ".%s" % os.path.basename(handler).strip(".py")
            module = importlib.import_module(module_name, package="pyrssw_handlers")
            if hasattr(module, "PyRSSWRequestHandler") and not hasattr(module, "ABC"):
                for member in inspect.getmembers(module):
                    if member[0].find("__") == -1 and isinstance(member[1], type) and issubclass(member[1], getattr(module, "PyRSSWRequestHandler")) and member[1].__name__ != "PyRSSWRequestHandler":
                        # do not add the abstract class in the handlers list and avoid native types
                        self._load_handler(member)

    def _load_handler(self, member):
        try:
            member[1]() #just try to instanciate to check if everything is ok
        except Exception as e:
            logging.getLogger().error("Error instanciating the class '%s' : %s" % (member[0], str(e)))

        self._handlers.append(member[1])
