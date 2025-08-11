"""HTTP client utilities with default timeouts and configuration."""

from typing import Optional
import requests


class HTTPSession(requests.Session):
    """Session with default timeout configuration."""

    DEFAULT_TIMEOUT = 30  # 30 seconds timeout
    DEFAULT_CONNECT_TIMEOUT = 10  # 10 seconds connection timeout

    def __init__(
        self, timeout: Optional[float] = None, connect_timeout: Optional[float] = None
    ):
        super().__init__()

        # Try to get timeout from config, fallback to defaults
        try:
            from config.config import (
                Config,
                DEFAULT_HTTP_TIMEOUT,
                DEFAULT_HTTP_CONNECT_TIMEOUT,
                HTTP_TIMEOUT_KEY,
                HTTP_CONNECT_TIMEOUT_KEY,
            )

            config_instance = Config.instance()
            self.timeout = float(
                config_instance.get_property(
                    HTTP_TIMEOUT_KEY, str(DEFAULT_HTTP_TIMEOUT)
                )
            )
            self.connect_timeout = float(
                config_instance.get_property(
                    HTTP_CONNECT_TIMEOUT_KEY, str(DEFAULT_HTTP_CONNECT_TIMEOUT)
                )
            )
        except Exception:
            # Fallback to provided values or defaults if config loading fails
            self.timeout = timeout or self.DEFAULT_TIMEOUT
            self.connect_timeout = connect_timeout or self.DEFAULT_CONNECT_TIMEOUT

        # Set default headers
        self.headers.update({"User-Agent": "Mozilla/5.0 (compatible; pyrssw/1.0)"})

    def get(self, url, **kwargs):
        """Override get to add default timeout if not specified."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = (self.connect_timeout, self.timeout)
        return super().get(url, **kwargs)

    def post(self, url, **kwargs):
        """Override post to add default timeout if not specified."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = (self.connect_timeout, self.timeout)
        return super().post(url, **kwargs)

    def head(self, url, **kwargs):
        """Override head to add default timeout if not specified."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = (self.connect_timeout, self.timeout)
        return super().head(url, **kwargs)

    def put(self, url, **kwargs):
        """Override put to add default timeout if not specified."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = (self.connect_timeout, self.timeout)
        return super().put(url, **kwargs)

    def delete(self, url, **kwargs):
        """Override delete to add default timeout if not specified."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = (self.connect_timeout, self.timeout)
        return super().delete(url, **kwargs)


class HTTPClient:
    """HTTP client with default timeout and retry configuration."""

    DEFAULT_TIMEOUT = 30  # 30 seconds timeout
    DEFAULT_CONNECT_TIMEOUT = 10  # 10 seconds connection timeout

    def __init__(
        self, timeout: Optional[float] = None, connect_timeout: Optional[float] = None
    ):
        self.session = requests.Session()

        # Try to get timeout from config, fallback to defaults
        try:
            from config.config import (
                Config,
                DEFAULT_HTTP_TIMEOUT,
                DEFAULT_HTTP_CONNECT_TIMEOUT,
                HTTP_TIMEOUT_KEY,
                HTTP_CONNECT_TIMEOUT_KEY,
            )

            config_instance = Config.instance()
            self.timeout = float(
                config_instance.get_property(
                    HTTP_TIMEOUT_KEY, str(DEFAULT_HTTP_TIMEOUT)
                )
            )
            self.connect_timeout = float(
                config_instance.get_property(
                    HTTP_CONNECT_TIMEOUT_KEY, str(DEFAULT_HTTP_CONNECT_TIMEOUT)
                )
            )
        except Exception:
            # Fallback to provided values or defaults if config loading fails
            self.timeout = timeout or self.DEFAULT_TIMEOUT
            self.connect_timeout = connect_timeout or self.DEFAULT_CONNECT_TIMEOUT

        # Set default headers
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; pyrssw/1.0)"}
        )

    def get(self, url: str, **kwargs):
        """GET request with default timeout."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = (self.connect_timeout, self.timeout)
        return self.session.get(url, **kwargs)

    def post(self, url: str, **kwargs):
        """POST request with default timeout."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = (self.connect_timeout, self.timeout)
        return self.session.post(url, **kwargs)

    def head(self, url: str, **kwargs):
        """HEAD request with default timeout."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = (self.connect_timeout, self.timeout)
        return self.session.head(url, **kwargs)

    def put(self, url: str, **kwargs):
        """PUT request with default timeout."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = (self.connect_timeout, self.timeout)
        return self.session.put(url, **kwargs)

    def delete(self, url: str, **kwargs):
        """DELETE request with default timeout."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = (self.connect_timeout, self.timeout)
        return self.session.delete(url, **kwargs)


# Instance globale pour l'application
http_client = HTTPClient()


def create_session_with_timeout() -> HTTPSession:
    """Factory function to create a session with timeout."""
    return HTTPSession()
