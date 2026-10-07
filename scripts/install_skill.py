"""Install without overwriting existing personal skills."""
import os
from pathlib import Path
import shutil

source = Path(__file__).resolve().parents[1] / 'skills/road-disease-memory'
target = Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex'))) / 'skills' / source.name
if target.exists():
    raise SystemExit(f'Already exists; compare and back up before updating: {target}')
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
print(f'Installed: {target}')
