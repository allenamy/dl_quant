#!/usr/bin/env python3
"""t1_lags.py — pod2 (PREREG_T1 §6 H3, GATE LAG0).
Signal-level lag profiles LR_l(i, h), h = 0..23, for legs king / fund / f10 (s42, s2027), unit-gross rank books built exactly as
w10_sleeve legs(): z = nan_to_num(xz(score)) (fund: rank in the 829 base of f_fund_ema_v1), z[~ok] = 0 with CAUSAL eligibility
ok = isfinite(y4[i-1, m]) (r18 N2), z -= mean(z[ok]), g = sum|z|; LR(i,h) = sum(z/g * nan_to_num(y4[i+h, m])) * 1e4.
Returns from the x0910 accounting meta (RAW compounded). Umask: device semantics; rows after the mask's last row carry it forward.
GATE LAG0: h=0 king / fund series equal the NW_s42 arm's archived legs_king / legs_fund (R18_ELIG=1) to 1e-9 on the arm's legs_ts.
"""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import rankdata
R = "/workspace/uplift_r2_2026-09-13/T1"
PREREG_SHA = "9548214267b5a44900ba90fee6b2fb2bbeb77964d562628b77678b16c56777f6"; AMEND_SHA = "a7628a7268cad50976470e5b6334c9086af9805bf786dac0ed51f496374da373"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
assert sha(R + "/PREREG_T1_edge_diagnosis_2026-09-13.md") == PREREG_SHA and sha(R + "/PREREG_AMENDMENT_1_T1_2026-09-13.md") == AMEND_SHA
AMEND2_SHA = "12b262fd5b5ec47b7741c10b500baa9bc726cfc873ef7c5b07edf39b897e7207"; assert sha(R + "/PREREG_AMENDMENT_2_T1_2026-09-13.md") == AMEND2_SHA
MX = "/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz"; PX = "/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"
UMP = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"; SLOWP = "/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
TGP = "/workspace/dlw_v4raw/data/dlw_targets.npz"; F10D = "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds"
NWARM = R + "/arms/NW_s42.npz"
INPUTS = {p: sha(p) for p in (MX, PX, UMP, SLOWP, TGP, F10D + "/f10_A0_s42.npy", F10D + "/f10_A0_s2027.npy", NWARM)}
t0 = time.time()
ZX = np.load(MX, allow_pickle=True); E = ZX["E_ts"].astype(np.int64); QVK = ZX["qvk"]; Y = ZX["y4"].astype(np.float64); nA = len(E)   # AMENDMENT 2: members = finite qvk (MEMBERS_TOPN=829), not meta members
PXz = np.load(PX, allow_pickle=True); tsP = PXz["ts"].astype(np.int64); SYM = [str(s) for s in PXz["symbols"]]; FE = PXz["f_fund_ema_v1"].astype(np.float64)
prow = {int(t): j for j, t in enumerate(tsP)}
UM = np.load(UMP, allow_pickle=True); umts = UM["ts"].astype(np.int64); umask = np.asarray(UM["mask"]); umap = {int(t): k for k, t in enumerate(umts)}; um_last = int(umts.max())
SLOW = np.load(SLOWP); assert SLOW.shape[1] == 829
TG = np.load(TGP, allow_pickle=True); dts = TG["E_ts"].astype(np.int64); dsy = [str(x) for x in TG["symbols"]]
rmap = {int(t): k for k, t in enumerate(dts)}; cmap = {s: k for k, s in enumerate(dsy)}
cols = np.array([cmap.get(s, -1) for s in SYM], np.int64); okc = cols >= 0
F10 = {}
for sd in ("42", "2027"):
    pd_ = np.load(F10D + "/f10_A0_s%s.npy" % sd)
    arr = np.full((nA, 829), np.nan, np.float32)
    for i in range(nA):
        k = rmap.get(int(E[i]))
        if k is None: continue
        arr[i, okc] = pd_[k, cols[okc]]
    F10[sd] = arr
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
H = 24
LEGS = ["king", "fund", "f10_s42", "f10_s2027"]
LR = {l: np.full((nA, H), np.nan) for l in LEGS}
have = np.zeros(nA, bool); carried = np.zeros(nA, bool)
for i in range(1, nA):
    j = prow.get(int(E[i]))
    if j is None: continue
    _q = np.nan_to_num(QVK[i], nan=-1.0); m = np.sort(np.where(_q > -0.5)[0]).astype(np.int64)   # AMENDMENT 2 (device L77-83 semantics)
    u = umap.get(int(E[i]))
    if u is not None: m = m[umask[u][m]]
    elif int(E[i]) > um_last: m = m[umask[umap[um_last]][m]]; carried[i] = True
    ok = np.isfinite(Y[i - 1, m])
    hmax = min(H, nA - i)
    YY = np.nan_to_num(Y[i:i + hmax][:, m], nan=0.0)
    sc = {"king": SLOW[i, m] if i < SLOW.shape[0] else np.full(len(m), np.nan), "fund": None, "f10_s42": F10["42"][i, m].astype(np.float64), "f10_s2027": F10["2027"][i, m].astype(np.float64)}
    for l in LEGS:
        z = np.nan_to_num(xz(FE[j, :])[m]) if l == "fund" else np.nan_to_num(xz(sc[l]))
        z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
        g = np.abs(z).sum()
        if g > 1e-9:
            LR[l][i, :hmax] = (YY @ (z / g)) * 1e4
        else:
            LR[l][i, :hmax] = 0.0
    have[i] = True
print("lags done", round(time.time() - t0, 1), "s", flush=True)
# ---------------- GATE LAG0 ----------------
A = np.load(NWARM, allow_pickle=True)
lts = A["legs_ts"].astype(np.int64); emap = {int(t): i for i, t in enumerate(E)}
idx = np.array([emap[int(t)] for t in lts])
g_king = float(np.nanmax(np.abs(LR["king"][idx, 0] - A["legs_king"]))); g_fund = float(np.nanmax(np.abs(LR["fund"][idx, 0] - A["legs_fund"])))
nan_king = int(np.isnan(LR["king"][idx, 0]).sum()); nan_fund = int(np.isnan(LR["fund"][idx, 0]).sum())
GL = dict(n=int(len(idx)), maxabs_king=g_king, maxabs_fund=g_fund, nan_king=nan_king, nan_fund=nan_fund, PASS=bool(g_king <= 1e-9 and g_fund <= 1e-9 and nan_king == 0 and nan_fund == 0))
print("GATE_LAG0", json.dumps(GL), flush=True)
out = R + "/receipts/T1_lags.npz"
np.savez_compressed(out, ts=E, have=have, umask_carried=carried, **{"LR_" + l: LR[l] for l in LEGS})
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, amendment1_sha256=AMEND_SHA, amendment2_sha256=AMEND2_SHA, inputs=INPUTS, gate_LAG0=GL, H=H, legs=LEGS, out=out, out_sha256=sha(out),
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T1_lags.json", "w"), indent=1, default=str)
print("DONE_t1_lags", RC["wall_s"])
