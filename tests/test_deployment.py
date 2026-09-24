import unittest
from dhruva.deployment import check, URL


class Response:
    status=200
    def __init__(self,body=b'ok',url=URL): self.body=body; self.url=url
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self,size): return self.body
    def geturl(self): return self.url


class DeploymentTests(unittest.TestCase):
    def test_ready_sleep_and_failure_distinguished(self):
        self.assertEqual(check(lambda *a,**kw:Response()),[])
        self.assertIn('UNVERIFIED',check(lambda *a,**kw:Response(b'html','https://share.streamlit.io'))[0])
        def unavailable(*a,**kw): raise TimeoutError('fixture')
        self.assertIn('TimeoutError',check(unavailable)[0])
