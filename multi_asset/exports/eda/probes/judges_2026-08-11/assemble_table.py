"""Assemble the honest cross-regime trajectory table (cd-CLEAN caliber).
run1 = all 10 months; run2 = 6 ran (4 held); lora = drift Run2-state arm.
Router pick per the FROZEN pre-committed tt-sign map. OOS = 7 unseen months."""
# cd-CLEAN from chain_status DONE lines (+ d1_2026_01_run1 from statusline: WAIT_DONE, =0.0175)
run1 = {"2025_08":0.0798,"2025_09":0.0493,"2025_10":0.1025,"2025_11":0.0485,"2025_12":0.0575,
        "2026_01":0.0175,"2026_02":0.0178,"2026_03":0.0281,"2026_04":0.0417,"2026_05":0.0540}
run2 = {"2025_08":0.0519,"2025_09":0.0576,"2025_10":0.0753,"2025_11":0.0390,
        "2026_01":0.0121,"2026_04":0.0715}   # 2025_12/2026_02/2026_03/2026_05 HELD (never ran)
lora = {"2025_10":0.0574,"2026_01":0.0211,"2026_05":0.0586}   # Run2-state drift arm
# FROZEN routing map (tt-sign): Run1 unless listed. 2026_04->Run2, 2026_05->Run2-state(lora)
router_pick = {m:"run1" for m in run1}
router_pick["2026_04"]="run2"; router_pick["2026_05"]="lora"
INSAMPLE = {"2025_10","2026_01","2026_04"}
OOS = [m for m in run1 if m not in INSAMPLE]

def pick_val(m):
    p = router_pick[m]
    return {"run1":run1,"run2":run2,"lora":lora}[p].get(m, run1[m])

print(f"{'month':9} {'run1':>7} {'run2':>7} {'lora':>7} {'router':>8} {'oracle':>7}  seg")
for m in run1:
    r2 = run2.get(m); lo = lora.get(m)
    orac = max([v for v in [run1[m], r2] if v is not None])
    seg = "in-sample" if m in INSAMPLE else "OOS"
    rv = pick_val(m); rp = router_pick[m]
    print(f"{m:9} {run1[m]:>7.4f} {(('%.4f'%r2) if r2 is not None else '  held'):>7} "
          f"{(('%.4f'%lo) if lo is not None else '   -'):>7} {rv:>7.4f}[{rp[:3]}] {orac:>7.4f}  {seg}")

def mean(d, keys):
    vs=[d[k] for k in keys if k in d]; return sum(vs)/len(vs), len(vs)

print("\n--- MEANS (cd-CLEAN) ---")
a1_all,_ = mean(run1, run1.keys()); print(f"always-Run1  ALL-10 = {a1_all:+.4f}")
a1_oos,_ = mean(run1, OOS);         print(f"always-Run1  OOS-7  = {a1_oos:+.4f}")
rt_oos = sum(pick_val(m) for m in OOS)/len(OOS); print(f"router       OOS-7  = {rt_oos:+.4f}   Δ vs always-Run1 = {rt_oos-a1_oos:+.4f}")
r2_avail,n2 = mean(run2, run2.keys()); print(f"always-Run2  (only {n2} ran) = {r2_avail:+.4f}   [4 months HELD -> incomplete]")
# oracle over months where both run1+run2 exist
both = [m for m in run1 if m in run2]
orac_both = sum(max(run1[m],run2[m]) for m in both)/len(both)
print(f"oracle(run1|run2) over {len(both)} both-ran = {orac_both:+.4f}")
print(f"\nOOS months: {OOS}")
print(f"router OOS picks: " + ", ".join(f'{m}:{router_pick[m][:3]}' for m in OOS))
