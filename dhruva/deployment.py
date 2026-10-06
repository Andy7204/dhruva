"""Bounded deployment probe; HTTP liveness is not portfolio correctness.

Streamlit Community Cloud answers bots with a redirect to its auth/wake page and
puts idle apps to sleep; both are normal and wake on the next visit. Only a
missing app (404), a server error or no connection counts as an incident.
"""
import http.client
from urllib.parse import urlparse

URL = 'https://dhruva-andy7204.streamlit.app/'


def check(url=URL, connect=None):
    u = urlparse(url)
    try:
        conn = (connect or http.client.HTTPSConnection)(u.netloc, timeout=15)
        conn.request('GET', u.path or '/', headers={'User-Agent': 'dhruva-watchdog'})
        status = conn.getresponse().status
        conn.close()
    except Exception as exc:
        return [f'DEPLOYMENT UNREACHABLE: {type(exc).__name__}: {exc}']
    if status == 404 or status >= 500:
        return [f'DEPLOYMENT ERROR: HTTP {status} from {url}']
    return []  # 200, or 3xx to the Streamlit auth/wake page: app exists (it may be asleep)
