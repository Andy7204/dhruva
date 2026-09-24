from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from dhruva.publication import publish


class PublicationTests(unittest.TestCase):
    def test_concurrent_code_preserved_but_concurrent_book_rejected(self):
        def git(root,*args):
            return subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,check=True).stdout.strip()
        for conflict in (False,True):
            with self.subTest(conflict=conflict), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp); remote=root/'remote'; remote.mkdir(); git(remote,'init','--bare','-b','main')
                a=root/'a'; git(root,'clone',str(remote),str(a))
                for repo in [a]:
                    git(repo,'config','user.name','Test'); git(repo,'config','user.email','test@example.invalid')
                (a/'runs').mkdir(); (a/'data/cache').mkdir(parents=True); (a/'reports').mkdir()
                for file in ['runs/book.json','data/cache/test.csv','reports/dashboard.html']:
                    (a/file).write_text('initial')
                git(a,'add','.'); git(a,'commit','-m','initial'); git(a,'push','origin','main')
                b=root/'b'; git(root,'clone',str(remote),str(b))
                git(b,'config','user.name','Test'); git(b,'config','user.email','test@example.invalid')
                (b/('runs/book.json' if conflict else 'code.py')).write_text('concurrent')
                git(b,'add','.'); git(b,'commit','-m','concurrent'); git(b,'push','origin','main')
                (a/'runs/book.json').write_text('new evidence')
                with patch('dhruva.publication.time.sleep'):
                    if conflict:
                        with self.assertRaisesRegex(RuntimeError,'Concurrent generated state'): publish(a)
                    else:
                        self.assertEqual(publish(a),'PUBLISHED')
                        self.assertEqual((a/'code.py').read_text(),'concurrent')
                        self.assertEqual((a/'runs/book.json').read_text(),'new evidence')


if __name__=='__main__': unittest.main()
