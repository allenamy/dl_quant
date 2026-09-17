import numpy as np, json, calendar, hashlib, time
A="/workspace/fp2_2026-09/health_check/dev_v4/probe_artifacts"; UMP="/workspace/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz"; CP="/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"
um=np.load(UMP, allow_pickle=True); mts=um["ts"].astype(np.int64); mrow={int(t):i for i,t in enumerate(mts)}; M=np.asarray(um["mask"])
Z=np.load(CP, allow_pickle=True); CTS=Z["ts"].astype(np.int64); r5=Z["data"][:,:,0].astype(np.float32); r5z=np.where(np.isfinite(r5), r5, 0).astype(np.float64); CS=np.concatenate([np.zeros((1,r5.shape[1])), np.cumsum(r5z,0)]); crow={int(t):i for i,t in enumerate(CTS)}; del r5, r5z
W0=calendar.timegm((2022,6,30,0,0,0)); UB=calendar.timegm((2026,8,30,20,0,0)); K24=calendar.timegm((2024,1,1,0,0,0))
rec={"gate":"FP2_OUTSIDE_MASK_PNL","utc":time.strftime("%FT%TZ", time.gmtime()),"method":"per anchor t in window: sum_j W[t,j]*r4h[t,j] split by mask[t,j]; r4h = sum of 5m simple returns over cache rows [E, E+48) (a proxy of the book accounting, identical for both arms); share = outside/(inside+outside)","inputs":{"umask":UMP,"umask_sha256":hashlib.sha256(open(UMP,"rb").read()).hexdigest(),"cache":CP},"books":{}}
for arm in ("A0","A1"):
  for s in ("42","2027"):
    p=f"{A}/w10_ablation_series_V4_{arm}_dyn_s{s}.npz"; z=np.load(p, allow_pickle=True); r=np.asarray(z["d30_n2_c42_rec"], float); W=np.asarray(z["d30_n2_c42_W"], np.float64); ts=r[:,0].astype(np.int64)
    out={}
    for wn,lo in (("W_ALPHA",W0),("KING_LIVE",K24)):
        ti=to=0.0; n=0; co=0; cnz=0; wo=0.0
        for i in range(len(ts)):
            t=int(ts[i])
            if t<lo or t>UB or t not in crow: continue
            e=crow[t]
            if e+48>=len(CS): continue
            r4=CS[e+48]-CS[e]; m=M[mrow[t]]; w=W[i]
            ti+=float((w[m]*r4[m]).sum()); to+=float((w[~m]*r4[~m]).sum()); n+=1; co+=int(((np.abs(w)>0)&~m).sum()); cnz+=int(((np.abs(w)>0)&~m&(np.abs(r4)>0)).sum()); wo+=float(np.abs(w[~m]).sum())
        out[wn]={"anchors":n,"pnl_inside_per_anchor_1e4":1e4*ti/n,"pnl_outside_per_anchor_1e4":1e4*to/n,"outside_share":to/(ti+to) if (ti+to) else None,"outside_cells":co,"outside_cells_with_nonzero_4h_return":cnz,"mean_abs_weight_outside_per_anchor":wo/n}
    rec["books"][f"{arm}/dyn/s{s}"]={"path":p,"sha256":hashlib.sha256(open(p,"rb").read()).hexdigest(),**out}
    print(arm, s, {k:(round(v["outside_share"],4), v["outside_cells"], v["outside_cells_with_nonzero_4h_return"], round(v["mean_abs_weight_outside_per_anchor"],4)) for k,v in out.items()})
json.dump(rec, open("/workspace/fp2_2026-09/v4_gates/OUTSIDE_MASK_PNL.json","w"), indent=1); print("written")
