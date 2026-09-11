"""r12 DIAGNOSTIC / GATE 0 -- inputs only. E-0826-D: env whitelist = EMPTY SET, asserted."""
import os, sys, json, time, calendar, hashlib
import numpy as np
from scipy.stats import rankdata
_W=["CAL","LEGS","PHI","FSEED","FPRED","LOOK","WRULE","W3FIX","MEMBERS_TOPN","TRADE_TOPN","FTRIM","FTRIM_TH",
    "FTPOS","RNSM","LTRIM_TH","CDAMP","SLEEVE","SEATNET","SEATF10","KTAIL","KMOD","KMOD_L","KMOD_AGREE",
    "KMOD_F10","FUNDSCALE","FEMAT_NPZ","UMASK_NPZ","UMASK_SCOPE","REF_SKIP","COSTB_JSON","SLOW_NPY"]
_s={k:os.environ[k] for k in _W if k in os.environ}; assert _s=={}, _s
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<24),b""): h.update(c)
    return h.hexdigest()
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
def iso(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
U="/workspace/uplift_2026-09-11"; APY=2190; WARM=900
ARM=f"{U}/r9/dev_ext/probe_artifacts/w10_ablation_series_R9_A1x_ext_s42.npz"
ARM2=f"{U}/r9/dev_ext/probe_artifacts/w10_ablation_series_R9_A1x_ext_s2027.npz"
META=f"{U}/r6/out/meta_newprod_v4_x0910.npz"; PANEL=f"{U}/r6/out/wide_panel_4h_v2ext_x0910.npz"
P5M="/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz"
OUT={"read_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"env_whitelist":[],"inputs":{}}
for k,v in [("arm_s42",ARM),("arm_s2027",ARM2),("meta",META),("panel",PANEL)]:
    OUT["inputs"][k]={"path":v,"sha256":sha(v)[:32]}
OUT["inputs"]["panel5m"]={"path":P5M,"bytes":os.path.getsize(P5M)}
Z=np.load(ARM,allow_pickle=True); CFG=json.loads(str(Z["config_json"]))
assert CFG["UPLIFT"]["self_sha256"][:16]=="b88e35a46b93d712"
assert CFG["CAL"]=="log" and CFG["PHI"]==0.45 and CFG["LEGS"]=="101" and CFG["WRULE"]=="msharpe" \
   and CFG["LOOK"]==900 and CFG["UMASK_SCOPE"]=="m1" and CFG["W3FIX"] is None and CFG["FTRIM"]=="zero"
OUT["arm_config"]={k:CFG.get(k) for k in ("CAL","PHI","LEGS","WRULE","LOOK","UMASK_SCOPE","W3FIX","FTRIM",
                                          "FTRIM_TH","MEMBERS_TOPN","FSEED","FPRED","COSTB_JSON","SLOW_NPY")}
COLS=[str(c) for c in Z["cols"]]; C={k:i for i,k in enumerate(COLS)}
R=np.asarray(Z["d30_n2_c42_rec"],float); W=np.asarray(Z["d30_n2_c42_W"],float)
ts=np.round(R[:,C["ts"]]).astype(np.int64); SYM=[str(s) for s in Z["symbols"]]
print("rows",len(ts),iso(ts[0]),iso(ts[-1]),"W",W.shape,flush=True)
# ---- GATE 0: reproduce the planning number ----
g=R[:,C["net_ex"]]/R[:,C["gross_total"]]
sl=slice(WARM,None); tsP=ts[sl]; gP=g[sl]
def sr(x): return float(np.mean(x)/np.std(x,ddof=1)*np.sqrt(APY))
OUT["GATE0"]={"n":int(len(gP)),"first":iso(tsP[0]),"last":iso(tsP[-1]),
              "mean_g":float(gP.mean()),"sharpe":sr(gP)}
Z2=np.load(ARM2,allow_pickle=True); R2=np.asarray(Z2["d30_n2_c42_rec"],float)
g2=(R2[:,C["net_ex"]]/R2[:,C["gross_total"]])[sl]
OUT["GATE0_s2027"]={"n":int(len(g2)),"mean_g":float(g2.mean()),"sharpe":sr(g2)}
assert abs(OUT["GATE0"]["mean_g"]-0.6602)<5e-4 and abs(OUT["GATE0"]["sharpe"]-1.2857)<5e-4, OUT["GATE0"]
assert OUT["GATE0"]["n"]==9199
print("GATE0 PASS",json.dumps(OUT["GATE0"]),flush=True)
# ---- meta / panel ----
MT=np.load(META,allow_pickle=True); E_ts=MT["E_ts"].astype(np.int64); members=MT["members"]; y4=MT["y4"]; qvk=MT["qvk"]
PW=np.load(PANEL,allow_pickle=True); pts=PW["ts"].astype(np.int64)
FN=PW["f_fund_now"]; IV=PW["f_fund_iv"]; pw_row={int(t):j for j,t in enumerate(pts)}
assert [str(s) for s in PW["symbols"]]==SYM
OUT["meta"]={"n_anchors":int(len(E_ts)),"first":iso(E_ts[0]),"last":iso(E_ts[-1]),"y4_shape":list(y4.shape)}
# device skips anchors with no panel row / sel<80 => align rec ts into meta index
mi={int(t):i for i,t in enumerate(E_ts)}
ridx=np.array([mi[int(t)] for t in ts])
# ---- V1: meta y4 convention vs 5m panel (E-0825-H: never infer semantics) ----
Z5=np.load(P5M,allow_pickle=True); t5=Z5["ts"].astype(np.int64); ch=[str(c) for c in Z5["ch"]]
assert ch[0]=="ret5" and [str(s) for s in Z5["symbols"]]==SYM
r5map={int(t):k for k,t in enumerate(t5)}
D5=Z5["data"]
rng=np.random.default_rng(0); pick=rng.choice(np.arange(3000,len(ts)-10),12,replace=False)
v1={"conv_E_to_E47":[], "conv_E1_to_E48":[]}
for p in pick:
    i=ridx[p]; k0=r5map[int(E_ts[i])]; m=members[i][:40]
    a=np.nansum(np.asarray(D5[k0:k0+48,m,0],np.float64),0)
    b=np.nansum(np.asarray(D5[k0+1:k0+49,m,0],np.float64),0)
    yy=np.asarray(y4[i,m],np.float64); ok=np.isfinite(yy)
    v1["conv_E_to_E47"].append(float(np.nanmax(np.abs(a[ok]-yy[ok]))))
    v1["conv_E1_to_E48"].append(float(np.nanmax(np.abs(b[ok]-yy[ok]))))
OUT["V1_y4_convention"]={"max_abs_E..E+47":float(np.max(v1["conv_E_to_E47"])),
                         "max_abs_E+1..E+48":float(np.max(v1["conv_E1_to_E48"])),
                         "note":"5m ret5 is float16; tolerance is f16 accumulation, not exactness"}
print("V1",json.dumps(OUT["V1_y4_convention"]),flush=True)
# ---- V2: carry bill per unit gross (the I-1 monitor, causal: same FN/IV row FTRIM already reads) ----
carry_bill=R[:,C["carry_ex"]]/R[:,C["gross_total"]]     # bps/anchor/gross, POSITIVE = we pay
OUT["V2_carry_bill"]={"mean":float(carry_bill.mean()),
    "pct":{q:float(np.percentile(carry_bill,q)) for q in (1,5,25,50,75,90,95,97.5,99,99.5,99.9)},
    "mean_postwarm":float(carry_bill[sl].mean()),
    "pct_postwarm":{q:float(np.percentile(carry_bill[sl],q)) for q in (50,90,95,99)}}
# ---- V3: book's own realised rank-IC (causal, computed from archived W and meta y4) ----
nA=len(ts); ic=np.full(nA,np.nan)
for p in range(nA):
    i=ridx[p]; m=members[i]; w=W[p,m]; yy=np.asarray(y4[i,m],np.float64)
    ok=np.isfinite(yy)&(np.abs(w)>1e-12)
    if ok.sum()<30: continue
    a=rankdata(w[ok]); b=rankdata(yy[ok])
    ic[p]=float(np.corrcoef(a,b)[0,1])
OUT["V3_book_ic"]={"finite":int(np.isfinite(ic).sum()),"mean":float(np.nanmean(ic)),
   "pct":{q:float(np.nanpercentile(ic,q)) for q in (1,5,10,25,50,75,95,99)}}
for Lw in (6,24,42,90):
    tr=np.full(nA,np.nan)
    cs=np.concatenate([[0.0],np.nancumsum(np.nan_to_num(ic))]); cn=np.concatenate([[0],np.cumsum(np.isfinite(ic))])
    for p in range(Lw+1,nA):
        lo=p-Lw; n=cn[p]-cn[lo]
        if n>=Lw//2: tr[p]=(cs[p]-cs[lo])/n
    OUT["V3_book_ic"]["trailing_%d"%Lw]={"pct":{q:float(np.nanpercentile(tr,q)) for q in (1,5,10,50,90)},
        "frac_below_-0.0228":float(np.nanmean(tr<-0.0228)),"frac_below_-0.0443":float(np.nanmean(tr<-0.0443))}
print("V3",json.dumps(OUT["V3_book_ic"]),flush=True)
# ---- V4: market state (causal detector inputs) ----
mkt=np.full(nA,np.nan); brd=np.full(nA,np.nan)
for p in range(nA):
    i=ridx[p]; m=members[i]; yy=np.asarray(y4[i,m],np.float64); ok=np.isfinite(yy)
    if ok.sum()<30: continue
    mkt[p]=float(np.median(yy[ok])); brd[p]=float((yy[ok]>0).mean())
OUT["V4_market"]={"mkt_med_pct":{q:float(np.nanpercentile(mkt,q)) for q in (1,5,50,95,99)},
                  "breadth_pct":{q:float(np.nanpercentile(brd,q)) for q in (1,5,50,95,99)}}
np.savez_compressed(f"{U}/r12_intervene/out/diag_series_s42.npz",ts=ts,ridx=ridx,ic=ic,mkt=mkt,brd=brd,
                    carry_bill=carry_bill,g=g,cols=np.array(COLS),rec=R.astype(np.float64))
OUT["self_sha256"]=sha(os.path.abspath(__file__))
json.dump(OUT,open(f"{U}/r12_intervene/out/DIAG0.json","w"),indent=1)
print("DIAG_DONE")
