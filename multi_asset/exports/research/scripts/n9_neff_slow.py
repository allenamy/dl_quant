"""N9 —— 慢书的 N_eff: 决定"扩宇宙还有没有空间"。
N8 显示慢书的主导方向就是 alpha ⇒ "只收割 2.79 个"可能是【对的数字】而非缺陷。
若慢书 N_eff 仍 ≈3, 则收割能力确实是瓶颈, 扩宇宙受限; 若已升到 8+, 则平滑本身完成了去集中,
扩宇宙有空间。判读预写: N_eff^slow ≥ 6 ⇒ 扩宇宙有空间; < 4 ⇒ 瓶颈仍在收割侧。"""
import sys, json
MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import numpy as np
import torch; torch.backends.mkldnn.enabled = False
from engine import replay_fullhist as RF
from engine import signal_chain as SC
KING="/tmp/king_pred_newgen.npz"; S2="/tmp/s2_pred_newgen.npz"
LW={"king":.5952380952380952,"s2":.20238095238095238,"funding":.20238095238095238,"size":0.0}
WIN=120*24
z=np.load(f"{MA}/exports/wide_dl_full_corrfund_causal_0731.npz",allow_pickle=True)
Y4=z["Y4"].astype(np.float64);CL4=z["CL4"].astype(bool);MEM=z["MEMBER110"].astype(bool)
T,N=Y4.shape;Rm=np.where(MEM&CL4,Y4,np.nan);Rd=Rm-np.nanmean(Rm,axis=1,keepdims=True)
_O=SC.SignalChain.shape_position;_OL=SC.SignalChain.leg_positions
_S={"a":1.0,"t":None,"idx":None,"prev":np.zeros(200),"have":False,"smp":[],"n":0}
def plp(self,t):
    o,m=_OL(self,t);_S["t"]=int(t);_S["idx"]=m;return o,m
def pp(self,combo):
    base=_O(self,combo);a=_S["a"];m=_S["idx"];out=base
    if a<1.0 and m is not None and len(base)==len(m):
        prev=_S["prev"][m]
        if _S["have"]:
            out=(1-a)*prev+a*base;out=out-out.mean()
            g0,g1=np.abs(base).sum(),np.abs(out).sum()
            out=out*g0/g1 if (g1>1e-12 and g0>0) else base
        _S["prev"][:]=0.0;_S["prev"][m]=out;_S["have"]=True
    _S["n"]+=1
    if _S["n"]%40==0 and m is not None and len(out)==len(m):
        _S["smp"].append((_S["t"],out.copy(),m.copy()))
    return out
SC.SignalChain.shape_position=pp;SC.SignalChain.leg_positions=plp
RF._SRC,RF._SRC_KEY=None,None;RF.COST_BPS=3.63;src=RF.get_src(None,KING,S2)
def neff(smp):
    v=[]
    for t,w,m in smp:
        W=Rd[max(0,t-WIN):t]; W=W[np.isfinite(W).sum(1)>=20]
        if W.shape[0]<100: continue
        ok=np.isfinite(W).mean(0)>0.8; Wc=W[:,ok]; Wc=Wc[np.isfinite(Wc).all(1)]
        if Wc.shape[0]<60 or ok.sum()<20: continue
        cols=np.where(ok)[0]; pos={c:i for i,c in enumerate(cols)}
        sel=[(i,pos[c]) for i,c in enumerate(m) if c in pos]
        if len(sel)<20: continue
        wi=np.array([w[i] for i,_ in sel]); ci=np.array([p for _,p in sel])
        C=np.cov(Wc,rowvar=False)[np.ix_(ci,ci)]
        lam,V=np.linalg.eigh(C); lam=np.clip(lam,0,None)
        r=np.square(V.T@wi)*lam
        if r.sum()>0: v.append(r.sum()**2/np.square(r).sum())
    return float(np.mean(v)) if v else float("nan")
out={}
for a in (1.0,0.15,0.03):
    _S.update(a=a,prev=np.zeros(200),have=False,smp=[],n=0)
    RF._SRC,RF._SRC_KEY=src,(None,KING,S2);RF.COST_BPS=3.63
    o=RF.run_replay(funding_mode="rank",use_c5=True,shaping="cap",king=KING,s2=S2,
                    weights=dict(LW),verbose=False)
    ne=neff(_S["smp"])
    out[str(a)]={"n_eff_book":round(ne,2),"sh":float(o["avg_net_of_cost_sharpe"]),
                 "turn":float(o["netting"]["net_turn_ann"]),"n_samples":len(_S["smp"])}
    print(f" a={a:4.2f}: N_eff^book = {ne:5.2f}  (turn {out[str(a)]['turn']:.0f}, "
          f"Sh {out[str(a)]['sh']:+.3f}, n={len(_S['smp'])})",flush=True)
ns=out["0.03"]["n_eff_book"]
v=("扩宇宙有空间(平滑已完成去集中)" if ns>=6 else "瓶颈仍在收割侧" if ns<4 else "中间带")
print(f"\n★ 宇宙 N_eff ≈46 | 慢书 N_eff = {ns} ⇒ {v}",flush=True)
print("JSON_BEGIN");print(json.dumps(out));print("JSON_END")
