"""READ-ONLY: what cond2 will do at/after the 12Z row on 2026-09-08 (deposit day, TRANSFER +35,007.38).
Adapted verbatim in method from pilot_journal/tools/resume_gate_flowday_probe.py. Production tree never written."""
import json, os, shutil, sys, tempfile
REPO="/Users/haosiyu/dl_quant_live"; sys.path.insert(0, os.path.join(REPO,"live")); os.chdir(REPO)
import watchdog as WD, watchdog_inputs as WI
SRC=os.path.join(REPO,"state/live/pilot_log")
FLOW=35007.37995552; NAV_NOW=117177.78

def build(add_row, nav=None, flow=None):
    tree=tempfile.mkdtemp(prefix="flow0908_"); shutil.rmtree(tree); shutil.copytree(SRC,tree)
    if add_row:
        rows=[json.loads(l) for l in open(os.path.join(SRC,"20260908/daily_nav.jsonl")) if l.strip()]
        last=rows[-1]; r=dict(last)
        r.update({"nav":nav,"wallet_balance":nav,"margin_balance":nav,
                  "external_flow_usdt":flow,"equity_delta_since_prev":nav-float(last["prev_nav"]),
                  "nav_ts":float(last["nav_ts"])+14400.0})
        with open(os.path.join(tree,"20260908/daily_nav.jsonl"),"a") as f: f.write(json.dumps(r)+"\n")
    return tree

def run(label,tree):
    ops,ve,_=WI.collect(tree)
    ev,_,_=WD.run(tree,broker=WD.MockBroker(),venue_events=ve,ops_stats=ops,verbose=False,state_dir=tempfile.mkdtemp())
    c2={}
    for k in ("detail","details","conditions"):
        d=ev.get(k) or {}
        if isinstance(d,dict) and "cond2_day_loss" in d: c2=d["cond2_day_loss"]; break
    print("%-46s tripped=%-5s blind=%s partial=%s"%(label,ev.get("tripped"),ev.get("conditions_blind"),ev.get("conditions_partial")))
    print("   cond2 keys: %s"%sorted(c2.keys()))
    for k in ("recent_day","recent_day_pct","triggered","n_priced_days","n_days","limit_pct","alert_pct"):
        if k in c2: print("   cond2.%-16s %s"%(k,c2[k]))
    if ev.get("triggers"): print("   TRIGGERS %s"%ev["triggers"])
    print()
    return ev,c2

print("=== A  production tree as-is (no 12Z row yet) ===");        run("A as-is", build(False))
print("=== B  + 12Z row: NAV %.0f, external_flow +%.2f  (what 12Z will write) ==="%(NAV_NOW,FLOW))
run("B deposit row", build(True,NAV_NOW,FLOW))
print("=== C  STRESS: same as B but book then loses 6%% intraday (NAV %.0f, flow still set) ==="%(NAV_NOW*0.94))
run("C deposit row + -6% day", build(True,NAV_NOW*0.94,FLOW))
print("=== D  CONTROL: 12Z row with NO transfer and -6% day (proves the stop is otherwise live) ===")
run("D no-flow -6% day", build(True,82719.86*0.94,0.0))
