import json,os
from collections import defaultdict
LOG="/Users/haosiyu/dl_quant_live/state/live/pilot_log"; COMBO=1787716800.0
days=sorted(d for d in os.listdir(LOG) if d.isdigit())
anch={}
for d in days:
    p=f"{LOG}/{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); ts=r.get("anchor_ts")
        if ts is None: continue
        m=r.get("mid_at_anchor_vector")
        if isinstance(m,str): m=json.loads(m)
        anch[ts]=m or {}
ats=sorted(anch)
bnbc=[t for t in ats if anch[t].get("BNBUSDT")]
print("anchors.jsonl rows:",len(ats),"  with BNBUSDT mid:",len(bnbc))
F={}
for d in days:
    p=f"{LOG}/{d}/fills.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        r=json.loads(ln); k=(r["symbol"],r["trade_id"]); c=F.get(k)
        if c is None: F[k]=r; continue
        if r.get("mid_at_fill_plus_60s") is not None and c.get("mid_at_fill_plus_60s") is None: F[k]=r
fts=set(r.get("anchor_ts") for r in F.values() if r.get("anchor_ts") is not None and r["anchor_ts"]>=COMBO)
miss=[t for t in fts if t not in anch]
print("combo-era fill anchor_ts:",len(fts)," NOT present as a key in anchors.jsonl:",len(miss))
# how much BNB commission sits on those anchors
bn_miss=0.;bn_all=0.;nz_miss=0.;nz_all=0.
for r in F.values():
    ts=r.get("anchor_ts")
    if ts is None or ts<COMBO: continue
    n=abs(float(r.get("fill_notional") or 0)); nz_all+=n
    if ts in miss: nz_miss+=n
    if (r.get("commission_asset") or "USDT")=="BNB":
        c=float(r.get("commission") or 0); bn_all+=c
        if ts in miss: bn_miss+=c
print(f"combo-era BNB commission total {bn_all:.6f} BNB; on anchors missing from anchors.jsonl {bn_miss:.6f} BNB ({bn_miss/bn_all*100:.1f}%)")
print(f"combo-era traded notional total {nz_all:,.0f}; on missing anchors {nz_miss:,.0f} ({nz_miss/nz_all*100:.1f}%)")
# what BNB price would reconcile 2.3992 vs my 2.8853?
