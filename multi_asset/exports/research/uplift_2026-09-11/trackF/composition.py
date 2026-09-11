"""Why 3.04 on the frozen window and 1.32 on full history: regime composition."""
import numpy as np, time
from judgeF import gseries, T, FROZEN
A=np.load('arms.npz'); B=np.load('tf.npz'); L=np.load('labels.npz')
lmap={int(t):int(l) for t,l in zip(L['ts'],L['lab'])}
NAMES={-1:'WARM',0:'LL',1:'LH',2:'HL',3:'HH'}
for nm,rec in (("A0",A['PARITY_A0_dyn_s42__rec']),("F1",B['TF_F1__rec'])):
    ts,g=gseries(rec); lb=np.array([lmap.get(int(t),-1) for t in ts])
    full=ts<=T(2026,8,10,20); froz=(ts>=FROZEN[0])&(ts<FROZEN[1]); post=(lb>=0)&full
    print(f"\n=== {nm} ===")
    print(f"{'cell':6s}{'share FULL':>12s}{'share FROZEN':>14s}{'mean g':>10s}{'Sharpe':>9s}{'n':>7s}")
    for l in (0,1,2,3):
        m=(lb==l)&full; v=g[m]
        print(f"{NAMES[l]:6s}{m.sum()/post.sum():12.3f}{((lb==l)&froz).sum()/froz.sum():14.3f}{v.mean():10.3f}{v.mean()/v.std(ddof=1)*np.sqrt(2190):9.2f}{int(m.sum()):7d}")
    # regime-matched expectation: per-cell mean/var, mixed at the FULL-history cell frequencies
    ws_full=np.array([((lb==l)&post).sum() for l in (0,1,2,3)],float); ws_full/=ws_full.sum()
    ws_fro=np.array([((lb==l)&froz).sum() for l in (0,1,2,3)],float); ws_fro/=ws_fro.sum()
    mu=np.array([g[(lb==l)&full].mean() for l in (0,1,2,3)])
    sd=np.array([g[(lb==l)&full].std(ddof=1) for l in (0,1,2,3)])
    for tag,w in (("FULL-history mix",ws_full),("FROZEN-window mix",ws_fro)):
        m_=float((w*mu).sum()); v_=float((w*(sd**2+mu**2)).sum()-m_**2)
        print(f"  expectation under {tag:20s}: mean {m_:6.3f}  Sharpe {m_/np.sqrt(v_)*np.sqrt(2190):5.2f}")
    print(f"  realised: FULL {g[full].mean():6.3f}/Sh {g[full].mean()/g[full].std(ddof=1)*np.sqrt(2190):5.2f}   FROZEN {g[froz].mean():6.3f}/Sh {g[froz].mean()/g[froz].std(ddof=1)*np.sqrt(2190):5.2f}")
