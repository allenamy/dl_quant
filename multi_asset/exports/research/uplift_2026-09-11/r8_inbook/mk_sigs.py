"""R8/BUILD-1 step 2: build the in-book FEMAT matrices for forms A / B / C / C2.
Signal chain is VERBATIM round-5 r5_basis/mk_sigs.py mk() (= p6_book.py mk() = the admitted Amihud sleeve
ORTHLAGA chain, proven bitwise identical by round-5 GATE S).  Only what we do with ORTH changes.
SIGN: FBSLOPE_NOLAG = -ORTH.  This sign was chosen POST-HOC in round 5 (flip.py header); it is FROZEN here
      by PREREG_r8 sha 83f4bed0..., written before any number of this round.
MISSING-BASIS FALLBACK (declared in prereg 2): ZB_eff := ZF  (form A) / ORTH := 0 (forms B,C,C2) = zero tilt.
RANK: scipy.stats.rankdata (AVERAGE).  NEVER argsort(argsort(.))."""
import numpy as np, json, os, hashlib
from scipy.stats import rankdata
R="/workspace/uplift_2026-09-11/r8_inbook"
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=PW["symbols"]
FE1=np.asarray(PW["f_fund_ema_v1"],float); BM=np.isfinite(FE1)
BP=np.load("/workspace/uplift_2026-09-11/r5_basis/basis_panel.npz",allow_pickle=True)
assert np.array_equal(BP["ts"].astype(np.int64),ts) and [str(x) for x in BP["symbols"]]==[str(x) for x in sym]
p_last=np.asarray(BP["p_last"],float); p_tw24=np.asarray(BP["p_tw24"],float)
# ---- re-assert the round-5 causality bar on the artifact we are reusing ----
H0=int(BP["hour0"]); ai=np.asarray(BP["ai"],np.int64)
assert np.all((H0+ai*3600)+3600<=ts), "CAUSALITY VIOLATION in reused basis_panel"
print("causality assert on reused basis_panel: OK  (newest bar close <= anchor)",flush=True)
BSLOPE=p_last-p_tw24
print("BSLOPE finite on fund-mask %.4f"%float(np.isfinite(BSLOPE[BM]).mean()),flush=True)
def rz_avg(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=rankdata(v[ok])/max(n-1,1)-0.5
    return out
ZF=rz_avg(np.where(BM,FE1,np.nan))
ZB=rz_avg(np.where(BM,BSLOPE,np.nan))
ORTH=np.full(ZB.shape,np.nan)
for i in range(len(ts)):
    ok=np.isfinite(ZB[i])&np.isfinite(ZF[i])
    if ok.sum()<10: continue
    x=ZF[i][ok]; y=ZB[i][ok]
    vx=float((x*x).sum()); b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
    ORTH[i][ok]=y-b*x
ORTHF=np.where(np.isfinite(ORTH),-ORTH,0.0)      # sign flip + zero-tilt fallback
ORTHF=np.where(BM,ORTHF,np.nan)
ZBF=np.where(np.isfinite(ZB),-ZB,np.nan)
ZBF=np.where(np.isfinite(ZBF),ZBF,ZF)            # fallback: no tilt
ZBF=np.where(BM,ZBF,np.nan)
# ---- gates from the UNTILTED reference book A0 (prereg 2) ----
A0=np.load("/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz",allow_pickle=True)
cols=[str(c) for c in A0["cols"]]; rec=np.asarray(A0["rec"],float); W=np.asarray(A0["W"],float)
ats=np.round(rec[:,cols.index("ts")]).astype(np.int64)
assert np.array_equal(ats,ts), "A0 rec ts axis != panel ts axis"
TR=np.zeros_like(W); TR[1:]=W[1:]-W[:-1]; TR[0]=W[0]
HOLD=np.zeros_like(W); HOLD[1:]=W[:-1]
GT=((np.sign(ORTHF)==np.sign(TR))&(np.abs(TR)>0)).astype(float)
GH=((np.sign(ORTHF)==np.sign(HOLD))&(np.abs(HOLD)>0)).astype(float)
print("gate coverage on fund-mask: G_T %.4f  G_H %.4f  (nonzero A0 trade cells %.4f, held cells %.4f)"%(
    float(GT[BM].mean()),float(GH[BM].mean()),float((np.abs(TR)>0)[BM].mean()),float((np.abs(HOLD)>0)[BM].mean())),flush=True)
os.makedirs(R+"/dev/sig",exist_ok=True)
MAN={}
def save(tag,M):
    M=np.where(BM,M,np.nan)
    assert np.array_equal(np.isfinite(M),BM), tag+": finite pattern != BM"
    p=R+"/dev/sig/%s.npz"%tag
    np.savez(p,symbols=sym,ts=ts,mat=M.astype(np.float32))
    MAN[tag]={"path":p,"sha256":hashlib.sha256(open(p,"rb").read()).hexdigest()[:16],
              "finite":round(float(np.isfinite(M).mean()),6)}
    print("sig",tag,json.dumps(MAN[tag]),flush=True)
for a in (0.05,0.10,0.20,0.35,0.50):
    save("R8A_BLEND_%03d"%round(a*100),(1-a)*ZF+a*ZBF)
for c in (0.10,0.25,0.50,1.00):
    save("R8B_OVL_%03d"%round(c*100),ZF+c*np.nan_to_num(ORTHF))
for c in (0.25,0.50,1.00):
    save("R8C_GT_%03d"%round(c*100),ZF+c*np.nan_to_num(ORTHF)*GT)
save("R8D_GH_050",ZF+0.50*np.nan_to_num(ORTHF)*GH)
# control: identity injection must reproduce A0 bitwise (device sanity: xz(ZF)==xz(FE1))
save("R8Z_IDENT",ZF.copy())
np.savez_compressed(R+"/parts.npz",ts=ts,symbols=sym,ZF=ZF.astype(np.float32),ZB=ZB.astype(np.float32),
                    ORTHF=np.where(BM,ORTHF,np.nan).astype(np.float32),GT=GT.astype(np.int8),GH=GH.astype(np.int8),BM=BM)
json.dump(MAN,open(R+"/SIG_MANIFEST.json","w"),indent=1)
print("MK_SIGS_DONE")
