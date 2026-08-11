"""C2-refute STAGE 1 — re-infer one model under one channel caliber, FULL CL4 anchor coverage.

usage: vs_infer.py --model king|s2 --arm TRAIN|SERVE|CAUSAL
Frozen normalisation: mu/sd are recomputed per fold from the AS-TRAINED panel (wide_dl_full.npz,
TRAIN caliber) and are IDENTICAL across arms -- a frozen model receives frozen normalisation, and
only the input channel changes. This mirrors the deployed situation and the §9 three-caliber probe.
Fold attribution is strictly OOS: each ts uses only its own test year's checkpoint.
READ-ONLY w.r.t. the repo; writes only /tmp/vs_pred_{model}_{arm}.npz
"""
import sys, os, glob, time, json, argparse
import numpy as np, pandas as pd, torch

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
sys.path.insert(0, REPO)
torch.backends.mkldnn.enabled = False
torch.set_num_threads(int(os.environ.get("NT", "4")))

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True, choices=["king", "s2"])
ap.add_argument("--arm", required=True, choices=["TRAIN", "SERVE", "CAUSAL"])
ap.add_argument("--bs", type=int, default=24)
args = ap.parse_args()

FULL = MA + "/exports/wide_dl_full.npz"
RUN = {"king": MA + "/exports/train/wideA_lamorth0_xattn_5yr",
       "s2": MA + "/exports/train/wideA_s2_y24_5yr"}[args.model]
H = {"king": 4, "s2": 24}[args.model]
K = 6

from multi_asset.data.wide_panel_dataset import WidePanelData
from multi_asset.model.wide_harness import WideFactorModel, ConformerPanelEncoder

t00 = time.time()
zf = np.load(FULL, allow_pickle=True)
member = zf["MEMBER110"]; CL4 = zf["CL4"]; YR4 = zf["YR4"]
ts = zf["ts"].astype(np.int64)
yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
T, N = member.shape
CH = np.array(zf["CH"])                       # (T,N,32) float32 -- TRAIN caliber as built
chn = [str(c) for c in zf["ch_names"]]
i_b = chn.index("betaadj_ret24")
assert i_b == 31, i_b

arms = np.load("/tmp/vs_ch31_arms.npz")
assert np.array_equal(arms["TRAIN"], CH[:, :, i_b]), "TRAIN arm != stored ch31 (rebuild broken)"
CH[:, :, i_b] = arms[args.arm]                # <<< the ONLY change between arms
print(f"[{args.model}/{args.arm}] ch31 swapped; mean|d vs TRAIN| = "
      f"{np.abs(arms[args.arm].astype(np.float64) - arms['TRAIN'].astype(np.float64)).mean():.6g}", flush=True)

d = WidePanelData(path=FULL, target_horizon=H)
ok = np.arange(T) >= (d.W - 1)
d.valid_hour = np.zeros(T, bool); d.valid_hour[ok] = CL4[ok].any(1)     # CL4 anchor grid
if args.model == "s2":
    d.CL = member.copy()                      # densify_s2_cl4.py caliber (member inference mask)
day_year = np.array([int(yr[d.day == dd][0]) for dd in d.uniq_days])

# model mask exactly as iter_batches builds it: member & CL & finite(Y)
mask_mat = (member & d.CL & np.isfinite(d.Y))
base_mask = member & CL4 & np.isfinite(YR4)   # composite base (king_pred_panel / densify recipe)
offs = np.arange(-d.W + 1, 1)

OUT = np.full((T, N), np.nan, np.float32)
DEV = "cpu"
years = sorted({int(y) for y in day_year})
n_done = 0
for f in sorted(glob.glob(RUN + "/fold_*_head_scores.npz"),
                key=lambda x: int(x.split("fold_")[1].split("_")[0])):
    fi = int(f.split("fold_")[1].split("_")[0])
    z = np.load(f); te = z["te_rows"]
    te_year = int(np.bincount(yr[te] - yr[te].min()).argmax() + yr[te].min())
    tr_days = d.uniq_days[day_year < te_year]
    d.set_fold(tr_days)                        # frozen normalisation for this fold (TRAIN caliber)
    mu, sd = d.mu.copy(), d.sd.copy()
    model = WideFactorModel(ConformerPanelEncoder(32, d=64, n_blocks=2, kernel_size=15, dropout=0.2),
                            n_factor_heads=K, xattn=True, n_xattn=1, dropout=0.2).to(DEV)
    miss, unexp = model.load_state_dict(torch.load(RUN + "/fold_%d_model.pt" % fi, map_location=DEV),
                                        strict=False)
    assert not miss and not unexp, (fi, miss, unexp)
    model.eval()
    rows = np.where(np.isin(d.day, d.uniq_days[day_year == te_year]) & d.valid_hour)[0]
    t0 = time.time()
    with torch.no_grad():
        for b0 in range(0, len(rows), args.bs):
            bh = rows[b0:b0 + args.bs]
            widx = bh[:, None] + offs[None, :]
            X = CH[widx].transpose(0, 2, 1, 3)
            Xn = np.clip((np.nan_to_num(X) - mu) / sd, -10, 10).astype(np.float32)
            mm = mask_mat[bh].astype(np.float32)
            sc = model(torch.from_numpy(Xn), torch.from_numpy(mm))["factor_scores"].numpy()
            sc = np.where(mm[:, :, None] > 0.5, sc, np.nan)
            # composite: per-ts z-mean over live heads over the base set
            for j, t in enumerate(bh):
                base = np.where(base_mask[t])[0]
                if base.size < 5:
                    continue
                comp = np.zeros(base.size); nk = 0
                for k in range(K):
                    col = sc[j, base, k]
                    if np.isfinite(col).all() and col.std() > 1e-12:
                        comp += (col - col.mean()) / col.std(); nk += 1
                if nk:
                    OUT[t, base] = (comp / nk).astype(np.float32)
            if b0 % (args.bs * 40) == 0:
                el = time.time() - t0
                print(f"  [{args.model}/{args.arm}] fold{fi} te={te_year} {b0}/{len(rows)} "
                      f"{el:.0f}s ({el/max(b0+args.bs,1):.3f}s/anchor)", flush=True)
    n_done += len(rows)
    print(f"[{args.model}/{args.arm}] fold{fi} te={te_year} rows={len(rows)} "
          f"{time.time()-t0:.0f}s", flush=True)
    del model

np.savez("/tmp/vs_pred_%s_%s.npz" % (args.model, args.arm), pred=OUT, ts=ts)
print(f"[{args.model}/{args.arm}] DONE rows={n_done} finite={int(np.isfinite(OUT).sum())} "
      f"total {time.time()-t00:.0f}s -> /tmp/vs_pred_{args.model}_{args.arm}.npz", flush=True)
