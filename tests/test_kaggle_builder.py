#!/usr/bin/env python3
"""Offline regression for Kaggle build & Tensor-vs-BatchEncoding GPU failure."""
import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
template = (ROOT / "kaggle/sourcecheck_template.py").read_text(encoding="utf-8")
assert 'return_dict=True' in template
assert 'enc["input_ids"]' in template
assert 'model.generate(**generate_kwargs)' in template
assert 'model.generate(inputs,' not in template
# Builder embeds JSON repr inside a Python expression; generated script must parse.
p = subprocess.run([sys.executable, "tools/build_kaggle_job.py", "--ids", "P01"],
                   cwd=ROOT, capture_output=True, text=True)
assert p.returncode == 0, p.stderr
output = ROOT / "kaggle/sourcecheck/sourcecheck_kaggle.py"
assert output.exists()
ast.parse(output.read_text(encoding="utf-8"))
meta = json.loads((ROOT / "kaggle/sourcecheck/kernel-metadata.json").read_text(encoding="utf-8"))
assert meta["is_private"] and meta["enable_gpu"]
print("Kaggle offline build/generation regression: PASS")
