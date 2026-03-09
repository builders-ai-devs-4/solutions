
from urllib.parse import urlsplit
import os

def get_filename_from_url(url: str = None) -> str:
    if url is None:
        return None
    urlpath = urlsplit(url).path
    return os.path.basename(urlpath)
    