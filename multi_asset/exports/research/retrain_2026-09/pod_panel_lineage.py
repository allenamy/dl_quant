"""面板血统: 各版本面板的 Y4 到底是 Σ简单 / 对数和 / 复利简单? 用 5 分钟原生数据对 40 个锚逐位对账(旧窗 [E, E+47] 与新窗 [E+1, E+48] 都试)."""
import numpy as np, time, glob
Z=np.load("/workspace/data/dlnative_5m_wide829_f16_ext.npz",allow_pickle=True); zts=Z["ts"].astype(np.int64); D=Z["data"]; zsym=[str(s) for s in Z["symbols"]]; zrow={int(t):i for i,t in enumerate(zts)}
print("5m:", D.shape, time.strftime("%Y-%m-%d",time.gmtime(zts[0])), "->", time.strftime("%Y-%m-%d",time.gmtime(zts[-1])))
for pf in ("wide_panel_4h_v1.npz","wide_panel_4h_v2ext.npz","wide_panel_4h_v3splice.npz"):
    try: P=np.load(f"/workspace/data/{pf}",allow_pickle=True)
    except Exception as e: print(pf, "load fail", e); continue
    keys=P.files; ykey="Y4" if "Y4" in keys else ("y4" if "y4" in keys else None)
    pts=P["ts"].astype(np.int64); psym=[str(s) for s in P["symbols"]] if "symbols" in keys else None
    print(f"\n== {pf}: {len(pts)} 锚 {time.strftime('%Y-%m-%d',time.gmtime(pts[0]))}→{time.strftime('%Y-%m-%d',time.gmtime(pts[-1]))}, symbols {len(psym) if psym else None}, Y4 key {ykey}")
    if ykey is None or psym is None: continue
    Y=P[ykey]; cidx=np.array([zsym.index(s) if s in zsym else -1 for s in psym]); okc=cidx>=0
    # 取 40 个均匀分布的锚
    pick=np.linspace(0,len(pts)-1,40).astype(int); res={"旧窗Σ简单":[], "旧窗对数和":[], "旧窗复利":[], "新窗Σ简单":[], "新窗对数和":[], "新窗复利":[]}
    for i in pick:
        t=int(pts[i]); r=zrow.get(t)
        if r is None or r+49>=len(zts): continue
        y=Y[i][okc].astype(np.float64)
        for win,(lo,hi) in (("旧窗",(r,r+48)),("新窗",(r+1,r+49))):
            seg=D[lo:hi,:,0].astype(np.float64)[:,cidx[okc]]; fin=np.isfinite(seg); rr=np.where(fin,seg,0); n=fin.sum(0)
            S=rr.sum(0); L=np.log1p(rr).sum(0); C=np.expm1(L); bad=n<46
            for nm,x in ((f"{win}Σ简单",S),(f"{win}对数和",L),(f"{win}复利",C)):
                x=x.copy(); x[bad]=np.nan; m=np.isfinite(x)&np.isfinite(y); res[nm].append(np.abs(x[m]-y[m]))
    for nm,v in res.items():
        if v: d=np.concatenate(v); print(f"   {nm:10s}: median|Δ| {np.median(d):.2e}  share<1e-6 {np.mean(d<1e-6):.3f}  n={len(d)}")
print("LINEAGE_DONE")
