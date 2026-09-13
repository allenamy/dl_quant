"""l2_b_selftest.py — PREREG_L2 §8 guards that do not need model fits: G-SF (shuffle-future, bitwise, with negative controls),
G-PC (synthetic positive / variance / noise controls through the SAME statistic and reading code as the judge), G-ALIGN (Stage A S2
repeated on the full metrics panel). Reads out/L2_B_data_s42.npz (sha from RECEIPT_L2_B_build.json) only for the row structure (anchors,
days, years) and, in G-PC, targets that are first permuted within anchor (the real association is destroyed before any statistic).
Writes RECEIPT_L2_B_selftest.json; asserts every guard after the receipt is written."""
import os, sys, time, json, copy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C
import l2_b_common as B

T_START = time.time()
envrep = C.check_env(sys.argv); pre = B.check_prereg()
st0 = C.sysstate(); assert st0["gpu"].replace(" ", "") == "0%,2MiB", st0["gpu"]
DEV = ("l2_common.py", "l2_b_common.py", "l2_b_selftest.py", "run_l2.sh")
rep = dict(device="l2_b_selftest.py", device_sha256={f: C.sha256(os.path.join(C.L2, "devices", f)) for f in DEV}, prereg=pre, env=envrep, sys_before=st0)
brc = json.load(open(os.path.join(C.L2, "receipts", "RECEIPT_L2_B_build.json")))
DATA = brc["per_seed"]["42"]["out"]; assert C.sha256(DATA) == brc["per_seed"]["42"]["out_sha256"]
rep["inputs"] = C.input_shas(check=True); rep["build_receipt_sha256"] = C.sha256(os.path.join(C.L2, "receipts", "RECEIPT_L2_B_build.json"))
D = B.load_core()
Zd = np.load(DATA); I = Zd["i"].astype(np.int64); Nn = Zd["n"].astype(np.int64); E = Zd["E"]; YR = Zd["year"].astype(np.int64); DAYv = Zd["day"]
syms = sorted({D["SYM"][n] for n in np.unique(Nn)})
MET, _ = B.load_metrics(syms)
GATES = {}

# ------------------------------------------------------------------ G-SF
rng = np.random.default_rng([20260913, 60])
cand = np.unique(I[(YR >= 2023)])
rows_sf = np.sort(rng.choice(cand, size=60, replace=False))
sf = dict(rows=[int(x) for x in rows_sf], identical=0, total=0, neg={"R3D": 0, "DOI1H": 0, "TKR24": 0, "RN8": 0}, neg_tested={"R3D": 0, "DOI1H": 0, "TKR24": 0, "RN8": 0})
for i in rows_sf:
    sel = I == i; nsel = Nn[sel]; Ei = E[sel]; k = int(i) + C.META_OFF; j = int(i); t0 = int(Ei[0]) - 600
    args = lambda Y, FN, IV, FE, TB, MT: B.features_rows(np.full(nsel.size, i), nsel, Ei, Y, FN, IV, FE, TB, D["FIRST_DAY"], MT, D["SYM"])
    F0 = args(D["Y"], D["FN"], D["IV"], D["FE"], D["TB24"], MET)
    r2 = np.random.default_rng([20260913, 61, int(i)])
    Y2 = D["Y"].copy(); Y2[k:] = r2.normal(0, 0.05, Y2[k:].shape)
    FN2 = D["FN"].copy(); FN2[j + 1:] = r2.normal(0, 1e-3, FN2[j + 1:].shape)
    IV2 = D["IV"].copy(); IV2[j + 1:] = r2.choice([1.0, 4.0, 8.0], IV2[j + 1:].shape)
    FE2 = D["FE"].copy(); FE2[j + 1:] = r2.normal(0, 1e-3, FE2[j + 1:].shape)
    TB2 = D["TB24"].copy(); TB2[j + 1:] = r2.random(TB2[j + 1:].shape)
    MET2 = {}
    for n in np.unique(nsel):
        m = MET.get(D["SYM"][n])
        if m is None:
            continue
        mm = {kk: v.copy() for kk, v in m.items()}; fut = mm["dt"] > t0
        for kk in ("OIQ", "TOP", "GLB", "TKR"):
            mm[kk][fut] = r2.random(int(fut.sum())) * 1e6
        MET2[D["SYM"][n]] = mm
    MET2full = dict(MET); MET2full.update(MET2)
    F1 = args(Y2, FN2, IV2, FE2, TB2, MET2full)
    sf["total"] += 1; sf["identical"] += int(np.array_equal(F0, F1, equal_nan=True))
    # negative controls: perturb data at or before E_i
    Y3 = D["Y"].copy(); Y3[k - 1] = Y3[k - 1] + 0.01
    F3 = args(Y3, D["FN"], D["IV"], D["FE"], D["TB24"], MET)
    fin = np.isfinite(F0[:, 4]); sf["neg_tested"]["R3D"] += 1; sf["neg"]["R3D"] += int(fin.any() and not np.array_equal(F0[fin, 4], F3[fin, 4]))
    TB3 = D["TB24"].copy(); TB3[j] = TB3[j] + 0.01
    F4 = args(D["Y"], D["FN"], D["IV"], D["FE"], TB3, MET)
    fin = np.isfinite(F0[:, 3]); sf["neg_tested"]["TKR24"] += 1; sf["neg"]["TKR24"] += int(fin.any() and not np.array_equal(F0[fin, 3], F4[fin, 3]))
    FN3 = D["FN"].copy(); FN3[j] = np.where(np.isfinite(FN3[j]), FN3[j] + 1e-4, FN3[j])
    F5 = args(D["Y"], FN3, D["IV"], D["FE"], D["TB24"], MET)
    sf["neg_tested"]["RN8"] += 1; sf["neg"]["RN8"] += int(not np.array_equal(F0[:, 8], F5[:, 8]))
    MET3 = dict(MET); changed = False
    for n in np.unique(nsel):
        m = MET.get(D["SYM"][n])
        if m is None:
            continue
        hit = m["dt"] == t0
        if hit.any():
            mm = {kk: v.copy() for kk, v in m.items()}; mm["OIQ"][hit] = mm["OIQ"][hit] * 1.01; MET3[D["SYM"][n]] = mm; changed = True
    if changed:
        F6 = args(D["Y"], D["FN"], D["IV"], D["FE"], D["TB24"], MET3)
        fin = np.isfinite(F0[:, 0]); sf["neg_tested"]["DOI1H"] += 1; sf["neg"]["DOI1H"] += int(fin.any() and not np.array_equal(F0[fin, 0], F6[fin, 0]))
GATES["G_SF_bitwise"] = sf["identical"] == sf["total"] == 60
GATES["G_SF_negative_controls"] = all(sf["neg"][k] == sf["neg_tested"][k] and sf["neg_tested"][k] > 0 for k in sf["neg"])
rep["G_SF"] = sf
print("G-SF %s" % json.dumps(sf), flush=True)

# ------------------------------------------------------------------ G-PC (synthetic scores; targets permuted within anchor first)
rA = Zd["rA"]; test = YR >= 2023
idx, a, sizes, uniq = B.anchor_index(I, test & np.isfinite(rA))
keep = sizes[a] >= B.MIN_ANCHOR
idx = idx[keep]
idx, a, sizes, uniq = B.anchor_index(I, np.isin(np.arange(I.size), idx))
g = np.random.default_rng([20260913, 62])
perm_s = -1e4 * rA[idx]
key = g.random(idx.size); o = np.lexsort((key, a)); base = np.lexsort((np.arange(idx.size), a))
sp = np.empty(idx.size); sp[base] = perm_s[o]                   # within-anchor permutation of real short P&L
col = Nn[idx]; days_a = DAYv[idx][np.r_[0, np.cumsum(sizes)[:-1]]]; yrs_a = YR[idx][np.r_[0, np.cumsum(sizes)[:-1]]]
anc_mean = np.bincount(a, sp, sizes.size) / sizes
dev = sp - anc_mean[a]
sd_a = np.sqrt(np.bincount(a, dev ** 2, sizes.size) / sizes); zdev = dev / np.maximum(sd_a[a], 1e-12)
ud, dinv = np.unique(days_a, return_inverse=True); Cm = B.draw_counts(ud.size)


def cell_stats(score, base_score, tgt):
    top, bot, _ = B.decile_sets(score, a, sizes, col)
    Dv, Hv = B.anchor_stats(tgt, a, sizes, top, bot)
    Mv = B.anchor_median_stat(tgt, a, sizes, top)
    topb, botb, _ = B.decile_sets(base_score, a, sizes, col)
    Db, _ = B.anchor_stats(tgt, a, sizes, topb, botb)
    cnt = np.bincount(dinv, None, ud.size)
    out = dict(G=float(Dv.mean()), H=float(Hv.mean()), G_med=float(Mv.mean()), dG=float(Dv.mean() - Db.mean()),
               G_ci=B.boot_ci(Cm, np.bincount(dinv, Dv, ud.size), cnt), H_ci=B.boot_ci(Cm, np.bincount(dinv, Hv, ud.size), cnt),
               TB_ci=B.boot_ci(Cm, np.bincount(dinv, Dv - Hv, ud.size), cnt), dG_ci=B.boot_ci(Cm, np.bincount(dinv, Dv - Db, ud.size), cnt),
               G_years={str(y): (float(Dv[yrs_a == y].mean()) if (yrs_a == y).any() else None) for y in B.TEST_YEARS}, z=-99.0, q05=0.0,
               shift_peak_forward_is_0=True)
    conds, first = B.reading(out)
    out.update(conds=conds, first_fail=first)
    return out


noise = g.normal(size=idx.size)
# (i) direction: score rises when the (permuted) short P&L falls; strength tuned to within-anchor rank IC ≈ 0.05
p_dir = -zdev * 0.06 + noise
# (ii) variance-only: target symmetrised within anchor (dev × Rademacher) so the tails carry no mean; score = |dev| + noise
sp_sym = anc_mean[a] + dev * g.choice([-1.0, 1.0], size=idx.size)
p_var = np.abs(zdev) + 0.5 * g.normal(size=idx.size)
p_noise = g.normal(size=idx.size)
pc = dict(direction=cell_stats(p_dir, p_noise, sp), variance=cell_stats(p_var, p_noise, sp_sym), noise=cell_stats(p_noise, g.normal(size=idx.size), sp))
ic = np.array([np.corrcoef(np.argsort(np.argsort(p_dir[a == q])), np.argsort(np.argsort(-sp[a == q])))[0, 1] for q in range(0, sizes.size, 25)])
pc["direction_rank_ic_sampled_anchors"] = float(np.nanmean(ic))
GATES["G_PC_direction_passes_C1_C4"] = all(pc["direction"]["conds"][c] for c in ("C1", "C2", "C3", "C4"))
GATES["G_PC_variance_not_pass"] = not all(pc["variance"]["conds"][c] for c in ("C1", "C2", "C3", "C4"))
GATES["G_PC_noise_fails_C1"] = not pc["noise"]["conds"]["C1"]
rep["G_PC"] = pc
print("G-PC dir %s | var %s | noise %s | ic %.4f" % (pc["direction"]["conds"], pc["variance"]["first_fail"], pc["noise"]["first_fail"], pc["direction_rank_ic_sampled_anchors"]), flush=True)

# ------------------------------------------------------------------ G-ALIGN (full metrics, anchor-level S2)
SH = list(range(-3, 4)); num = {h: 0.0 for h in SH}; dx = {h: 0.0 for h in SH}; dy = {h: 0.0 for h in SH}; n_used = 0
un = np.unique(Nn)
for n in un:
    m = MET.get(D["SYM"][n])
    if m is None:
        continue
    sel = np.nonzero(Nn == n)[0]; Es = E[sel]; js = I[sel]
    okj = (js - 3 >= 0) & (js + 3 < C.N_REC)
    sel = sel[okj]; Es = Es[okj]; js = js[okj]
    if sel.size < 3:
        continue
    lo = int(m["dt"].min()); hi = int(m["dt"].max()); grid = np.arange(lo, hi + 300, 300)
    val = np.full(grid.size, np.nan); pos = (m["dt"] - lo) // 300
    tk = m["TKR"]; good = np.isfinite(tk) & (tk > 0)
    val[pos[good]] = tk[good] / (1 + tk[good])
    cs = np.concatenate([[0.0], np.cumsum(np.nan_to_num(val))]); cc = np.concatenate([[0], np.cumsum(np.isfinite(val))])
    endi = (Es - 300 - lo) // 300 + 1                          # data times (E-24h-5m, E-5m] ⇒ grid indices endi-288 .. endi-1
    st = endi - 288
    okw = (st >= 0) & (endi <= grid.size)
    Mv = np.full(sel.size, np.nan)
    cnt = np.where(okw, cc[np.clip(endi, 0, grid.size)] - cc[np.clip(st, 0, grid.size)], 0)
    sm = np.where(okw, cs[np.clip(endi, 0, grid.size)] - cs[np.clip(st, 0, grid.size)], 0.0)
    good = okw & (cnt >= 280); Mv[good] = sm[good] / cnt[good]
    Fv = {h: D["TB24"][js + h, n] for h in SH}
    ok = np.isfinite(Mv) & np.all([np.isfinite(Fv[h]) for h in SH], axis=0)
    if ok.sum() < 3:
        continue
    dd = DAYv[sel][ok]; ud2, inv2 = np.unique(dd, return_inverse=True); cnt2 = np.bincount(inv2)
    gmask = cnt2[inv2] >= 3
    if gmask.sum() < 3:
        continue
    x = Mv[ok][gmask]; inv3 = np.unique(inv2[gmask], return_inverse=True)[1]
    x = x - (np.bincount(inv3, x) / np.bincount(inv3))[inv3]
    n_used += int(x.size)
    for h in SH:
        v = Fv[h][ok][gmask]; v = v - (np.bincount(inv3, v) / np.bincount(inv3))[inv3]
        num[h] += float((x * v).sum()); dx[h] += float((x * x).sum()); dy[h] += float((v * v).sum())
S2 = {h: num[h] / np.sqrt(dx[h] * dy[h]) for h in SH}
GATES["G_ALIGN_peak_0"] = max(SH, key=lambda h: S2[h]) == 0
rep["G_ALIGN"] = dict(rows=n_used, corr_by_offset={str(h): S2[h] for h in SH})
print("G-ALIGN %s rows %d" % ({h: round(S2[h], 4) for h in SH}, n_used), flush=True)

st1 = C.sysstate(); GATES["gpu_idle_after"] = st1["gpu"].replace(" ", "") == "0%,2MiB"
rep.update(gates=GATES, sys_after=st1, wall_s=round(time.time() - T_START, 1))
C.jdump(rep, os.path.join(C.L2, "receipts", "RECEIPT_L2_B_selftest.json"))
assert all(GATES.values()), ("SELFTEST GATE FAILED", GATES)
print("SUMMARY l2_b_selftest OK gates=%s wall=%.0fs" % (json.dumps(GATES), rep["wall_s"]), flush=True)
