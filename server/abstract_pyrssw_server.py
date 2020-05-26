from abc import ABC, abstractmethod
from typing import Optional


class AbstractPyRSSWHTTPServer(ABC):
    
    @abstractmethod
    def get_auth_key(self) -> Optional[str]:
        pass

    @abstractmethod
    def get_serving_url_prefix(self) -> Optional[str]:
        pass
