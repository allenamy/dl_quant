"""OKXRHO: build f_fund_ema_v1-equivalent matrices for OKX and for a cold-started Binance control.
Recipe is a line-by-line mirror of /workspace/pod_panel_ext.py L116-162 (v1 arm):
  interval per settlement (from response spacing, snapped to ALLOWED), rate_nf = rate*(8/iv),
  wall-clock EMA HL=3d seeded at the first settlement, anchor sampling searchsorted(right)-1,
  >12h staleness -> NaN.
ENV WHITELIST (E-0826-D) = EMPTY SET."""
import os
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG","PANEL_OUT","EXPORT_PANEL","EMA_STATE_JSON")
assert not [k for k in _F if k in os.environ], [k for k in _F if k in os.environ]
import numpy as np, json, hashlib, datetime as dt
HL=3*86400.0
ALLOWED=np.array([1.0,2.0,4.0,6.0,8.0])
OUT="/workspace/r9okx"
PAN="/workspace/data/wide_panel_4h_v2ext.npz"   # the panel the archived A0 arms actually read (dev_v4 symlink chain, VERIFIED)
P=np.load(PAN,allow_pickle=True)
TS=P["ts"].astype(np.int64); SY=[str(x) for x in P["symbols"]]
NT,NS=len(TS),len(SY)
FE_PANEL=P["f_fund_ema_v1"]

def ema_v1_matrix(per_sym, t_start=None):
    """per_sym: {sym: (ft_sec, rate, iv_or_None)}. t_start: drop settlements before this epoch-sec (cold start)."""
    M=np.full((NT,NS),np.nan,np.float32)
    n=0
    for j,s in enumerate(SY):
        v=per_sym.get(s)
        if v is None: continue
        ft,fr,fiv=v
        if t_start is not None:
            k=ft>=t_start
            if k.sum()<2: continue
            ft,fr=ft[k],fr[k]; fiv=fiv[k] if fiv is not None else None
        if len(ft)<2: continue
        dt_h=np.round(np.diff(ft)/3600.0)
        dv=np.full(len(ft),np.nan); dv[1:]=np.where((dt_h>0)&(dt_h<=24),dt_h,np.nan)
        iv_full=np.where(np.isfinite(fiv),fiv,dv) if fiv is not None else dv
        iv_full=np.where(np.isfinite(iv_full),iv_full,8.0)
        iv_full=ALLOWED[np.argmin(np.abs(iv_full[:,None]-ALLOWED[None,:]),axis=1)]
        rate_nf=fr*(8.0/iv_full)
        e1=np.full(len(fr),np.nan); acc=None; prev=None
        for k in range(len(fr)):
            if acc is None: acc=rate_nf[k]
            else:
                d=max(ft[k]-prev,1); a=1-0.5**(d/HL); acc=acc+a*(rate_nf[k]-acc)
            prev=ft[k]; e1[k]=acc
        pos=np.searchsorted(ft,TS,side="right")-1
        okp=pos>=0
        col=np.full(NT,np.nan,np.float32); col[okp]=e1[pos[okp]].astype(np.float32)
        stale=okp&((TS-np.where(okp,ft[np.maximum(pos,0)],0))>12*3600)
        col[stale]=np.nan
        M[:,j]=col; n+=1
    return M,n

# ---- OKX ----
Z=np.load(f"{OUT}/okx_funding_raw.npz",allow_pickle=True)
osyms=[str(x) for x in Z["syms"]]
okx={s:(Z[f"ft_{s}"].astype(np.int64), Z[f"fr_{s}"].astype(np.float64), None) for s in osyms}
OKX_T0=int(min(v[0][0] for v in okx.values()))
FE_OKX,n_okx=ema_v1_matrix(okx)
# ---- Binance (same months) ----
B=np.load(f"{OUT}/bin_funding_raw.npz",allow_pickle=True)
bsyms=[str(x) for x in B["syms"]]
binf={s:(B[f"ft_{s}"].astype(np.int64), B[f"fr_{s}"].astype(np.float64), B[f"iv_{s}"].astype(np.float64)) for s in bsyms}
FE_BINWARM,n_bw=ema_v1_matrix(binf)                 # from 2026-05 archives: builder self-check vs panel
FE_BINCOLD,n_bc=ema_v1_matrix(binf,t_start=OKX_T0)  # cold-started at the same instant as OKX: venue-isolating control

rep={"panel":PAN,"n_ts":NT,"n_sym":NS,
     "okx_first_settlement_utc":dt.datetime.utcfromtimestamp(OKX_T0).isoformat()+"Z",
     "n_sym_okx":n_okx,"n_sym_bin_warm":n_bw,"n_sym_bin_cold":n_bc,
     "okx_syms_pulled":len(osyms),"bin_syms_pulled":len(bsyms)}

# ---- GATE B: my builder on Binance data must reproduce the canonical panel column ----
W0=int(dt.datetime(2026,8,1,tzinfo=dt.timezone.utc).timestamp()); W1=int(dt.datetime(2026,8,31,tzinfo=dt.timezone.utc).timestamp())
r=(TS>=W0)&(TS<=W1)
a=FE_BINWARM[r].ravel(); b=FE_PANEL[r].ravel(); ok=np.isfinite(a)&np.isfinite(b)
rep["GATE_B_builder_vs_panel_2026_08"]={"n":int(ok.sum()),
    "pearson":float(np.corrcoef(a[ok],b[ok])[0,1]),
    "maxabs":float(np.abs(a[ok]-b[ok]).max()),
    "med_abs":float(np.median(np.abs(a[ok]-b[ok]))),
    "finite_panel":float(np.isfinite(b).mean()),"finite_mine":float(np.isfinite(a).mean())}
np.savez_compressed(f"{OUT}/fe_mats.npz", ts=TS, symbols=np.array(SY),
    FE_OKX=FE_OKX, FE_BINWARM=FE_BINWARM, FE_BINCOLD=FE_BINCOLD, okx_t0=np.array(OKX_T0))
for tag,M in (("OKX",FE_OKX),("BINCOLD",FE_BINCOLD),("BINWARM",FE_BINWARM)):
    np.savez_compressed(f"{OUT}/femat_{tag}.npz", ts=TS, symbols=np.array(SY), mat=M)
    rep[f"sha16_femat_{tag}"]=hashlib.sha256(open(f"{OUT}/femat_{tag}.npz","rb").read()).hexdigest()[:16]
print(json.dumps(rep,indent=1))
json.dump(rep,open(f"{OUT}/build_fe_report.json","w"),indent=1)
