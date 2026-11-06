#!/usr/bin/env python3
from pathlib import Path
import runpy
source=Path(__file__).resolve().parent/'primary-review'/'verify_primary.py'
text=source.read_text(encoding='utf-8')
old='HERE = Path(__file__).resolve().parent\nINPUT = (HERE.parent / "romarrng-pr70-w445-464-candidate-free-20261103" / "input").resolve()'
new='HERE = Path(__file__).resolve().parent / "primary-review"\nINPUT = (Path(__file__).resolve().parent / "candidate-free-input").resolve()'
if old not in text:
    raise SystemExit('primary verifier path constants not found')
path=Path(__file__).resolve().parent/'primary-review-portable-runtime.py'
path.write_text(text.replace(old,new,1),encoding='utf-8')
runpy.run_path(str(path),run_name='__main__')
path.unlink()
