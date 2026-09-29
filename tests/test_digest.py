import json
import tempfile
import unittest
from pathlib import Path
from dhruva.digest import build, post


def book(as_of, orders=(), risk_on=False):
    return {'as_of':as_of,'orders':list(orders),'risk_on':risk_on,'holdings':{},'cash':100.,
            'history':[['d',100.]]*6+[[as_of,101.]],'next_rebalance_in':10}


class DigestTests(unittest.TestCase):
    def test_quiet_day_is_silent_and_changes_or_friday_notify(self):
        prev={'b':book('2026-09-28')}
        self.assertEqual(build(prev,[{'name':'b','state':book('2026-09-29')}])['kind'],'NONE')
        friday=build(prev,[{'name':'b','state':book('2026-10-02')}])
        self.assertEqual(friday['kind'],'WEEKLY'); self.assertIn('+1.00%',friday['text'])
        order={'status':'scheduled','decided_date':'2026-09-29','side':'BUY','symbol':'X.NS'}
        self.assertEqual(build(prev,[{'name':'b','state':book('2026-09-29',[order])}])['kind'],'CHANGE')
        flip=build(prev,[{'name':'b','state':book('2026-09-29',risk_on=True)}])
        self.assertIn('market filter turned ON',flip['text'])

    def test_post_once_per_session(self):
        class Client:
            repo='o/r'; calls=[]
            def request(self,method,path,body=None):
                self.calls.append((method,path))
                return [] if method=='GET' else {'number':7}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'runs').mkdir()
            (root/'runs/digest.json').write_text(json.dumps({'kind':'CHANGE','as_of':'2026-09-29','text':'x'}))
            client=Client()
            self.assertEqual(post(root,client)['status'],'SENT')
            self.assertEqual(post(root,client)['status'],'ALREADY_SENT')
            self.assertEqual(sum(m=='POST' for m,_ in client.calls),2)
