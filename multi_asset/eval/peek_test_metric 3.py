"""Quick peek: evaluate the current best_model.pt on the fold-0 test set.
Health check for sigma-collapse / signal existence (DENSE — directional, not final)."""
import numpy as np, torch, glob, os.path as p, sys
from scipy.stats import pearsonr, spearmanr
DEV="cuda" if torch.cuda.is_available() else "cpu"
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from src.model.dual_path_model_v3 import DualPathLOBModelV3

RUN = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train/btc_dualpath_run1/fold_0"
NPZ = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/windowed_npz/bnfbtc"
TEST_DAYS = [d.strip() for d in open(p.join(RUN,"..","test_days.txt")).read().split()] if p.exists(p.join(RUN,"..","test_days.txt")) else None
# test window 2025-02-09 .. 2025-05-09
import datetime as dt
days = sorted(int(p.basename(f)[:8]) for f in glob.glob(p.join(NPZ,"*.npz")))
test = [str(d) for d in days if 20250209 <= d <= 20250509]
print(f"test days: {len(test)} ({test[0]}..{test[-1]})")

st = np.load(p.join(RUN,"stats_cache.npz"))
x_mean, x_std = st["x_mean"], st["x_std"]; y_med, y_sig = float(st["y_median"]), float(st["y_sigma"])

ck = torch.load(p.join(RUN,"best_model.pt"), map_location="cpu", weights_only=False)
cfg=dict(ck["config"]); cfg["use_film_multistage"]=True
model = DualPathLOBModelV3(**cfg); model.load_state_dict(ck["state"], strict=True); model.eval(); model.to(DEV)

Xs,Rs,Ps,Ys,Ms=[],[],[],[],[]
for d in test:
    z=np.load(p.join(NPZ,f"{d}.npz"))
    Xs.append(z["X"]); Rs.append(z["X_raw"].astype(np.float32)); Ps.append(z["regime_prior"])
    Ys.append(z["y_600"]); Ms.append(z["y_mask_600"])
X=np.concatenate(Xs); R=np.concatenate(Rs); P=np.concatenate(Ps); Y=np.concatenate(Ys); M=np.concatenate(Ms).astype(bool)
Xn=np.clip((X-x_mean)/x_std,-10,10).astype(np.float32)
print(f"test windows: {len(X)}  valid mask: {M.sum()}")

q50=np.zeros(len(X))
with torch.no_grad():
    for i in range(0,len(X),512):
        j=min(i+512,len(X))
        out=model(x_feat=torch.from_numpy(Xn[i:j]).to(DEV), x_raw=torch.from_numpy(R[i:j]).to(DEV),
                  regime_prior=torch.from_numpy(P[i:j].astype(np.float32)).to(DEV))
        q=out["quantiles"] if isinstance(out,dict) else out
        q50[i:j]=q[:,1].detach().cpu().numpy()
m=M & np.isfinite(Y) & np.isfinite(q50)
qd=q50*y_sig+y_med
P_=pearsonr(qd[m],Y[m])[0]; S_=spearmanr(qd[m],Y[m])[0]
# clean-ish: every 4th window (~stride 720s)
mi=np.where(m)[0][::4]
Pc=pearsonr(qd[mi],Y[mi])[0]; Sc=spearmanr(qd[mi],Y[mi])[0]
print(f"\n=== epoch-8 BEST on test (DENSE): P={P_:+.4f} S={S_:+.4f} | sigma_yhat/sigma_y={qd[m].std()/Y[m].std():.4f} | n={m.sum()}")
print(f"=== clean-ish (every 4th): P={Pc:+.4f} S={Sc:+.4f} n={len(mi)}")
print(f"=== single-asset REG_arch fold-0 reference: P~0.058 ===")
