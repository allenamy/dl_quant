"""C2-refute PROBE A — reconstruction validation BEFORE the main run. READ-ONLY.

Answers, in order:
  V1  which panel is the AS-TRAINED input for king / s2 (wide_dl_full vs wide_dl_full_fundfix)?
  V2  can I reconstruct the frozen fold-4 mu/sd from the panel + fold split?  (bit-check vs shipped)
  V3  is channel 31 = betaadj_ret24 leaky in the AS-TRAINED panel (rebuild same vs causal)?
  V4  fold assignment of every anchor (which fold's model is OOS for each hour)?
Nothing is written outside /tmp.
"""
import sys, json, hashlib
import numpy as np, pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")

XK = MA + "/exports/train/wideA_lamorth0_xattn_5yr"
XS = MA + "/exports/train/wideA_s2_y24_5yr"
FULL = MA + "/exports/wide_dl_full.npz"
FIX = MA + "/exports/wide_dl_full_fundfix.npz"

print("=" * 78); print("V1 — which panel is the AS-TRAINED input?"); print("=" * 78, flush=True)

pk = np.load(XK + "/panel_ref.npz", allow_pickle=True)
ps = np.load(XS + "/panel_ref.npz", allow_pickle=True)
print("king panel_ref keys:", list(pk.keys()))
print("king panel_ref horizon:", pk["horizon"], " s2 horizon:", ps["horizon"])
print("king ts len", pk["ts"].shape, "s2 ts len", ps["ts"].shape)

for tag, path in (("wide_dl_full", FULL), ("wide_dl_full_fundfix", FIX)):
    z = np.load(path, allow_pickle=True)
    ts = z["ts"].astype(np.int64)
    same_ts = bool(len(ts) == len(pk["ts"]) and np.array_equal(ts, pk["ts"].astype(np.int64)))
    chn = [str(c) for c in z["ch_names"]]
    fi = chn.index("funding_ema")
    # panel_ref.funding is CH[:,:,funding_ema] of the training panel -> the discriminator
    fund_panel = z["CH"][:, :, fi].astype(np.float32)
    fk = pk["funding"].astype(np.float32)
    ok = np.isfinite(fund_panel) & np.isfinite(fk)
    eq = bool(np.array_equal(np.nan_to_num(fund_panel, nan=-9e9), np.nan_to_num(fk, nan=-9e9)))
    mx = float(np.abs(fund_panel[ok] - fk[ok]).max()) if ok.any() else float("nan")
    # also Yraw / YR / member / CL
    y4 = z["Y4"].astype(np.float32)
    eqy = bool(np.array_equal(np.nan_to_num(y4, nan=-9e9), np.nan_to_num(pk["Yraw"].astype(np.float32), nan=-9e9)))
    print(f"[{tag}] ts_identical={same_ts} funding_bitidentical={eq} max|dfunding|={mx:.6g} Yraw_bitidentical={eqy}")
    del z, fund_panel

print()
print("=" * 78); print("V2 — reconstruct frozen fold-4 mu/sd"); print("=" * 78, flush=True)

from multi_asset.data.wide_panel_dataset import WidePanelData
from multi_asset.train.train_wide_harness import year_folds

nd = np.load("/tmp/norm_stats_deployed.npz", allow_pickle=True)

# which panel path won V1? decide by funding bit-identity to king panel_ref
zf = np.load(FULL, allow_pickle=True)
chn = [str(c) for c in zf["ch_names"]]
fi = chn.index("funding_ema")
full_fund_eq = np.array_equal(np.nan_to_num(zf["CH"][:, :, fi].astype(np.float32), nan=-9e9),
                              np.nan_to_num(pk["funding"].astype(np.float32), nan=-9e9))
del zf
AS_TRAINED = FULL if full_fund_eq else FIX
print("AS_TRAINED panel chosen:", AS_TRAINED, flush=True)
print("ch_names[31] check pending below")

res = {}
for name, H, run in (("king", 4, XK), ("s2", 24, XS)):
    d = WidePanelData(path=AS_TRAINED, target_horizon=H, aux_horizons=(1, 24) if H == 4 else (1, 4))
    print(f"[{name}] T={d.T} N={d.N} C={d.C} valid_hours={int(d.valid_hour.sum())}", flush=True)
    print(f"[{name}] ch_names[31]={d.ch_names[31]!r}  idx('betaadj_ret24')={d.ch_names.index('betaadj_ret24')}")
    folds = year_folds(d, embargo_days=8, val_days=30, year_from=None)
    print(f"[{name}] year_folds -> {len(folds)} folds: " +
          ", ".join(f"{i}:te={f['year']}({len(f['te'])}d)" for i, f in enumerate(folds)))
    # fold 4 = the deployed one
    hits = []
    for i, f in enumerate(folds):
        d.set_fold(f["tr"])
        dmu = float(np.abs(d.mu - nd[f"{name}_mu"]).max())
        dsd = float(np.abs(d.sd - nd[f"{name}_sd"]).max())
        rel = float(np.abs((d.sd - nd[f"{name}_sd"]) / nd[f"{name}_sd"]).max())
        hits.append((i, f["year"], dmu, dsd, rel))
        print(f"   fold{i} te={f['year']}: max|dmu|={dmu:.3e} max|dsd|={dsd:.3e} maxrel_sd={rel:.3e}", flush=True)
    best = min(hits, key=lambda r: r[4])
    print(f"[{name}] BEST MATCH = fold{best[0]} (te={best[1]}), max rel sd err {best[4]:.3e}")
    res[name] = dict(folds=[(int(f["year"]), int(f["te"][0]), int(f["te"][-1]),
                            int(f["tr"][0]), int(f["tr"][-1])) for f in folds],
                     best_fold=int(best[0]), best_year=int(best[1]), rel_sd_err=best[4])
    del d

json.dump(res, open("/tmp/vs_probeA_folds.json", "w"), indent=1)

print()
print("=" * 78); print("V3 — leak in ch31 of the AS-TRAINED panel"); print("=" * 78, flush=True)
z = np.load(AS_TRAINED, allow_pickle=True)
CH = z["CH"]; chn = [str(c) for c in z["ch_names"]]
mem = z["MEMBER110"]; CL4 = z["CL4"]; Y4 = z["Y4"].astype(np.float64)
i_b = chn.index("betaadj_ret24"); i_r24 = chn.index("ret_24h"); i_bet = chn.index("beta_24h")
ret1 = CH[:, :, chn.index("ret_1h")].astype(np.float64)
mk = np.where(mem, ret1, np.nan)
market = np.nanmean(mk, axis=1)
market = np.nan_to_num(market)
mk_same = np.convolve(market, np.ones(24), "same")
mk_caus24 = np.convolve(market, np.ones(24))[:len(market)]           # tail-24 causal
# serve = tail-13 (t-12..t)  == 'same' with the future 11 taps zero-filled
k13 = np.zeros(24); k13[:13] = 1.0
mk_serve = np.convolve(market, np.ones(13))[:len(market)]
r24 = CH[:, :, i_r24].astype(np.float64); bet = CH[:, :, i_bet].astype(np.float64)
rec_train = r24 - bet * mk_same[:, None]
stored = CH[:, :, i_b].astype(np.float64)
ok = np.isfinite(stored) & np.isfinite(rec_train)
print("rebuild 'same' vs stored ch31: max|d| = %.4g  corr = %.6f  (n=%d)"
      % (np.abs(stored[ok] - rec_train[ok]).max(),
         np.corrcoef(stored[ok], rec_train[ok])[0, 1], ok.sum()))

from scipy.stats import rankdata
def xsec_ic(P, Y, mask):
    out = []
    for t in range(P.shape[0]):
        b = np.where(mask[t] & np.isfinite(P[t]) & np.isfinite(Y[t]))[0]
        if b.size < 20: continue
        out.append(np.corrcoef(rankdata(P[t, b]), rankdata(Y[t, b]))[0, 1])
    return np.array(out)

msk = mem & CL4
for tag, mkv in (("TRAIN same-24", mk_same), ("SERVE tail-13", mk_serve), ("CAUSAL tail-24", mk_caus24)):
    P = r24 - bet * mkv[:, None]
    ic = xsec_ic(P, Y4, msk)
    print("  %-16s rank-IC %+.5f  t %+.2f  n=%d" % (tag, ic.mean(), ic.mean()/ic.std()*np.sqrt(len(ic)), len(ic)))
ic_st = xsec_ic(stored, Y4, msk)
print("  %-16s rank-IC %+.5f  t %+.2f  n=%d" % ("STORED ch31", ic_st.mean(), ic_st.mean()/ic_st.std()*np.sqrt(len(ic_st)), len(ic_st)))
print("DONE probe A", flush=True)
