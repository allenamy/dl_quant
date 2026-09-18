"""P-B summary: per-anchor deviation curve for one or more preplay runs (current-code vs timeline-pinned), phases split at the production interventions."""
import json, sys, numpy as np
def load(p):
    out=[]
    for l in open(p):
        r=json.loads(l); k=r.get("king_vs_archive") or {}; c=r.get("combo_vs_archive") or {}
        if not isinstance(c, dict): c={}
        out.append(dict(ts=r["anchor_ts"], utc=r["utc"], kl1=k.get("l1_rel", np.nan), kmax=k.get("max_abs_dw", np.nan), kn=k.get("n_diff_gt_1e-6", -1), cl1=c.get("l1_rel", np.nan), cmax=c.get("max_abs_dw", np.nan), w3=r.get("w3_max_abs_diff", np.nan), sd=r.get("members_symdiff_vs_archive"), ver={k2: (v[-28:] if isinstance(v, str) else v) for k2, v in (r.get("versions") or {}).items()}, crc=r.get("combo_rc")))
    return out
runs={n: load(p) for n, p in (a.split("=") for a in sys.argv[1:])}
CUTS=[(1788696000, "09-02 12Z FTRIM"), (1788840000, "09-04 04Z M1"), (1788624000, "09-05 16Z seed"), (1789646400, "09-17 12Z 3520d363")]
for n, rs in runs.items():
    print("==", n, "n", len(rs))
    for r in rs:
        print(f"{r['utc']:10s} king L1 {r['kl1']:.4f} max {r['kmax']:.4f} n> {r['kn']:4d}  combo L1 {r['cl1']:.4f} max {r['cmax']:.4f} rc {r['crc']}  w3 {r['w3']:.4f} sd {r['sd']}  {r['ver']}")
    ts=np.array([r["ts"] for r in rs]); kl=np.array([r["kl1"] for r in rs], float); cl=np.array([r["cl1"] for r in rs], float)
    edges=sorted(set([int(ts.min())] + [c for c, _ in CUTS if ts.min() < c <= ts.max()] + [int(ts.max()) + 1]))
    for a, b in zip(edges[:-1], edges[1:]):
        m=(ts >= a) & (ts < b)
        if m.sum(): print(f"  phase [{a}..{b}) n={m.sum()} king L1 mean {np.nanmean(kl[m]):.4f} med {np.nanmedian(kl[m]):.4f} max {np.nanmax(kl[m]):.4f} | combo L1 mean {np.nanmean(cl[m]):.4f} med {np.nanmedian(cl[m]):.4f} max {np.nanmax(cl[m]):.4f}")
