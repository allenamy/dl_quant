"""0C — rebuild the funding_ema channel with the SETTLEMENT-INTERVAL DIMENSION FIXED.

> created 2026-07-25 | Session: 0C re-run on corrected funding factor | 状态: final

BUG (0B): FUND_EMA stores the EMA of the PER-SETTLEMENT-PERIOD rate, but 55/140 coins settle every
4h and 85 every 8h (16 migrate mid-history). A 4h coin with the SAME annualised carry shows half the
per-period rate. The engine ranks the funding leg cross-sectionally (_rank_centered), and
rank-centring removes individual scale but NOT a group-level scale offset -> 4h coins are
systematically ranked "low funding" -> leg sign -1 pushes them to the long side.

FIX: normalise every settlement rate to an 8h-EQUIVALENT before the EMA:
    rate_8h_equiv = rate * (8 / interval_h_of_that_settlement)
Everything else is held bit-identical to build_wide_panel.py: EMA span = max(2, round(24/median
interval_h)) with adjust=False, causal ffill (searchsorted right-1) onto the hourly grid. Only the
LEVEL changes, so the experiment isolates the dimension fix.

CONTROL (must pass before anything downstream is believed): rebuild the SHIPPED recipe from the same
CSVs and compare to the shipped panel channel. If the control does not reproduce the shipped channel
to ~1e-6, the rebuild pipeline is wrong and no conclusion follows.

Writes exports/eda/funding_ema_normfix.npz {ts, symbols, FN (normalised), FS (shipped rebuild),
IH (interval in force, hourly grid)} + funding_dim_fix_control.json.
"""
import sys, json, os.path as p
import numpy as np, pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
EDA = MA + "/exports/eda/"
WIDE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data/wide"
sys.path.insert(0, MA)

W = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
ts = W["ts"].astype(np.int64)
symbols = [str(s) for s in W["symbols"]]
ch = [str(c) for c in W["ch_names"]]
FI = ch.index("funding_ema")
SHIPPED = W["CH"][:, :, FI].astype(np.float64)
T, N = SHIPPED.shape
print(f"panel {T}x{N}, shipped funding_ema finite {np.isfinite(SHIPPED).mean():.4f}", flush=True)

FN = np.full((T, N), np.nan)      # normalised (8h-equivalent)
FS = np.full((T, N), np.nan)      # shipped-recipe rebuild (control)
IH = np.full((T, N), np.nan)      # settlement interval in force
meta = []
for j, s in enumerate(symbols):
    f = p.join(WIDE, f"{s}_funding.csv")
    if not p.exists(f):
        meta.append({"sym": s, "ok": False}); continue
    d = pd.read_csv(f).sort_values("fundingTime_ms")
    rate = pd.to_numeric(d["fundingRate"], errors="coerce").values.astype(np.float64)
    ihr = pd.to_numeric(d["funding_interval_h"], errors="coerce").values.astype(np.float64)
    fts = d["fundingTime_ms"].values.astype(np.int64)
    ok = np.isfinite(rate) & np.isfinite(ihr) & (ihr > 0)
    rate, ihr, fts = rate[ok], ihr[ok], fts[ok]
    if len(rate) < 3:
        meta.append({"sym": s, "ok": False}); continue
    ih_med = float(np.median(ihr))
    span = max(2, int(round(24.0 / max(ih_med, 1.0))))          # EXACT build_wide_panel rule
    ema_s = pd.Series(rate).ewm(span=span, adjust=False).mean().values
    ema_n = pd.Series(rate * (8.0 / ihr)).ewm(span=span, adjust=False).mean().values
    idx = np.searchsorted(fts, ts, side="right") - 1            # causal ffill, EXACT rule
    good = idx >= 0
    FS[good, j] = ema_s[idx[good]]
    FN[good, j] = ema_n[idx[good]]
    IH[good, j] = ihr[idx[good]]
    meta.append({"sym": s, "ok": True, "n": int(len(rate)), "ih_median": ih_med, "span": span,
                 "ih_unique": sorted(set(ihr.tolist())), "migrated": bool(len(set(ihr.tolist())) > 1)})

# ---------------- CONTROL: does the rebuild reproduce the shipped channel? ----------------
m = np.isfinite(SHIPPED) & np.isfinite(FS)
diff = np.abs(SHIPPED[m] - FS[m])
corr = float(np.corrcoef(SHIPPED[m], FS[m])[0, 1])
print(f"[CONTROL] shipped vs rebuild: corr={corr:.9f} mean|diff|={diff.mean():.3e} "
      f"max|diff|={diff.max():.3e} n={m.sum():,}", flush=True)
mn = np.isfinite(SHIPPED) & np.isfinite(FN)
corr_n = float(np.corrcoef(SHIPPED[mn], FN[mn])[0, 1])
print(f"[fix] shipped vs normalised: corr={corr_n:.6f}", flush=True)

# ---------------- how big is the group offset the bug creates? ----------------
mem = W["MEMBER110"]
rows = np.where(mem.any(1))[0]
g4, g8, gN = [], [], []
for t in rows[::24]:
    v = np.where(mem[t] & np.isfinite(SHIPPED[t]) & np.isfinite(IH[t]))[0]
    if v.size < 20:
        continue
    is4 = IH[t, v] <= 4.0
    if is4.sum() < 3 or (~is4).sum() < 3:
        continue
    x = SHIPPED[t, v]; xr = pd.Series(x).rank().values; xr = (xr - xr.mean()) / (len(xr) / 2)
    xn = FN[t, v]; xnr = pd.Series(xn).rank().values; xnr = (xnr - xnr.mean()) / (len(xnr) / 2)
    g4.append(xr[is4].mean()); g8.append(xr[~is4].mean()); gN.append(xnr[is4].mean() - xnr[~is4].mean())
g4, g8, gN = np.array(g4), np.array(g8), np.array(gN)
gap_shipped = float((g4 - g8).mean()); gap_norm = float(gN.mean())
print(f"[group offset] mean rank-centred(4h) - rank-centred(8h): shipped {gap_shipped:+.4f} -> "
      f"normalised {gap_norm:+.4f}  (n={len(g4)} sampled anchors)", flush=True)

n4 = sum(1 for x in meta if x.get("ok") and x["ih_median"] <= 4)
n8 = sum(1 for x in meta if x.get("ok") and x["ih_median"] > 4)
nmig = sum(1 for x in meta if x.get("ok") and x["migrated"])
print(f"[universe] 4h-median {n4} / 8h-median {n8} / migrated mid-history {nmig}", flush=True)

np.savez(EDA + "funding_ema_normfix.npz", ts=ts, symbols=np.array(symbols, dtype=object),
         FN=FN.astype(np.float32), FS=FS.astype(np.float32), IH=IH.astype(np.float32))
json.dump(dict(title="funding_ema settlement-interval dimension fix", created="2026-07-25", auditor="0C",
               fix="rate_8h_equiv = rate * (8 / interval_h_of_that_settlement), applied BEFORE the EMA; "
                   "EMA span / adjust / causal-ffill held bit-identical to build_wide_panel.py",
               control=dict(corr=corr, mean_abs_diff=float(diff.mean()), max_abs_diff=float(diff.max()),
                            n=int(m.sum()),
                            verdict="PASS" if (corr > 0.999999 and diff.mean() < 1e-6) else "FAIL"),
               shipped_vs_normalised_corr=corr_n,
               group_offset=dict(rank_centred_4h_minus_8h_shipped=gap_shipped,
                                 rank_centred_4h_minus_8h_normalised=gap_norm,
                                 n_sampled_anchors=int(len(g4)),
                                 note="rank-centred to [-1,1]; a non-zero value means the 4h group sits "
                                      "systematically on one side of the cross-section"),
               universe=dict(n_4h_median=n4, n_8h_median=n8, n_migrated=nmig),
               per_coin=meta),
          open(EDA + "funding_dim_fix_control.json", "w"), indent=1, default=str)
print("SAVED funding_ema_normfix.npz + funding_dim_fix_control.json", flush=True)
