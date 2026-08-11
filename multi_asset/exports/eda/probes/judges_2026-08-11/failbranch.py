FAILS = ["injected_failure_A", "injected_failure_B"]
print(f"\n{'ALL PASS' if not (FAILS if 'FAILS' in dir() else fails) else 'FAILURES: ' + str(FAILS if 'FAILS' in dir() else fails)}")
import sys
sys.exit(0 if not FAILS else 1)
