"""What did the PRE-FIX code actually do?  Measure, do not assert from memory."""
import importlib.util, os, sys, json, traceback
REPO = "/Users/haosiyu/dl_quant_live"
sys.path[:0] = [os.path.join(REPO, "ops"), os.path.join(REPO, "live"), os.path.join(REPO, "scheduler")]
P = os.path.join(REPO, "ops", "check_factor_health.py")
SRC = open(P).read()

FIND = ('                "findings": ["UNREACHABLE: the shadow monitor report could not be read at all. "\n'
        '                             "Factor health is UNKNOWN — which is not the same as healthy, and is "\n'
        '                             "the one state in this file that cannot be inferred from anything "\n'
        '                             "else."],\n')
print("find-string occurrences:", SRC.count(FIND))
assert SRC.count(FIND) == 1

spec = importlib.util.spec_from_file_location("_prefix_cfh", P)
mod = importlib.util.module_from_spec(spec); sys.modules["_prefix_cfh"] = mod
exec(compile(SRC.replace(FIND, ""), P, "exec"), mod.__dict__)

res = mod.evaluate(None, now=1.0)
print("pre-fix evaluate(None) keys:", sorted(res))
print("  has findings?", "findings" in res)

class Notifier:
    def __init__(self): self.calls = []
    def alarm(self, sev, msg):
        self.calls.append((sev, msg)); return {"status": "SENT", "delivered_offbox": True}

# make fetch() return None (unreachable report) without touching disk
mod.fetch = lambda: None
n = Notifier(); logs = []
try:
    mod.run(notifier=n, log=logs.append)
    print("run() RETURNED normally ->", res.get("ok"))
except Exception as e:
    print("run() RAISED:", type(e).__name__, e)
    # what run_anchor does with it
    print("  run_anchor would then alarm:", ("HIGH", f"因子健康检查本轮无法运行 ({e}) — 衰减与新鲜度本轮无人监视。"))
print("notifier calls inside run():", n.calls)
print("logs:", logs)
print("state file written?", os.path.exists(mod.LAST))
