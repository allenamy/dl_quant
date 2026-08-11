import json, os
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
CFG = f"{MA}/configs/d1gate"
print("=== Branch A: 2026-02 / 2026-03 run1 fold spans ===")
for m in ["2026_02", "2026_03"]:
    f = f"{CFG}/d1_{m}_run1.json"
    if not os.path.exists(f):
        print(f"  {m}: config MISSING"); continue
    d = json.load(open(f)); t = d["training"]
    print(f"  {m}: test_starts={t['fold_test_starts']} train={t['train_days']} val={t['val_days']} test={t['test_days']} embargo={t.get('embargo_days')}")

# augms span
ad = f"{MA}/data/npz_v2arch_augms"
days = sorted(x[:-4] for x in os.listdir(ad) if x.endswith(".npz") and x[0].isdigit())
print(f"=== augms span: {days[0]} .. {days[-1]} (n={len(days)}) ===")

# fold-day requirement for 2026-02/03 (positional on v2arch full day list)
V2 = f"{MA}/data/npz_v2arch"
v2days = sorted(x[:-4] for x in os.listdir(V2) if x.endswith(".npz") and x[0].isdigit())
def fold_days(daylist, ts, TR=450, VA=45, TE=28, EMB=1):
    if ts not in daylist: return None
    ti = daylist.index(ts); test = daylist[ti:ti+TE]
    ve = ti-EMB; vs = ve-VA; val = daylist[vs:ve]
    te = vs-EMB; trs = max(0, te-TR); train = daylist[trs:te]
    return train[0], test[-1]
for m, ts in [("2026_02", None), ("2026_03", None)]:
    cfg = json.load(open(f"{CFG}/d1_{m}_run1.json"))
    ts = cfg["training"]["fold_test_starts"][0]
    span = fold_days(v2days, ts)
    if span:
        need_lo, need_hi = span
        have = (need_lo >= days[0] and need_hi <= days[-1])
        print(f"  {m} fold needs {need_lo} .. {need_hi}  | augms covers? {have}  (extend to {need_hi} if not)")

print("=== Branch B: wf450_backext configs ===")
bd = f"{MA}/configs/wf450_backext"
if os.path.isdir(bd):
    for x in sorted(os.listdir(bd)):
        print("   ", x)
