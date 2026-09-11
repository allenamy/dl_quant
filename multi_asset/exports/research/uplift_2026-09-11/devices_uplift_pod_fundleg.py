"""fund leg gross return per anchor, two panel lineages (ext vs holefix2).
xz/leg formula copied verbatim from pod_export_bundle_v3.py L84-L110."""
import numpy as np, time, json, csv, sys
from scipy.stats import rankdata
def xz(v):
    ok=np.isfinite(v); out=np.full(len(v),np.nan); n=ok.sum()
    if n>=10: out[ok]=rankdata(v[ok])/max(n-1,1)-0.5
    return out
def run(panel, meta, tag):
    P=np.load(panel,allow_pickle=True); M=np.load(meta,allow_pickle=True)
    pts=P["ts"].astype(np.int64); FE=P["f_fund_ema_v1"]; R24=P["f_rev_24h"]; FN=P["f_fund_now"]
    row={int(t):j for j,t in enumerate(pts)}
    E_ts=M["E_ts"].astype(np.int64); members=M["members"]; y4=M["y4"]
    out=[]
    for i in range(len(E_ts)):
        j=row.get(int(E_ts[i]))
        if j is None: continue
        m=members[i]; ok=np.isfinite(y4[i,m])
        if ok.sum()<50: continue
        r={}
        for leg,sc in (("fund",FE[j,m]),("rev24",-R24[j,m])):
            z=np.nan_to_num(xz(sc)); z=np.where(ok,z,0.0); z-=z[ok].mean()
            g=np.abs(z).sum()
            r[leg]=float((z/g*np.nan_to_num(y4[i,m],nan=0.0)).sum()*1e4) if g>1e-9 else 0.0
        fe=FE[j,m][np.isfinite(FE[j,m])]
        out.append(dict(ts=int(E_ts[i]),fund=r["fund"],rev24=r["rev24"],n=int(ok.sum()),
                        fundema_sd=float(fe.std()) if fe.size else np.nan))
    with open(f"/workspace/codex_research/uplift_fundleg_{tag}.csv","w",newline="") as f:
        w=csv.DictWriter(f,list(out[0].keys())); w.writeheader(); w.writerows(out)
    print(tag,"anchors",len(out))
run("/workspace/data/wide_panel_4h_v2ext.npz","/workspace/data/wide_fea_v2ext_meta.npz","ext")
run("/workspace/data/wide_panel_4h_v2holefix.npz","/workspace/data/wide_fea_v4_meta.npz","holefix2")
run("/workspace/data/wide_panel_4h_v3splice.npz","/workspace/data/wide_fea_v2ext_meta.npz","v3splice")
