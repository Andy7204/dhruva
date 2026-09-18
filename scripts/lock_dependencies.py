"""Record the installed runtime dependency closure for Linux deployment."""
from importlib.metadata import distribution
from pathlib import Path
from packaging.markers import default_environment
from packaging.requirements import Requirement

root = Path(__file__).resolve().parents[1]
environment = default_environment()
environment.update(sys_platform='linux', platform_system='Linux', os_name='posix', extra='')
pending = ['pandas', 'numpy', 'streamlit', 'tzdata']
seen = {}
while pending:
    name = pending.pop().lower().replace('_', '-')
    if name in seen: continue
    dist = distribution(name)
    seen[name] = dist.version
    for text in dist.requires or []:
        req = Requirement(text)
        if req.marker is None or req.marker.evaluate(environment):
            pending.append(req.name)
lines = ['# Deployment dependency closure, Python 3.12 / Linux; requires clean CI verification.',
         '# Generated from installed distributions; changes require tests and review.']
lines += [f'{name}=={version}' for name, version in sorted(seen.items())]
(root/'requirements.lock').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(f'Pinned {len(seen)} distributions.')
