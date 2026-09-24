"""Bounded deployment probe; HTTP liveness is not portfolio correctness."""
import urllib.request
import http.cookiejar

# Community Cloud's actual app iframe base, observed in the public page.
URL='https://dhruva-andy7204.streamlit.app/~/+/_stcore/health'


def check(opener=None):
    if opener is None:
        opener=urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())).open
    try:
        with opener(URL,timeout=15) as response:
            body=response.read(256).decode('utf-8',errors='replace').strip()
            if response.status!=200 or response.geturl()!=URL or body.lower()!='ok':
                return ['DEPLOYMENT UNVERIFIED: health endpoint redirected or not ready; app may be asleep']
        return []
    except Exception as exc:
        return [f'DEPLOYMENT UNREACHABLE: {type(exc).__name__}: {exc}']
