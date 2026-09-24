"""One operational alert channel: deduplicated GitHub issues via job token."""
import json
import os
from pathlib import Path
import re
import urllib.request
import time
from dhruva.ledger import atomic_write, canonical

RECEIPTS=Path(__file__).resolve().parents[1]/'runs/alerts'


class GitHub:
    def __init__(self):
        self.repo=os.environ['GITHUB_REPOSITORY']
        self.token=os.environ['GITHUB_TOKEN']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',self.repo):
            raise ValueError('Invalid repository')

    def request(self, method, path, body=None):
        if method=='GET': path+=('&' if '?' in path else '?')+'_dhruva='+str(time.time_ns())
        req=urllib.request.Request('https://api.github.com/repos/'+self.repo+path,
            data=None if body is None else json.dumps(body).encode(), method=method,
            headers={'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json',
                     'Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28'})
        with urllib.request.urlopen(req,timeout=30) as response:
            return json.load(response)

    def receipt(self, key, value=None):
        path=RECEIPTS/(key+'.json')
        if value is not None:
            atomic_write(path,canonical({'repository':self.repo,'number':value})+b'\n')
        elif path.exists():
            record=json.loads(path.read_text(encoding='utf-8'))
            if record['repository']==self.repo: return record['number']


def notify(channel, errors, *, client=None, test=False):
    """A single open incident per channel; repeat failures do not spam comments."""
    client=client or GitHub()
    if channel not in ('watchdog','pipeline'): raise ValueError('Unknown alert channel')
    marker='<!-- dhruva-alert:'+channel+(':test' if test else '')+' -->'
    title=('[Dhruva TEST] ' if test else '[Dhruva] ')+channel+' incident'
    issues=[]
    for page in range(1,11):
        batch=client.request('GET',f'/issues?state=open&per_page=100&page={page}')
        issues.extend(batch)
        if len(batch)<100: break
    matches=[i for i in issues if 'pull_request' not in i and i.get('title')==title and marker in (i.get('body') or '')]
    key=channel+('-test' if test else '')
    known=client.receipt(key)
    if known and not any(i['number']==known for i in matches):
        # GitHub list endpoints may lag creation. Resolve the successful POST
        # receipt directly instead of creating another incident from a stale list.
        issue=client.request('GET',f'/issues/{known}')
        if issue.get('state')=='open' and issue.get('title')==title and marker in (issue.get('body') or ''):
            matches.append(issue)
    if errors:
        if matches: return {'status':'ALREADY_OPEN','url':matches[0]['html_url']}
        # Only bounded errors, never environment dumps or full tracebacks.
        safe=[]
        for error in errors:
            text=str(error)
            for env_name,value in os.environ.items():
                if value and len(value)>5 and any(x in env_name for x in ('TOKEN','SECRET','API_KEY','PASSWORD')):
                    text=text.replace(value,'[REDACTED]')
            safe.append(text[:500])
        run=os.getenv('GITHUB_RUN_ID','local')
        body=marker+'\n'+('**Synthetic acceptance test; no production incident.**\n' if test else '')
        body+='\n'+'\n'.join('- '+e for e in safe)
        body+=f'\n\n[Workflow evidence](https://github.com/{client.repo}/actions/runs/{run})\n'
        issue=client.request('POST','/issues',{'title':title,'body':body,'assignees':[client.repo.split('/')[0]]})
        client.receipt(key,issue['number'])
        return {'status':'CREATED','url':issue['html_url']}
    closed=[]
    for issue in matches:
        client.request('PATCH',f"/issues/{issue['number']}",{'state':'closed','state_reason':'completed'})
        closed.append(issue['html_url'])
    return {'status':'RECOVERED' if closed else 'NO_INCIDENT','urls':closed}


def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--pipeline',action='store_true'); args=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    if args.pipeline:
        outcome=os.getenv('PIPELINE_JOB_STATUS','unknown')
        errors=[] if outcome=='success' else ['Daily workflow did not complete successfully: '+outcome]
        result=notify('pipeline',errors)
    else:
        try:
            record=json.loads((root/'runs/watchdog/latest.json').read_text(encoding='utf-8'))
            errors=list(record['errors'])
        except (OSError,ValueError,KeyError): errors=['Watchdog evidence unavailable']
        outcome=os.getenv('WATCHDOG_OUTCOME','success')
        if outcome!='success': errors.append('Watchdog check did not complete successfully: '+outcome)
        result=notify('watchdog',errors)
    print(json.dumps(result))


if __name__=='__main__': main()
