import re
from typing import Optional
from urllib.parse import urlparse


URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https://
    # domain...
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


def is_url_valid(url: Optional[str]) -> bool:
    is_url_valid: bool = False
    if url is not None and url != "":
        is_url_valid = re.match(URL_REGEX, url) is not None
    return is_url_valid


def is_a_picture_url(href: str) -> bool:
        """Returns True if the href is a link to a picture

        Args:
            href (str): url

        Returns:
            bool: True if the href leads to real content
        """
        _is_a_picture_link: bool = False
        parsed_url = urlparse(href)
        for extension in [".jpg", ".jpeg", ".png", ".gif"]:
            if parsed_url.path.lower().endswith(extension):
                _is_a_picture_link = True
                break

        return _is_a_picture_link

def is_a_video_url(href: str) -> bool:
        """Returns True if the href is a link to a video

        Args:
            href (str): url

        Returns:
            bool: True if the href leads to real content
        """
        _is_a_video_link: bool = False
        parsed_url = urlparse(href)
        for extension in [".mp4", ".avi"]:
            if parsed_url.path.lower().endswith(extension):
                _is_a_video_link = True
                break

        return _is_a_video_link
