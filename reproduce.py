"""Standalone entry point for the released experiments."""
import sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
stage=sys.argv[1] if len(sys.argv)>1 else 'check'
if stage=='check':
 scripts=[['check.py'],['check_dominance.py']]
elif stage in ['primary','scale','additional']:
 scripts=[['final_bench.py',stage]]
elif stage=='quality':scripts=[['quality.py']]
elif stage=='baselines':scripts=[['baselines.py']]
else:raise SystemExit('Choose check, primary, scale, additional, quality, or baselines')
for args in scripts:subprocess.run([sys.executable,str(ROOT/'src'/args[0]),*args[1:]],check=True)
