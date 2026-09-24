"""Publish generated evidence without overwriting concurrent state commits."""
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
PATHS=['runs/','reports/dashboard.html','data/cache/']


def publish(root=ROOT):
    def git(*args,check=True):
        return subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,check=check)
    base=git('rev-parse','HEAD').stdout.strip()
    git('add','--',*PATHS)
    if git('diff','--cached','--quiet',check=False).returncode==0:
        return 'NO_CHANGES'
    git('commit','-m','Refresh daily paper books and dashboard')
    for attempt in range(3):
        if git('push','origin','HEAD:main',check=False).returncode==0: return 'PUBLISHED'
        git('fetch','origin','main')
        # Only code/docs may have changed remotely while data was being fetched.
        # Any concurrent generated-state writer must be resolved explicitly.
        if git('diff','--quiet',base,'origin/main','--',*PATHS,check=False).returncode:
            raise RuntimeError('Concurrent generated state changed; refusing to overwrite. Recover uploaded evidence.')
        git('rebase','origin/main')
        base=git('rev-parse','origin/main').stdout.strip()
        time.sleep(1)
    raise RuntimeError('Generated publication failed after three attempts; recover uploaded evidence')


if __name__=='__main__': print(publish())
