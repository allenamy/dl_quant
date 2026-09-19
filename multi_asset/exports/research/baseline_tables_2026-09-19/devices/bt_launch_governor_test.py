#!/usr/bin/env python3
"""bt_launch_governor_test.py — test of the bt_launch.py v3 governor (PSI halving, own-total cap, stop + re-queue) before the A0 main launch.
Three smoke launches of the SAME job set (run OBJB_A0|scaled|rule|raw|UAFE, seeds 0..3, N anchors from START) under the frozen A0 config:
  G0  baseline: the governor at its production constants (no --gov)
  G1  PSI trip forced: --gov -1,HOLD,100 (every poll is "above the limit") ⇒ max_parallel halves 4 → 2 → 1, running children are stopped by
      their recorded PID and re-queued; every seed must still finish rc 0 and its PATH npz must be BITWISE the G0 file
  G2  own-total cap forced: --gov 100,60,CAP (CAP below the parent's own Σ Pss) ⇒ no second child starts, max_parallel → 1, paths bitwise G0
Checks: each launch VERDICT=PASS exit 0; G0 has no governor event; G1 has ≥ 2 halvings and ≥ 1 stopped_and_requeued; G2 has an
own_total_over_cap event and never more than one child at a time (from the receipt's start/finish order in the log); npz shas equal G0 per seed.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B bt_launch_governor_test.py PATH,HOME,LC_CTYPE <config> START N HOLD CAP <out.json>
"""
import os, sys, json, time, subprocess, hashlib
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
CFG_P, START, N, HOLD, CAP, OUTP = sys.argv[2:8]
HERE = os.path.dirname(os.path.abspath(__file__)); CFG = json.load(open(CFG_P)); ROOT = CFG["paths"]["pod_root"]
RUN = "OBJB_A0|scaled|rule|raw|UAFE"; SEEDS = "0,1,2,3"; T0 = time.time(); RES = []
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def ok(n, c, d=None): RES.append(dict(check=n, ok=bool(c), detail=d)); print(("PASS " if c else "FAIL ") + n, json.dumps(d, default=str)[:240] if d is not None else "", flush=True)


def launch(label, gov=None):
    cmd = ["/workspace/venv/bin/python", "-B", os.path.join(HERE, "bt_launch.py"), "PATH,HOME,LC_CTYPE", CFG_P, "--smoke", START, N, SEEDS, RUN, label] + (["--gov", gov] if gov else [])
    lp = f"{ROOT}/logs/bt_launch_smoke_{label}.log"
    with open(lp, "w") as f:
        rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT, env={k: os.environ[k] for k in WL if k in os.environ})
    rec = json.load(open(f"{ROOT}/receipts/BT_LAUNCH_smoke_{label}.json")); log = open(lp).read().splitlines()
    d = f"{ROOT}/runs_smoke/{label}/{RUN.replace('|', '_')}"
    shas = {s: sha(f"{d}/PATH_{RUN.replace('|', '_')}_seed_{s:02d}.npz") for s in range(4)}
    return dict(rc=rc, rec=rec, log=log, shas=shas, cmd=cmd)


def max_concurrent(log):
    cur = mx = 0
    for l in log:
        if "] started " in l: cur += 1; mx = max(mx, cur)
        if "] finished " in l or "governor: stopped" in l: cur -= 1
    return mx


tag = time.strftime("%H%M%S", time.gmtime())
G0 = launch(f"gov0_{tag}"); G1 = launch(f"gov1_{tag}", f"-1,{HOLD},100"); G2 = launch(f"gov2_{tag}", f"100,60,{CAP}")
for nm, G in (("G0", G0), ("G1", G1), ("G2", G2)):
    ok(f"{nm}.launch_PASS_exit0", G["rc"] == 0 and G["rec"]["VERDICT"] == "PASS", dict(rc=G["rc"], verdict=G["rec"]["VERDICT"], failed=G["rec"].get("failed")))
ev = lambda G, a: [e for e in G["rec"]["governor"]["events"] if e["action"] == a]
ok("G0.no_governor_event_at_production_constants", G0["rec"]["governor"]["events"] == [] and G0["rec"]["governor"]["test_override"] is None, G0["rec"]["governor"])
ok("G0.ran_4_children_concurrently", max_concurrent(G0["log"]) == 4, max_concurrent(G0["log"]))
ok("G1.halved_at_least_twice", len(ev(G1, "halve_max_parallel")) >= 2, ev(G1, "halve_max_parallel"))
ok("G1.stopped_and_requeued_at_least_one_running_child", len(ev(G1, "stopped_and_requeued")) >= 1, ev(G1, "stopped_and_requeued"))
ok("G1.paths_bitwise_equal_G0", G1["shas"] == G0["shas"], dict(G0=G0["shas"], G1=G1["shas"]))
ok("G2.own_total_over_cap_event", len(ev(G2, "own_total_over_cap")) >= 1, ev(G2, "own_total_over_cap")[:2])
ok("G2.never_more_than_one_child", max_concurrent(G2["log"]) == 1, max_concurrent(G2["log"]))
ok("G2.paths_bitwise_equal_G0", G2["shas"] == G0["shas"], dict(G2=G2["shas"]))
fails = [r["check"] for r in RES if not r["ok"]]
out = dict(device="bt_launch_governor_test.py", self_sha256=sha(os.path.abspath(__file__)), launcher_sha256=sha(os.path.join(HERE, "bt_launch.py")), argv=sys.argv,
           config=dict(path=CFG_P, sha256=sha(CFG_P)), launches={nm: dict(cmd=G["cmd"], rc=G["rc"], governor=G["rec"]["governor"], shas=G["shas"], runtime_s=G["rec"]["runtime_s"],
           receipt_label=G["rec"]["smoke"]["label"]) for nm, G in (("G0", G0), ("G1", G1), ("G2", G2))}, checks=RES, failed=fails, VERDICT="PASS" if not fails else "RED",
           runtime_s=round(time.time() - T0, 1))
json.dump(out, open(OUTP, "w"), indent=1, default=str)
print("BT_LAUNCH_GOVERNOR_TEST VERDICT: " + ("ALL PASS %d/%d checks" % (len(RES), len(RES)) if not fails else "FAILURES %d/%d: %s" % (len(fails), len(RES), fails)), flush=True)
sys.exit(0 if not fails else 3)
