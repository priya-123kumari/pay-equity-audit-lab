"""Fallback runner if pytest is unavailable:  python tests/run_without_pytest.py"""
import os, sys, time, traceback
here = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [here, os.path.dirname(here)]
import test_pipeline as t
fails = 0
for name in sorted(n for n in dir(t) if n.startswith("test_")):
    s = time.time()
    try:
        getattr(t, name)(); print(f"PASS {name} ({time.time()-s:.1f}s)")
    except Exception:
        fails += 1; print(f"FAIL {name}"); traceback.print_exc()
print(f"\n{'ALL PASSED' if not fails else str(fails) + ' FAILED'}")
sys.exit(1 if fails else 0)
