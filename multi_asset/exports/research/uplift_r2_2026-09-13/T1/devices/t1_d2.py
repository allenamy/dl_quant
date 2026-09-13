#!/usr/bin/env python3
"""t1_d2.py — pod2 (PREREG_T1 §2.4 D2, GATE D2; AMENDMENT 2 member set for the fund signal-level share).
Deployed combo weights (read-only copies of ~/wide_shadow/state/target_live/<E>.json, uploaded to T1/private/target_live) scored
through the x0910 ACCOUNTING meta y4 (RAW compounded, no expm1) and the x0910 panel carry c4 = f_fund_now*4/IVf.
Primary (PREREG): price = sum(w*y4)*1e4 / sum|w|, NaN-return names booked 0 (their |w| reported as unknown_gross);
carry = sum(w*c4)*1e4 / sum|w| (positive = paid). r6 variant (finite-set renormalised price) computed for GATE D2.
Per anchor also: long/short split, deep-negative-funding short cohort (w<0 and RN8<=-0.0010), the 15 stale-span names, non-8h names
(panel f_fund_iv at E != 8), and the fund leg's signal-level unit rank book share of the 15 names (device legs() semantics, causal eligibility).
"""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import rankdata
R = "/workspace/uplift_r2_2026-09-13/T1"
PREREG_SHA = "9548214267b5a44900ba90fee6b2fb2bbeb77964d562628b77678b16c56777f6"; AMEND_SHA = "a7628a7268cad50976470e5b6334c9086af9805bf786dac0ed51f496374da373"; AMEND2_SHA = "12b262fd5b5ec47b7741c10b500baa9bc726cfc873ef7c5b07edf39b897e7207"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
assert sha(R + "/PREREG_T1_edge_diagnosis_2026-09-13.md") == PREREG_SHA and sha(R + "/PREREG_AMENDMENT_1_T1_2026-09-13.md") == AMEND_SHA and sha(R + "/PREREG_AMENDMENT_2_T1_2026-09-13.md") == AMEND2_SHA
MX = "/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz"; PX = "/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"
UMP = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"; TL = R + "/private/target_live"; R6ROWS = R + "/private/j1_recon_rows.json"
STALE15 = ["ANKRUSDT", "AXSUSDT", "ENJUSDT", "FLOWUSDT", "GMTUSDT", "IOSTUSDT", "KAVAUSDT", "MASKUSDT", "ONTUSDT", "RVNUSDT", "SKLUSDT", "STGUSDT", "XTZUSDT", "ZILUSDT", "ZRXUSDT"]
LIVE0 = 1787716800; W5_HI = 1789056000
t0 = time.time()
ZX = np.load(MX, allow_pickle=True); E = ZX["E_ts"].astype(np.int64); Y = ZX["y4"].astype(np.float64); QVK = ZX["qvk"]
PXz = np.load(PX, allow_pickle=True); tsP = PXz["ts"].astype(np.int64); SYM = [str(s) for s in PXz["symbols"]]; sidx = {s: i for i, s in enumerate(SYM)}
FN = PXz["f_fund_now"].astype(np.float64); IV = PXz["f_fund_iv"].astype(np.float64); FE = PXz["f_fund_ema_v1"].astype(np.float64)
IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0); RN8 = FN * (8.0 / IVf); C4 = np.nan_to_num(FN, nan=0.0) * (4.0 / IVf)
UM = np.load(UMP, allow_pickle=True); umts = UM["ts"].astype(np.int64); umask = np.asarray(UM["mask"]); umap = {int(t): k for k, t in enumerate(umts)}; um_last = int(umts.max())
emap = {int(t): i for i, t in enumerate(E)}; prow = {int(t): j for j, t in enumerate(tsP)}
stale_idx = np.array([sidx[s] for s in STALE15 if s in sidx]); assert len(stale_idx) == 15, ("stale names not all on the 829 axis", len(stale_idx))
files = sorted(f for f in os.listdir(TL) if f.endswith(".json"))
INPUTS = {p: sha(p) for p in (MX, PX, UMP)}; INPUTS["target_live_files"] = {f: sha(TL + "/" + f) for f in files}
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
COLS = ["A", "k_meta", "j_panel", "gross", "unmapped_share", "unknown_ret_share", "price", "price_r6", "carry", "gross_L", "gross_S", "price_L", "price_S", "carry_L", "carry_S",
        "coh_gross", "coh_price", "coh_carry", "st15_gross", "st15_price", "st15_carry", "non8h_gross", "non8h_price", "non8h_carry", "fundsig_st15_absz_share", "fundsig_st15_lr0", "fundsig_lr0",
        "producer_is_combo", "n_names"]
rows = []; WMAT = []
for f in files:
    d = json.load(open(TL + "/" + f)); A = int(d["anchor_ts"])
    if A < LIVE0: continue
    k = emap.get(A); j = prow.get(A)
    if k is None or j is None: continue
    w = np.zeros(829); miss = 0.0; tot = 0.0
    for s, x in d["weights"].items():
        tot += abs(float(x)); jj = sidx.get(s)
        if jj is None: miss += abs(float(x)); continue
        w[jj] += float(x)
    r = Y[k]; fin = np.isfinite(r); nz = np.abs(w) > 0
    if not (fin & nz).any(): continue
    g = np.abs(w).sum(); gfin = np.abs(w[fin & nz]).sum()
    price = float((w[fin] * r[fin]).sum() / g * 1e4); price_r6 = float((w[fin & nz] * r[fin & nz]).sum() / gfin * 1e4)
    carry = float((w * C4[j]).sum() / g * 1e4)
    L = w > 0; S = w < 0; rz = np.nan_to_num(r, nan=0.0)
    coh = S & np.isfinite(RN8[j]) & (RN8[j] <= -0.0010)
    st = np.zeros(829, bool); st[stale_idx] = True
    n8 = np.isfinite(IV[j]) & (IV[j] != 8.0)
    def part(mask): return (float(np.abs(w[mask]).sum() / g), float((w[mask] * rz[mask]).sum() / g * 1e4), float((w[mask] * C4[j][mask]).sum() / g * 1e4))
    cg, cp, cc = part(coh); sg, sp, scar = part(st); ng, npr, ncar = part(n8)
    # fund signal-level unit rank book (legs() semantics, AMENDMENT 2 member set, causal eligibility)
    _q = np.nan_to_num(QVK[k], nan=-1.0); m = np.sort(np.where(_q > -0.5)[0])
    u = umap.get(A)
    if u is not None: m = m[umask[u][m]]
    elif A > um_last: m = m[umask[umap[um_last]][m]]
    ok = np.isfinite(Y[k - 1, m]); z = np.nan_to_num(xz(FE[j, :])[m]); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
    gz = np.abs(z).sum(); zz = np.zeros(829); zz[m] = z / gz if gz > 1e-9 else 0.0
    rows.append([A, k, j, g, miss / tot if tot > 0 else 0.0, float(np.abs(w[~fin & nz]).sum() / g), price, price_r6, carry,
                 float(np.abs(w[L]).sum() / g), float(np.abs(w[S]).sum() / g), float((w[L] * rz[L]).sum() / g * 1e4), float((w[S] * rz[S]).sum() / g * 1e4),
                 float((w[L] * C4[j][L]).sum() / g * 1e4), float((w[S] * C4[j][S]).sum() / g * 1e4), cg, cp, cc, sg, sp, scar, ng, npr, ncar,
                 float(np.abs(zz[st]).sum()), float((zz[st] * rz[st]).sum() * 1e4), float((zz * rz).sum() * 1e4),
                 float("combo_stage" in str(d.get("producer"))), float(nz.sum())])
    WMAT.append(w.astype(np.float32))
D = np.array(rows); W = np.stack(WMAT)
print("D2 anchors", D.shape, time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(D[0, 0]))), "..", time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(D[-1, 0]))), flush=True)
# ---------------- GATE D2 ----------------
r6 = json.load(open(R6ROWS))["rows"]; r6map = {r["A"]: r["D2"]["price_y4meta"] for r in r6 if "D2" in r}
cmp = [(int(a), p6, r6map[int(a)]) for a, p6 in zip(D[:, 0], D[:, 7]) if int(a) in r6map and int(a) <= W5_HI]
diffs = np.array([abs(a - b) for _, a, b in cmp]) if cmp else np.array([np.inf])
w5 = np.array([b for a, _, b in cmp])
GD = dict(n_compared=len(cmp), maxabs_per_anchor_price_r6variant=float(diffs.max()), r6_mean_on_compared=float(w5.mean()) if len(w5) else None,
          t1_mean_on_compared=float(np.mean([a for _, a, _ in cmp])) if cmp else None, PASS=bool(len(cmp) > 0 and diffs.max() <= 1e-6))
print("GATE_D2", json.dumps(GD), flush=True)
out = R + "/receipts/T1_d2.npz"
np.savez_compressed(out, cols=np.array(COLS), D=D, W=W, symbols=np.array(SYM))
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, amendment1_sha256=AMEND_SHA, amendment2_sha256=AMEND2_SHA, inputs=INPUTS, r6_rows_sha256=sha(R6ROWS),
          gate_D2=GD, n=int(D.shape[0]), first=int(D[0, 0]), last=int(D[-1, 0]), max_unknown_ret_share=float(D[:, 5].max()), max_unmapped_share=float(D[:, 4].max()),
          out=out, out_sha256=sha(out), env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T1_d2.json", "w"), indent=1, default=str)
print("DONE_t1_d2", RC["wall_s"])
