"""(a) pod panel f_fund_now/f_fund_iv (pod_panel_ext.py L152-159) vs producer ledger last-settled rate at the same anchors (empirical definition check);
(b) replay carry_ex recomputed from its own W x panel rates (bitwise-ish) and x ledger rates;
(c) 2x2: {replay W, live target w} x {panel rates, ledger rates} on the common anchors -> weights-vs-rates attribution of the replay-vs-live carry gap."""
import json, numpy as np, time
G="/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber/gap_1"
WS="/Users/haosiyu/wide_shadow"
def f(t): return time.strftime("%m-%d %HZ", time.gmtime(int(t)))
P=np.load(f"{G}/panel_fund_tail.npz", allow_pickle=True); pts=P["ts"].astype(np.int64); psym=[str(s) for s in P["symbols"]]; FN=P["f_fund_now"].astype(np.float64); IV=P["f_fund_iv"].astype(np.float64); prow={int(t):i for i,t in enumerate(pts)}
cfg=json.load(open(f"{WS}/shadow_bundle/config.json")); bsym=cfg["symbols_panel"]; assert bsym==psym, "symbol order differs between pod panel and live bundle"
LT=json.load(open(f"{WS}/state/aux.json"))["ledger_tail"]
def r_last(s,N):
    led=LT.get(s)
    if not led: return None
    best=None
    for ft,r,iv in led:
        if ft<=N: best=(ft,r,iv)
        else: break
    if best is None or N-best[0]>12*3600: return None
    return best
R=json.load(open(f"{G}/replay_tail_rows.json"))
# (a) panel vs ledger on anchors 08-26 00Z .. 08-31 00Z, symbols with a ledger
anch=[int(t) for t in pts if t>=1787702400]
n=neq=nan_p_only=nan_l_only=iv_neq=0; maxd=0.0; ex=[]
for N in anch:
    i=prow[N]
    for j,s in enumerate(psym):
        rl=r_last(s,N); pv=FN[i,j]; piv=IV[i,j]
        if rl is None and not np.isfinite(pv): continue
        if rl is None: nan_l_only+=1; continue
        if not np.isfinite(pv): nan_p_only+=1; continue
        n+=1; d=abs(pv-rl[1]); maxd=max(maxd,d)
        if d>1e-9: neq+=1; ex.append((f(N),s,pv,rl[1],rl[0]-N)) if len(ex)<5 else None
        if np.isfinite(piv) and piv!=rl[2]: iv_neq+=1
print(f"(a) panel f_fund_now vs ledger last-settled<=N on {len(anch)} anchors {f(anch[0])}->{f(anch[-1])}: compared {n}, |diff|>1e-9: {neq} (max {maxd:.2e}; float32 rounding ~1e-9), iv unequal {iv_neq}, panel-NaN-but-ledger-has {nan_p_only}, ledger-None-but-panel-has {nan_l_only}")
for e in ex: print("   e.g.", e)
# (b)+(c)
for tag in ("pod_live_w3fix_callog_s42","pod_live_callog_s42"):
    cols=R[tag]["cols"]; rows=np.array(R[tag]["rows"]); W=np.array(R[tag]["W"]); wts=[int(t) for t in R[tag]["W_ts"]]
    ic=cols.index("carry_ex"); it=cols.index("ts"); ig=cols.index("gross_total")
    import os
    common=[N for N in wts if N>=1787716800 and N in prow and os.path.exists(f"{WS}/state/target_live/{N}.json")]
    rec=[]
    for N in common:
        k=wts.index(N); i=prow[N]; w=W[k]
        sm_r=w-w[np.abs(w)>1e-12].mean() if (np.abs(w)>1e-12).any() else w   # device carry_ex uses smr (demeaned, rescaled to same gross): line 305
        nz=np.abs(w)>1e-12; smr=w.copy(); smr[nz]-=smr[nz].mean(); g0=np.abs(w).sum(); g1=np.abs(smr).sum(); smr*= g0/g1 if g1>1e-9 else 1
        fn=np.nan_to_num(FN[i]); ivv=np.where(np.isfinite(IV[i])&(IV[i]>0),IV[i],8.0)
        rep_panel=float((smr*fn*(4.0/ivv)).sum()*1e4)
        lr=np.zeros(len(psym)); liv=np.full(len(psym),8.0)
        for j,s in enumerate(psym):
            rl=r_last(s,N)
            if rl: lr[j]=rl[1]; liv[j]=rl[2]
        rep_ledger=float((smr*lr*(4.0/liv)).sum()*1e4)
        stored=float(rows[list(rows[:,it].astype(np.int64)).index(N), ic]); gt=float(rows[list(rows[:,it].astype(np.int64)).index(N), ig])
        # live target weights at the same anchor
        tl=json.load(open(f"{WS}/state/target_live/{N}.json"))["weights"]; wl=np.zeros(len(psym))
        for s,v in tl.items():
            if s in psym: wl[psym.index(s)]=v
        gl=np.abs(wl).sum()
        live_panel=float((wl*fn*(4.0/ivv)).sum()*1e4); live_ledger=float((wl*lr*(4.0/liv)).sum()*1e4)
        rec.append((N,stored,rep_panel,rep_ledger,gt,live_panel,live_ledger,gl))
    a=np.array(rec)
    print(f"\n{tag}: {len(common)} common anchors {f(common[0])}->{f(common[-1])}")
    print(f"(b) stored carry_ex vs recompute W x panel: max|diff| {np.abs(a[:,1]-a[:,2]).max():.2e}; W x ledger vs W x panel: mean diff {(a[:,3]-a[:,2]).mean():+.4f} max|diff| {np.abs(a[:,3]-a[:,2]).max():.2e}")
    print(f"(c) 2x2 per-NAV bps/anchor (+ = book pays):  replayW x panel {a[:,2].mean():+.3f} | replayW x ledger {a[:,3].mean():+.3f} | liveW x panel {a[:,5].mean():+.3f} | liveW x ledger {a[:,6].mean():+.3f}")
    print(f"    per-gross (mean of ratio):               replayW x panel {(a[:,2]/a[:,4]).mean():+.3f} (gross {a[:,4].mean():.3f}) | liveW x ledger {(a[:,6]/a[:,7]).mean():+.3f} (gross {a[:,7].mean():.3f}); sd replay per-gross {(a[:,2]/a[:,4]).std(ddof=1):.3f}, sd live per-gross {(a[:,6]/a[:,7]).std(ddof=1):.3f}")
    d=(a[:,6]/a[:,7])-(a[:,2]/a[:,4]); print(f"    weights effect (liveW - replayW, same ledger rates, per gross): mean {d.mean():+.3f} sd {d.std(ddof=1):.3f} se {d.std(ddof=1)/np.sqrt(len(d)):.3f}  -> x21.9 = {d.mean()*21.9:+.1f} %/gross/yr")
# se for live - dev_real, live - settle_real from the 52-window rows
o=json.load(open(f"{G}/carry_reconcile_rows.json"))
for k in ("dev_real","settle_real","dev_target"):
    d=np.array([x["live_pays"]-x[k] for x in o]); print(f"52 windows: live_pays - {k}: mean {d.mean():+.3f} sd {d.std(ddof=1):.3f} se {d.std(ddof=1)/np.sqrt(len(d)):.3f} -> {d.mean()*21.9:+.1f} %/gross/yr")
