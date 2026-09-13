#!/usr/bin/env python3
"""t7_universe_pod2.py — T7 coverage denominator: the replay's eligible names per anchor (A0 rule), exported as booleans only.
Rule replicated from the pinned replay device (w10_sleeve_t1.py = w10_sleeve_r18.py + T1 instr; A0 knobs from r18_drive.py L53-55):
  members_i = all names with finite qvk[i] (MEMBERS_TOPN=829 rebuild, w10_sleeve_t1.py L81-86)
  m = members_i ∩ UMASK_UPIT_CRYPTO row (UMASK_SCOPE=m1, L229-232; no mask row => unmasked)
  C0 (A0 canonical, forward rule): sel = isfinite(y4[i, m]) & qv4h >= 2.5e5, qv4h = expm1(clip(qvk,0,30))*48  (L255-256)
  NW (r18 causal rule, R18_ELIG=1):  sel = isfinite(y4[i-1, m]) & qv4h >= 2.5e5
  device skips an anchor when sel.sum() < 80 (L262) or its panel row is missing (L227-228).
Cross-check (third-party): per anchor n_sel and len(m) vs the archived r18 arm runs C0_s42 / NW_s42 `rec` columns 0 (ts), 8 (sel.sum()), 9 (len(m)).
Only those three rec columns are read. y4 is used ONLY through isfinite(); no return value is read into any output.
Launch: env -i PATH=... HOME=/root nice -n 10 /workspace/venv/bin/python t7_universe_pod2.py PATH,HOME"""
import os, sys, json, hashlib, time
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
import numpy as np
META = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"
UMASK = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
ARMS = {"C0": "/workspace/uplift_2026-09-11/r18_foundation/arms/C0_s42.npz", "NW": "/workspace/uplift_2026-09-11/r18_foundation/arms/NW_s42.npz"}
OUT = "/workspace/uplift_r2_2026-09-13/T7/receipts"
os.makedirs(OUT, exist_ok=True)
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
REC = {"device": os.path.basename(__file__), "device_sha256": sha(os.path.abspath(__file__)), "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "env_actual": {k: os.environ[k] for k in sorted(os.environ)}, "python": sys.version.split()[0], "numpy": np.__version__,
       "inputs": {k: {"path": p, "realpath": os.path.realpath(p), "sha256": sha(p)} for k, p in [("meta", META), ("panel", PANEL), ("umask", UMASK)] + [("arm_" + a, p) for a, p in ARMS.items()]}}
MT = np.load(META, allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); y4f = np.isfinite(MT["y4"]); qvk = MT["qvk"]; nA = len(E_ts)
PW = np.load(PANEL, allow_pickle=True)
pts = PW["ts"].astype(np.int64); SYM = [str(s) for s in PW["symbols"]]; NW = len(SYM)
assert NW == 829 and qvk.shape == (nA, NW) and y4f.shape == (nA, NW), (NW, qvk.shape, y4f.shape)
pw_row = {int(t): j for j, t in enumerate(pts)}
UZ = np.load(UMASK, allow_pickle=True)
assert [str(x) for x in UZ["symbols"]] == SYM, "umask symbols mismatch"
umap = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"])
elig = {"C0": np.zeros((nA, NW), bool), "NW": np.zeros((nA, NW), bool)}
n_m = np.full(nA, -1, np.int64); n_sel = {"C0": np.full(nA, -1, np.int64), "NW": np.full(nA, -1, np.int64)}
has_row = np.zeros(nA, bool); mask_applied = np.zeros(nA, bool)
for i in range(nA):
    j = pw_row.get(int(E_ts[i]))
    if j is None: continue
    has_row[i] = True
    q = np.nan_to_num(qvk[i], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5]; m = np.sort(o[:829]).astype(np.int64)
    k = umap.get(int(pts[j]))
    if k is not None: m = m[UM[k][m]]; mask_applied[i] = True
    qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
    liq = qv4h >= 2.5e5
    s = {"C0": y4f[i, m] & liq, "NW": ((y4f[i - 1, m]) if i >= 1 else np.zeros(len(m), bool)) & liq}
    n_m[i] = len(m)
    for a in ("C0", "NW"):
        elig[a][i, m[s[a]]] = True; n_sel[a][i] = int(s[a].sum())
# cross-check vs archived arm runs (rec columns 0, 8, 9 only)
XC = {}
for a, p in ARMS.items():
    Z = np.load(p, allow_pickle=True)
    keys = sorted(x for x in Z.files if x.endswith("_rec"))
    assert len(keys) >= 1, (a, keys)
    idx = {int(t): i for i, t in enumerate(E_ts)}
    for kk in keys:   # every rec array in the arm file is checked (C0 files hold S0_rec and d30_n2_c42_rec)
        r = Z[kk]; ts = r[:, 0].astype(np.int64); nsel_dev = r[:, 8].astype(np.int64); nm_dev = r[:, 9].astype(np.int64); del r
        ii = np.array([idx[int(t)] for t in ts])
        x = {"n_rec_rows": int(len(ts)), "n_sel_mismatch": int((n_sel[a][ii] != nsel_dev).sum()), "len_m_mismatch": int((n_m[ii] != nm_dev).sum()),
             "anchors_with_elig_ge80_but_no_rec": int(((n_sel[a] >= 80) & ~np.isin(E_ts, ts)).sum()),
             "anchors_in_rec_with_sel_lt_80": int((n_sel[a][ii] < 80).sum()),
             "rec_first_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(ts.min()))), "rec_last_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(ts.max())))}
        x["PASS"] = x["n_sel_mismatch"] == 0 and x["len_m_mismatch"] == 0
        XC[a + ":" + kk] = x
        if kk.startswith("d30"): np.save(OUT + f"/rec_ts_{a}.npy", ts)
REC["crosscheck_vs_archived_arms"] = XC
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
REC["per_year"] = {int(y): {"n_anchors": int((yrs == y).sum()), "n_anchors_with_panel_row": int(((yrs == y) & has_row).sum()),
                            "mean_n_elig_C0_on_ge80": float(np.mean(n_sel["C0"][(yrs == y) & (n_sel["C0"] >= 80)])) if ((yrs == y) & (n_sel["C0"] >= 80)).any() else None}
                   for y in sorted(set(yrs.tolist()))}
# per-symbol Binance-panel liquidity window (first/last anchor with finite qvk): used only to choose mapping-check dates
fin = np.isfinite(qvk)
first = np.array([int(E_ts[np.argmax(fin[:, c])]) if fin[:, c].any() else -1 for c in range(NW)])
last = np.array([int(E_ts[nA - 1 - np.argmax(fin[::-1, c])]) if fin[:, c].any() else -1 for c in range(NW)])
np.savez_compressed(OUT + "/T7_universe_elig.npz", E_ts=E_ts, symbols=np.array(SYM), elig_C0=elig["C0"], elig_NW=elig["NW"], n_m=n_m,
                    n_sel_C0=n_sel["C0"], n_sel_NW=n_sel["NW"], has_panel_row=has_row, umask_applied=mask_applied,
                    rec_ts_C0=np.load(OUT + "/rec_ts_C0.npy"), rec_ts_NW=np.load(OUT + "/rec_ts_NW.npy"), qvk_first_ts=first, qvk_last_ts=last)
REC["output"] = {"path": OUT + "/T7_universe_elig.npz", "sha256": sha(OUT + "/T7_universe_elig.npz")}
json.dump(REC, open(OUT + "/RECEIPT_T7_universe_pod2.json", "w"), indent=1)
print(json.dumps({"crosscheck": XC, "per_year": REC["per_year"], "out_sha": REC["output"]["sha256"]}, indent=1))
