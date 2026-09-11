"""Track D batch 2 — universe-slice sleeves (listing age) at v4 caliber. Same device, same env."""
import numpy as np, os, json, subprocess, time
HC="/workspace/review_scratch/health_check"; D="/workspace/uplift_2026-09-11/dev_v4s"
OUT="/workspace/uplift_2026-09-11/trackD_v4"; os.makedirs(OUT,exist_ok=True)
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); BASE=np.isfinite(FE1)
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); mem=MT["members"]; y4=MT["y4"]; NW=829
# listing age: first anchor index at which the name is a member with finite y4 (era-synchronous, causal)
first=np.full(NW,10**9,np.int64)
for i in range(len(E)):
    m=np.asarray(mem[i]); ok=np.isfinite(y4[i,m]); idx=m[ok]
    new=idx[first[idx]==10**9]
    if len(new): first[new]=i
emap={int(t):i for i,t in enumerate(E)}
AGE=np.full((len(ts),NW),10**9,np.int64)      # age in anchors at each panel row
for j,t in enumerate(ts):
    i=emap.get(int(t))
    if i is None: continue
    AGE[j]=i-first
print("age matrix built; frac<540 among base", float(((AGE<540)&BASE).sum()/max(BASE.sum(),1)))
YOUNG=540   # 90 days = 540 anchors
V={}
V["YOUNGFUND"]=np.where(BASE & (AGE<YOUNG), FE1, np.nan)
V["OLDFUND"]  =np.where(BASE & (AGE>=YOUNG), FE1, np.nan)
V["YOUNG180"] =np.where(BASE & (AGE<1080), FE1, np.nan)
R24=np.asarray(PW["f_rev_24h"],float)
V["YOUNGREV"] =np.where(BASE & (AGE<YOUNG), -R24, np.nan)
AM=np.asarray(PW["f_amihud_24h"],float)
V["YOUNGILLIQ"]=np.where(BASE & (AGE<YOUNG), AM, np.nan)
COMMON=["CAL=log","WRULE=msharpe","LOOK=900","MEMBERS_TOPN=829","UMASK_SCOPE=m1",
        f"UMASK_NPZ={HC}/masks/umask_UPIT_CRYPTO.npz",f"COSTB_JSON={HC}/calib/costb_fee_steady.json",
        "SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"]
def run(tag):
    env=dict(os.environ); env.update(OMP_NUM_THREADS="2",OPENBLAS_NUM_THREADS="2",MKL_NUM_THREADS="2")
    cmd=["env"]+COMMON+["LEGS=001","PHI=0","FTRIM=off",f"FEMAT_NPZ={D}/sig/cur2.npz",f"OUT_TAG={tag}",
         "/workspace/venv/bin/python",f"{HC}/w10_health.py"]
    with open(f"{D}/logs/{tag}.log","w") as lf:
        rc=subprocess.call(cmd,cwd=D,stdout=lf,stderr=subprocess.STDOUT,env=env)
    src=f"{D}/probe_artifacts/w10_ablation_series_{tag}.npz"
    if rc!=0 or not os.path.exists(src): print("FAIL",tag,rc,flush=True); return False
    A=np.load(src,allow_pickle=True)
    np.savez_compressed(f"{OUT}/{tag}.npz",cols=A["cols"],rec=A["d30_n2_c42_rec"],rec_s0=A["S0_rec"],
                        legs_ts=A["legs_ts"],legs_fund=A["legs_fund"],config_json=A["config_json"])
    os.remove(src); return True
t0=time.time()
for name,M in V.items():
    for sgn,tg in ((1.0,"p"),(-1.0,"m")):
        tag=f"SL_{name}__{tg}"
        if os.path.exists(f"{OUT}/{tag}.npz"): continue
        np.savez(f"{D}/sig/cur2.npz",symbols=sym,ts=ts,mat=(sgn*M).astype(np.float32))
        ok=run(tag); print(f"{tag:24s} {'ok' if ok else 'FAIL'} {time.time()-t0:6.1f}s",flush=True)
        os.remove(f"{D}/sig/cur2.npz")
print("BATCH2 DONE")
