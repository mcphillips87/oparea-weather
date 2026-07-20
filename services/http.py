import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT = (5, 10)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "CPAOA Weather App (mcphillips87@gmail.com)",
    "Connection": "close",
})

retry = Retry(
    total=1,
    connect=1,
    read=0,
    status=1,
    backoff_factor=0.25,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET"]),
    raise_on_status=False,
)

adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
SESSION.mount("https://", adapter)
SESSION.mount("http://", adapter)


def get(url, *, timeout=DEFAULT_TIMEOUT, **kwargs):
    return SESSION.get(url, timeout=timeout, **kwargs)
