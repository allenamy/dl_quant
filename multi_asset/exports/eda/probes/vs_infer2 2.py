"""C3 STAGE 6 — champion vs the runs it actually beat, under the SERVE caliber.

usage: vs_infer2.py --run {lam0,qim} --arm {TRAIN,SERVE}

★ WHICH RUNS. The dispatch said "champion vs xattn". Evidence says otherwise: the coronation
scripts (eval/eda_scripts/coronation_xattn_5yr.py, pair_xattn_5yr.py) compare
  X = wideA_lamorth0_xattn_5yr   (deployed champion, bit-confirmed)
  L = wideA_lamorth0_5yr         (same recipe MINUS the cross-asset attention block)
  Q = wideA_qim_multiyear        (quantile head)
`wideA_xattn` is a 3-fold run on the OTHER grid and is not what the deployed model was raced against.
All three above share ONE panel_ref (md5 185d3b6571, T=48168, horizon=4) and champion/L have
BIT-IDENTICAL fold splits, so this is a controlled A/B rather than a cross-grid comparison.

Champion's TRAIN/SERVE composites already exist as /tmp/vs_pred_king_{TRAIN,SERVE}.npz (built by
vs_infer.py with the identical recipe), so only L and Q need computing.

Frozen normalisation per fold from the AS-TRAINED panel, identical across arms; only ch31 changes.
READ-ONLY; writes only /tmp.
"""
import sys, os, glob, time, argparse
import numpy as np, pandas as pd, torch

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
sys.path.insert(0, REPO)
torch.backends.mkldnn.enabled = False
torch.set_num_threads(int(os.environ.get("NT", "6")))

ap = argparse.ArgumentParser()
ap.add_argument("--run", required=True, choices=["lam0", "qim"])
ap.add_argument("--arm", required=True, choices=["TRAIN", "SERVE", "CAUSAL"])
ap.add_argument("--bs", type=int, default=24)
args = ap.parse_args()

REG = {"lam0": dict(dir=MA + "/exports/train/wideA_lamorth0_5yr", kind="factor", K=6, xattn=False),
       "qim":  dict(dir=MA + "/exports/train/wideA_qim_multiyear", kind="qim", K=2, xattn=False)}
cfg = REG[args.run]
FULL = MA + "/exports/wide_dl_full.npz"

from multi_asset.data.wide_panel_dataset import WidePanelData
from multi_asset.model.wide_harness import (WideFactorModel, WideQIMModel, ConformerPanelEncoder)

t00 = time.time()
zf = np.load(FULL, allow_pickle=True)
member = zf["MEMBER110"]; CL4 = zf["CL4"]; YR4 = zf["YR4"]
ts = zf["ts"].astype(np.int64)
yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
T, N = member.shape
CH = np.array(zf["CH"])
chn = [str(c) for c in zf["ch_names"]]
i_b = chn.index("betaadj_ret24"); assert i_b == 31

arms = np.load("/tmp/vs_ch31_arms.npz")
assert np.array_equal(arms["TRAIN"], CH[:, :, i_b]), "TRAIN arm != stored ch31"
CH[:, :, i_b] = arms[args.arm]
print(f"[{args.run}/{args.arm}] ch31 swapped", flush=True)

d = WidePanelData(path=FULL, target_horizon=4)
ok = np.arange(T) >= (d.W - 1)
d.valid_hour = np.zeros(T, bool); d.valid_hour[ok] = CL4[ok].any(1)
day_year = np.array([int(yr[d.day == dd][0]) for dd in d.uniq_days])
mask_mat = (member & d.CL & np.isfinite(d.Y))          # == member & CL4 & finite(YR4)
base_mask = member & CL4 & np.isfinite(YR4)
offs = np.arange(-d.W + 1, 1)
K = cfg["K"]


def build():
    enc = ConformerPanelEncoder(32, d=64, n_blocks=2, kernel_size=15, dropout=0.2)
    if cfg["kind"] == "qim":
        return WideQIMModel(enc, n_quantiles=25, xattn=cfg["xattn"], n_xattn=1, dropout=0.2)
    return WideFactorModel(enc, n_factor_heads=K, xattn=cfg["xattn"], n_xattn=1, dropout=0.2)


OUT = np.full((T, N), np.nan, np.float32)
n_done = 0
for f in sorted(glob.glob(cfg["dir"] + "/fold_*_head_scores.npz"),
                key=lambda x: int(x.split("fold_")[1].split("_")[0])):
    fi = int(f.split("fold_")[1].split("_")[0])
    te = np.load(f)["te_rows"]
    te_year = int(np.bincount(yr[te] - yr[te].min()).argmax() + yr[te].min())
    d.set_fold(d.uniq_days[day_year < te_year])
    mu, sd = d.mu.copy(), d.sd.copy()
    model = build()
    miss, unexp = model.load_state_dict(torch.load(cfg["dir"] + "/fold_%d_model.pt" % fi,
                                                   map_location="cpu"), strict=False)
    assert not miss and not unexp, (args.run, fi, miss, unexp)   # a silent key mismatch = another model
    model.eval()
    rows = np.where(np.isin(d.day, d.uniq_days[day_year == te_year]) & d.valid_hour)[0]
    t0 = time.time()
    with torch.no_grad():
        for b0 in range(0, len(rows), args.bs):
            bh = rows[b0:b0 + args.bs]
            X = CH[bh[:, None] + offs[None, :]].transpose(0, 2, 1, 3)
            Xn = np.clip((np.nan_to_num(X) - mu) / sd, -10, 10).astype(np.float32)
            mm = mask_mat[bh].astype(np.float32)
            sc = model(torch.from_numpy(Xn), torch.from_numpy(mm))["factor_scores"].numpy()
            sc = np.where(mm[:, :, None] > 0.5, sc, np.nan)
            for j, t in enumerate(bh):
                base = np.where(base_mask[t])[0]
                if base.size < 5:
                    continue
                comp = np.zeros(base.size); nk = 0
                for k in range(sc.shape[2]):
                    col = sc[j, base, k]
                    if np.isfinite(col).all() and col.std() > 1e-12:
                        comp += (col - col.mean()) / col.std(); nk += 1
                if nk:
                    OUT[t, base] = (comp / nk).astype(np.float32)
            if b0 % (args.bs * 40) == 0:
                el = time.time() - t0
                print(f"  [{args.run}/{args.arm}] fold{fi} te={te_year} {b0}/{len(rows)} "
                      f"{el:.0f}s ({el/max(b0+args.bs,1):.3f}s/anchor)", flush=True)
    n_done += len(rows)
    print(f"[{args.run}/{args.arm}] fold{fi} te={te_year} rows={len(rows)} {time.time()-t0:.0f}s", flush=True)
    del model

np.savez("/tmp/vs2_pred_%s_%s.npz" % (args.run, args.arm), pred=OUT, ts=ts)
print(f"[{args.run}/{args.arm}] DONE rows={n_done} finite={int(np.isfinite(OUT).sum())} "
      f"total {time.time()-t00:.0f}s", flush=True)
