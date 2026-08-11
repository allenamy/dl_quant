"""C2-refute PROBE B — exact ch31 rebuild + reproduction fidelity + CPU timing. READ-ONLY.

B1  rebuild ch31 EXACTLY as build_wide_dl does (float64 from wide_panel_full) and assert the
    TRAIN arm is bit-identical to the stored channel. If that fails, everything downstream is
    a different quantity and the run must not proceed.
B2  re-infer king + s2 under the TRAIN caliber on a small anchor block and compare against the
    STORED pred panels (king_pred_panel.npz / s2_pred_panel_cl4.npz). This is the check that the
    thing I am perturbing is the thing that produced +1.814.
B3  time it, so the sampling decision is made on a measurement rather than a guess.
Writes only /tmp.
"""
import sys, os, glob, time, json
import numpy as np, pandas as pd, torch

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
sys.path.insert(0, REPO)
torch.backends.mkldnn.enabled = False        # matches signal/inference.py's CPU settings exactly
torch.set_num_threads(int(os.environ.get("NT", "26")))

FULL = MA + "/exports/wide_dl_full.npz"
WPANEL = MA + "/exports/wide_panel_full.npz"
XK = MA + "/exports/train/wideA_lamorth0_xattn_5yr"
XS = MA + "/exports/train/wideA_s2_y24_5yr"

# ---------------------------------------------------------------- B1
print("=" * 78); print("B1 — exact ch31 rebuild"); print("=" * 78, flush=True)
zp = np.load(WPANEL, allow_pickle=True)
print("wide_panel_full keys:", list(zp.keys())[:12])
Cl = zp["CLOSE"].astype(np.float64)
print("CLOSE shape", Cl.shape)
logc = np.log(np.where(Cl > 0, Cl, np.nan))


def _shift(A, n):
    out = np.full_like(A, np.nan)
    if n < len(A):
        out[n:] = A[:-n]
    return out


ret1 = logc - _shift(logc, 1)
market = np.nanmean(np.where(np.isfinite(ret1), ret1, np.nan), axis=1)
btc = np.nanmean(ret1, axis=1)                      # wide_factory's identical quantity
print("market == wide_factory btc :", np.allclose(np.nan_to_num(market), np.nan_to_num(btc), atol=0, rtol=0))

bser = pd.Series(btc)
n = 24
var_b = bser.rolling(n, min_periods=n // 2).var().values
cov = np.column_stack([pd.Series(ret1[:, si]).rolling(n, min_periods=n // 2).cov(bser).values
                       for si in range(ret1.shape[1])])
beta24 = cov / np.where(np.abs(var_b[:, None]) > 1e-18, var_b[:, None], np.nan)
ret24 = logc - _shift(logc, 24)

m0 = np.nan_to_num(market)
mk_train = np.convolve(m0, np.ones(24), "same")                 # centred  t-12..t+11   (11 future)
mk_serve = np.convolve(m0, np.ones(13))[:len(m0)]               # tail-13  t-12..t
mk_caus = np.convolve(m0, np.ones(24))[:len(m0)]                # tail-24  t-23..t
print("mk_train[100] check  sum(m0[88:112]) =", m0[88:112].sum(), " conv =", mk_train[100])
print("mk_serve[100] check  sum(m0[88:101]) =", m0[88:101].sum(), " conv =", mk_serve[100])
print("mk_caus [100] check  sum(m0[77:101]) =", m0[77:101].sum(), " conv =", mk_caus[100])

zf = np.load(FULL, allow_pickle=True)
chn = [str(c) for c in zf["ch_names"]]
i_b = chn.index("betaadj_ret24")
stored31 = zf["CH"][:, :, i_b]                                   # float32, already nan_to_num'd

arms = {}
for tag, mk in (("TRAIN", mk_train), ("SERVE", mk_serve), ("CAUSAL", mk_caus)):
    v = ret24 - beta24 * mk[:, None]
    v = np.nan_to_num(v.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    arms[tag] = v
d = np.abs(arms["TRAIN"].astype(np.float64) - stored31.astype(np.float64))
print("TRAIN vs stored ch31:  max|d| = %.6g   n_exact = %d / %d   corr = %.10f"
      % (d.max(), int((d == 0).sum()), d.size,
         np.corrcoef(arms["TRAIN"].ravel(), stored31.ravel())[0, 1]))
if d.max() > 1e-6:
    print("!! TRAIN arm is NOT the stored channel — STOP"); sys.exit(1)
print("=> TRAIN arm reproduces the stored channel; SERVE/CAUSAL are exact same-code perturbations.")
for tag in ("SERVE", "CAUSAL"):
    dd = np.abs(arms[tag].astype(np.float64) - stored31.astype(np.float64))
    print("   %-6s differs from TRAIN: mean|d| %.6g  max|d| %.6g  frac!=0 %.4f"
          % (tag, dd.mean(), dd.max(), float((dd != 0).mean())))
np.savez("/tmp/vs_ch31_arms.npz", TRAIN=arms["TRAIN"], SERVE=arms["SERVE"], CAUSAL=arms["CAUSAL"])
print("saved /tmp/vs_ch31_arms.npz", flush=True)
del zp, Cl, cov, beta24, ret24, ret1

# ---------------------------------------------------------------- B2/B3
print(); print("=" * 78); print("B2/B3 — reproduction fidelity + timing (TRAIN caliber)"); print("=" * 78, flush=True)
from multi_asset.data.wide_panel_dataset import WidePanelData
from multi_asset.model.wide_harness import WideFactorModel, ConformerPanelEncoder

member = zf["MEMBER110"]; CL4 = zf["CL4"]; YR4 = zf["YR4"]
ts = zf["ts"].astype(np.int64)
yr = pd.to_datetime(ts, unit="ms", utc=True).year.to_numpy()
T, N = member.shape
K = 6
DEV = "cpu"


def build_model():
    return WideFactorModel(ConformerPanelEncoder(32, d=64, n_blocks=2, kernel_size=15, dropout=0.2),
                           n_factor_heads=K, xattn=True, n_xattn=1, dropout=0.2).to(DEV)


def comp_rows(scores_rows, rows, base_mask):
    """king_pred_panel.py / densify comp recipe, restricted to the given rows."""
    out = np.full((len(rows), N), np.nan)
    for j, t in enumerate(rows):
        base = np.where(base_mask[t])[0]
        if base.size < 5:
            continue
        comp = np.zeros(base.size); nk = 0
        for k in range(K):
            col = scores_rows[j, base, k]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std(); nk += 1
        if nk:
            out[j, base] = comp / nk
    return out


king_stored = np.load(MA + "/exports/eda/king_pred_panel.npz", allow_pickle=True)["king_pred"]
s2_stored = np.load(MA + "/exports/eda/s2_pred_panel_cl4.npz", allow_pickle=True)["s2_pred"]

CHW = zf["CH"]                                          # (T,N,32) float32, TRAIN caliber as-stored
offs = np.arange(-168 + 1, 1)


def infer_block(model, mu, sd, rows, mask_mat, CHsrc, bs=24):
    """rows -> (len(rows), N, K) factor scores, mask_mat (T,N) bool used as the model mask."""
    out = np.full((len(rows), N, K), np.nan, np.float32)
    with torch.no_grad():
        for b0 in range(0, len(rows), bs):
            bh = np.asarray(rows[b0:b0 + bs])
            widx = bh[:, None] + offs[None, :]
            X = CHsrc[widx].transpose(0, 2, 1, 3)
            Xn = np.clip((np.nan_to_num(X) - mu) / sd, -10, 10).astype(np.float32)
            mm = mask_mat[bh].astype(np.float32)
            sc = model(torch.from_numpy(Xn), torch.from_numpy(mm))["factor_scores"].numpy()
            out[b0:b0 + bs] = np.where(mm[:, :, None] > 0.5, sc, np.nan)
    return out


report = {}
for name, run, H, base_is_member in (("king", XK, 4, False), ("s2", XS, 24, True)):
    print(f"\n--- {name} ---", flush=True)
    d = WidePanelData(path=FULL, target_horizon=H)
    ok = np.arange(T) >= (d.W - 1)
    d.valid_hour = np.zeros(T, bool); d.valid_hour[ok] = CL4[ok].any(1)
    if base_is_member:
        d.CL = member.copy()                                 # densify_s2_cl4 caliber
    day_year = np.array([int(yr[d.day == dd][0]) for dd in d.uniq_days])
    # fold 4 (te=2026) — the deployed one; validate there first
    te_year = 2026
    tr_days = d.uniq_days[day_year < te_year]
    d.set_fold(tr_days)
    mu, sd = d.mu, d.sd
    model = build_model()
    miss, unexp = model.load_state_dict(torch.load(run + "/fold_4_model.pt", map_location=DEV), strict=False)
    assert not miss and not unexp, (miss, unexp)
    model.eval()
    # model mask exactly as iter_batches builds it
    if base_is_member:
        mask_mat = member & np.isfinite(d.Y)                 # d.CL was set to member
        mask_mat = member & member & np.isfinite(d.Y)
    else:
        mask_mat = member & CL4 & np.isfinite(d.Y)
    rows_all = np.where(np.isin(d.day, d.uniq_days[day_year == te_year]) & d.valid_hour)[0]
    rows = rows_all[:96]
    t0 = time.time()
    sc = infer_block(model, mu, sd, rows, mask_mat, CHW)
    el = time.time() - t0
    base_mask = member & CL4 & np.isfinite(YR4)
    C = comp_rows(sc, rows, base_mask)
    ref = (king_stored if name == "king" else s2_stored)[rows]
    good = np.isfinite(C) & np.isfinite(ref)
    corr = np.corrcoef(C[good], ref[good])[0, 1] if good.sum() > 10 else float("nan")
    mad = float(np.abs(C[good] - ref[good]).max()) if good.any() else float("nan")
    # per-anchor cross-sectional corr (the caliber that matters)
    pac = []
    for j in range(len(rows)):
        g = np.isfinite(C[j]) & np.isfinite(ref[j])
        if g.sum() >= 20:
            pac.append(np.corrcoef(C[j, g], ref[j, g])[0, 1])
    print("  rows=%d  time=%.1fs  (%.3f s/anchor)  cover mine=%d stored=%d"
          % (len(rows), el, el / len(rows), int(np.isfinite(C).sum()), int(np.isfinite(ref).sum())))
    print("  POOLED corr(mine, stored) = %.8f   max|d| = %.4g" % (corr, mad))
    print("  PER-ANCHOR xsec corr: n=%d  median %.8f  min %.8f"
          % (len(pac), float(np.median(pac)) if pac else np.nan, float(np.min(pac)) if pac else np.nan))
    report[name] = dict(sec_per_anchor=el / len(rows), pooled_corr=float(corr),
                        per_anchor_median=float(np.median(pac)) if pac else None,
                        per_anchor_min=float(np.min(pac)) if pac else None,
                        n_anchors_total_CL4=int(len(rows_all)))
    del d, model

json.dump(report, open("/tmp/vs_probeB.json", "w"), indent=1)
print("\n" + json.dumps(report, indent=1))
print("DONE probe B", flush=True)
