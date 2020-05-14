from abc import ABC, abstractmethod
from typing import List, Optional

from typing_extensions import Type

from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler

class AbstractPyRSSWHTTPServer(ABC):
    
    @abstractmethod
    def get_auth_key(self) -> Optional[str]:
        pass

    @abstractmethod
    def get_serving_url_prefix(self) -> Optional[str]:
        pass
