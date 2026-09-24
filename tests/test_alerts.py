import unittest
from dhruva.alerts import notify


class FakeGitHub:
    repo='owner/repo'
    def __init__(self): self.issues=[]; self.posts=0; self.receipts={}; self.stale=False
    def receipt(self,key,value=None):
        if value is not None: self.receipts[key]=value
        return self.receipts.get(key)
    def request(self,method,path,body=None):
        if method=='GET':
            if '?' in path: return [] if self.stale else [i for i in self.issues if i.get('state')!='closed']
            return next(i for i in self.issues if path.endswith('/'+str(i['number'])))
        if method=='POST':
            self.posts+=1
            issue=dict(body,state='open',number=self.posts,html_url=f'https://github.com/owner/repo/issues/{self.posts}')
            self.issues.append(issue); return issue
        issue=next(i for i in self.issues if path.endswith('/'+str(i['number'])))
        issue.update(body); return issue


class AlertTests(unittest.TestCase):
    def test_failure_duplicate_recovery_without_success_spam(self):
        api=FakeGitHub()
        self.assertEqual(notify('watchdog',[],client=api)['status'],'NO_INCIDENT')
        self.assertEqual(notify('watchdog',['missed run'],client=api)['status'],'CREATED')
        self.assertEqual(notify('watchdog',['missed run'],client=api)['status'],'ALREADY_OPEN')
        self.assertEqual(api.posts,1)
        self.assertEqual(notify('watchdog',[],client=api)['status'],'RECOVERED')

    def test_test_incident_cannot_close_real_incident(self):
        api=FakeGitHub()
        notify('watchdog',['real'],client=api)
        notify('watchdog',['test'],client=api,test=True)
        notify('watchdog',[],client=api,test=True)
        self.assertNotEqual(api.issues[0].get('state'),'closed')

    def test_stale_list_uses_successful_creation_receipt(self):
        api=FakeGitHub(); api.stale=True
        self.assertEqual(notify('watchdog',['failed'],client=api)['status'],'CREATED')
        self.assertEqual(notify('watchdog',['failed'],client=api)['status'],'ALREADY_OPEN')
        self.assertEqual(notify('watchdog',[],client=api)['status'],'RECOVERED')
        self.assertEqual(api.posts,1)


if __name__=='__main__': unittest.main()
