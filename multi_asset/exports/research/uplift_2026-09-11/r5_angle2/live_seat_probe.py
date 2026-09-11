"""READ-ONLY probe of the LIVE seat. Reads ~/wide_shadow/state/leg_returns_live.json and recomputes
w3 with the live rule VERBATIM (shadow_loop_v3.py L455-461 = fea171/combo_stage.py L30-36), then the
rev24 mask + renormalisation (combo_stage.py L228-229). Writes nothing to the live tree."""
import json, numpy as np
LR=json.load(open("/Users/haosiyu/wide_shadow/state/leg_returns_live.json"))
look=900; n=len(LR["king"]); out=[]
for end in range(look,n+1):
    r=np.stack([np.array(LR[k][end-look:end],float) for k in ("king","rev24","fund")])
    s=np.maximum(r.mean(1)/(r.std(1)+1e-9),0.0)
    w=s/s.sum() if s.sum()>0 else np.array([1/3]*3)
    wm=np.array([w[0],0.0,w[2]]); wm=wm/wm.sum() if wm.sum()>1e-12 else np.array([.5,0,.5])
    out.append(wm)
out=np.array(out)
res={"n_leg_return_rows":n,"n_recomputable_anchors":len(out),
     "w3_3leg_latest":[round(float(x),4) for x in (lambda s: s/s.sum())(np.maximum(np.stack([np.array(LR[k][-look:],float) for k in ("king","rev24","fund")]).mean(1)/(np.stack([np.array(LR[k][-look:],float) for k in ("king","rev24","fund")]).std(1)+1e-9),0.0))],
     "w3_masked_latest":[round(float(x),4) for x in out[-1]],
     "masked_king_min":round(float(out[:,0].min()),4),"masked_king_max":round(float(out[:,0].max()),4),
     "masked_king_median":round(float(np.median(out[:,0])),4),
     "frac_anchors_masked_king_le_0.21":round(float((out[:,0]<=0.21).mean()),4)}
print(json.dumps(res,indent=1))
open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r5_angle2/LIVE_SEAT_PROBE.json","w").write(json.dumps(res,indent=1))
