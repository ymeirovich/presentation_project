from typing import Any, Dict, Optional
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger("agent.http")

_DEFAULT_TIMEOUT = 10  # seconds

class TimeoutHTTPAdapter(HTTPAdapter):
    """HTTPAdapter with a default timeout."""
    def __init__(self, *args, timeout=_DEFAULT_TIMEOUT, **kwargs):
        self.timeout = timeout
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        kwargs.setdefault('timeout', self.timeout)
        return super().send(request, **kwargs)
    
def _build_session() -> requests.Session:
    session=requests.Session()
    #Retries for transient error (connection issues, 5xx)
    retries= Retry(
        total=3,
        backoff_factor=0.5, #0.5s, 1s, 2s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS"],
        raise_on_status=False,
    )
    adapter = TimeoutHTTPAdapter(max_retries=retries, timeout=_DEFAULT_TIMEOUT)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

_session = _build_session()

def get_json(url:str, params:Optional[Dict[str,Any]]=None, headers: Optional[Dict[str,str]]=None) -> Dict[str, Any]:
    """Make a GET request and return parsed JSON with good errors."""

    log.debug("GET %s params=%s", url,params)
    try:
        resp= _session.get(url, params=params, headers=headers) 
    except requests.RequestException as e:
        #Network-level issue (DNS, connection, timeout)
        log.error("Network error requesting %s: %s", url, e)
        raise

    #Application-level checks
    if not resp.ok:
        #Don't crash sliently; include status and body snippet for diagnosis
        body = (resp.text or "")[:300]  # Limit to 300 chars
        msg = f"HTTP {resp.status_code} for {url}. Body starts: {body!r}"
        log.error(msg)
        resp.raise_for_status()  # Raises HTTPError for bad status codes

    try:
        return resp.json()
    except ValueError:
        #Content wasn't JSON
        body = (resp.text or "")[:300]  # Limit to 300 chars
        msg = f"Invalid JSON from {url}. Body starts: {body!r}"
        log.error(msg)
        raise

    