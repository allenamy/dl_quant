"""horizon_profile.py — where inside the 4h target does the new information live? (diagnostic, not a gate; motivated by the bar-shift receipt of the
A1 basis columns: IC ~0 with the right edge at E-10min, peak at E-5min, half at E, ~0 inside the window.)
For each column of the shift-0 feature files and for the saved king predictions (BASE / A1 / A1A2, per seed), mean per-anchor Spearman IC vs
  (a) the cumulative simple-return sum over the first n 5-min bars after the anchor, n in {1, 2, 3, 6, 12, 24, 48} (n=48 = the y4 definition
      Σ ret5 over rows E+1..E+48 of the ext cache, checked against META y4), and
  (b) the EXECUTABLE window: Σ ret5 over rows E+6..E+48 = from E+25 min (first full bar after the live N+23 min execution) to E+4h.
Δ vs BASE on (b) is the part of the S1 gain a book traded at N+23 could see at all. Folds: predictions exist only on their test years (2024-26);
features are evaluated over all anchors and per year. env: META_IN FILES ("tag=path,...") PREDS ("tag=path,...") OUT_JSON"""
import os, sys, json, time, hashlib
import numpy as np
from scipy.stats import spearmanr
SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
sys.path.insert(0, "/workspace")
from zload import zload
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); T0 = int(CTS[0]); RET = np.asarray(Z["data"][:, :, 0], np.float32); del Z
MT = np.load(os.environ.get("META_IN", "/workspace/data/wide_fea_v2ext_meta.npz"), allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; nA = len(E_ts); yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
Ei = (E_ts - T0) // 300; assert np.all(CTS[Ei] == E_ts)
fin = np.isfinite(RET); CS = np.concatenate([np.zeros((1, RET.shape[1])), np.cumsum(np.where(fin, RET, 0), 0, dtype=np.float64)]); CN = np.concatenate([np.zeros((1, RET.shape[1]), int), np.cumsum(fin, 0)])
def win(a, b):   # Σ ret5 over rows Ei+a .. Ei+b inclusive; NaN if any bar missing
    s = CS[Ei + b + 1] - CS[Ei + a]; n = CN[Ei + b + 1] - CN[Ei + a]; return np.where(n == (b - a + 1), s, np.nan).astype(np.float32)
HZ = {f"n{n}": win(1, n) for n in (1, 2, 3, 6, 12, 24, 48)}; HZ["exec_25m_4h"] = win(6, 48)
chk = np.isfinite(y4) & np.isfinite(HZ["n48"]); print(f"y4 check: max|Σret5(1..48) - META y4| = {np.abs(HZ['n48'][chk] - y4[chk]).max():.2e} over {chk.sum()} cells", flush=True)
def sp(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 30: return np.nan
    r = spearmanr(a[ok], b[ok]); return r.correlation if hasattr(r, "correlation") else r[0]
def profile(X, rows):
    out = {}
    for h, Y in HZ.items():
        ics = np.array([sp(X[i, members[i]], Y[i, members[i]]) for i in rows])
        out[h] = round(float(np.nanmean(ics)), 4)
    return out
res = {"self_sha256": SELF, "horizons": list(HZ), "features": {}, "preds": {}}
for kv in os.environ.get("FILES", "").split(","):
    if not kv: continue
    tag, p = kv.split("="); Zf = np.load(p, allow_pickle=True); F = np.asarray(Zf["F"], np.float32); names = [str(n) for n in Zf["names"]]
    for k, nm in enumerate(names):
        r = {"all": profile(F[:, :, k], range(nA))}
        for y in (2024, 2025, 2026): r[str(y)] = profile(F[:, :, k], np.where(yrs == y)[0])
        res["features"][f"{tag}:{nm}"] = r; print(f"FEAT {tag}:{nm} all {r['all']}", flush=True)
for kv in os.environ.get("PREDS", "").split(","):
    if not kv: continue
    tag, p = kv.split("="); P = np.load(p); rows = np.where(np.isfinite(P).any(1))[0]
    r = {"test_rows": profile(P, rows), "n_rows": int(len(rows))}
    for y in (2024, 2025, 2026): r[str(y)] = profile(P, rows[yrs[rows] == y])
    res["preds"][tag] = r; print(f"PRED {tag} test_rows {r['test_rows']}", flush=True)
json.dump(res, open(os.environ["OUT_JSON"], "w"), indent=1); print("HORIZON_DONE", flush=True)
