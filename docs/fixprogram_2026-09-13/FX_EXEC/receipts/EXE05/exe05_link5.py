import json, re, collections
P = "/Users/haosiyu/cc_tmp/fx_exec_census_exe05/anchor_runs.log"
rows = []
for line in open(P, encoding="utf-8", errors="replace"):
    m = re.search(r'phase_A: (\{.*\})\s*$', line.rstrip("\n"))
    if not m:
        continue
    try:
        d = json.loads(m.group(1))
    except ValueError:
        continue
    s = d.get("sizing")
    if not isinstance(s, dict):
        continue
    rows.append({"ts": d.get("anchor_ts"), "rid": d.get("rebalance_id"), "sizing": s,
                 "universe": d.get("universe"), "raw_mode": d.get("mode"),
                 "n_live": d.get("n_live")})
print("phase_A rows with a sizing block:", len(rows))
sz = [r["sizing"] for r in rows]
print("gross_previous == 0.0 :", sum(1 for s in sz if s.get("gross_previous") == 0.0), "/", len(sz))
print("actual_leverage is null:", sum(1 for s in sz if s.get("actual_leverage") is None), "/", len(sz))
print("resized is True       :", sum(1 for s in sz if s.get("resized") is True), "/", len(sz))
print("blind is True         :", sum(1 for s in sz if s.get("blind") is True), "/", len(sz))
print("deadzone_frac values  :", dict(collections.Counter(s.get("deadzone_frac") for s in sz)))
print("leverage_drift_frac non-null:", sum(1 for s in sz if s.get("leverage_drift_frac") is not None))
# LIVE = non-blind, nav present (DRY_RUN rows carry nav null / universe skipped)
live = [r for r in rows if r["sizing"].get("nav") and r["sizing"].get("blind") is not True]
print("\nrows with a real nav (the LIVE-sized ones):", len(live))
ok = bad = 0
for r in live:
    s = r["sizing"]
    want = round(float(s["nav"]) * float(s["target_leverage"]), 2)
    if abs(float(s["gross"]) - want) <= 0.005:
        ok += 1
    else:
        bad += 1
        if bad <= 5:
            print("   EXCEPTION", r["rid"], "gross", s["gross"], "nav*tgt", want)
print(f"gross == round(nav * target_leverage, 2): {ok}/{ok+bad}  exceptions={bad}")
