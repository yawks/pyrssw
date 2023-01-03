import re
import importlib
import inspect
import logging
import os
from glob import glob
from typing import Dict, List, cast

from typing_extensions import Type

from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler

from utils.singleton import Singleton


@Singleton
class HandlersManager:
    """Singleton class which provides handlers list"""

    _handlers: Dict[str, Type[PyRSSWRequestHandler]] = {}

    def get_handlers(self) -> Dict[str, Type[PyRSSWRequestHandler]]:
        if len(self._handlers) == 0:
            self._load_handlers()

        return self._handlers

    def _load_handlers(self):
        for handler in glob("pyrssw_handlers/*.py"):
            module_name = ".%s" % re.sub( "\.py$", "", os.path.basename(handler))
            module = importlib.import_module(
                module_name, package="pyrssw_handlers")
            if hasattr(module, "PyRSSWRequestHandler") and not hasattr(module, "ABC"):
                for member in inspect.getmembers(module):
                    if member[0].find("__") == -1 and isinstance(member[1], type) and issubclass(member[1], getattr(module, "PyRSSWRequestHandler", "")) and member[1].__name__ != "PyRSSWRequestHandler":
                        # do not add the abstract class in the handlers list and avoid native types
                        self._load_handler(member)

    def _load_handler(self, member):
        try:
            handler_instance = cast(PyRSSWRequestHandler, member[1]())
            self._handlers[handler_instance.get_handler_name_for_url()
                           ] = member[1]
        except Exception as e:
            logging.getLogger().error("Error instanciating the class '%s' : %s" %
                                      (member[0], str(e)))
