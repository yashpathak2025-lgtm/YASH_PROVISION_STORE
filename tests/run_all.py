import subprocess,sys
cmd=[sys.executable,'-m','pytest','-q','tests/test_contract.py','tests/test_e2e.py']
raise SystemExit(subprocess.call(cmd))
