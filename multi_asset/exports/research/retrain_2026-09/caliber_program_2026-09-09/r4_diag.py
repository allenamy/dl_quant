"""R4 diagnosis: does the raw-target replay differ from the published arm in BOOK BEHAVIOUR (weights / stops / seats) or only in
accounting? (i) weight-matrix and fires equality per anchor; (ii) fixed-weight accounting with chain targets vs the patch table."""
import numpy as np, calendar, time
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}; CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); APY = 2190; H = "/workspace/review_scratch/health_check"
def T(s): return time.strftime("%F %H:%MZ", time.gmtime(int(s)))
MR = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_raw.npz", allow_pickle=True); MO = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz", allow_pickle=True)
mt = MR["E_ts"].astype(np.int64); y4r = MR["y4"]; y4o = MO["y4"]; qvk = MO["qvk"]; mi = {int(t): i for i, t in enumerate(mt)}
MEM = np.empty(len(mt), dtype=object)
for i in range(len(mt)):
    q = np.nan_to_num(qvk[i], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5]; MEM[i] = np.sort(o[:829]).astype(np.int64)
PW = np.load("%s/dev_alt/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz" % H, allow_pickle=True); pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
UZ = np.load("%s/masks/umask_UPIT_CRYPTO.npz" % H, allow_pickle=True); umap = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"]); UROW = {j: UM[umap[int(t)]] for j, t in enumerate(PW["ts"].astype(np.int64)) if int(t) in umap}
def mem_at(t):
    i = mi[int(t)]; j = pw_row.get(int(t)); m = MEM[i]
    if j is not None and j in UROW: m = m[UROW[j][m]]
    return i, m
def smr_of(sm):
    nz = np.abs(sm) > 1e-12; r = sm.copy()
    if nz.any():
        r[nz] -= r[nz].mean(); g0 = np.abs(sm).sum(); g1 = np.abs(r).sum()
        if g1 > 1e-12: r *= g0 / g1
    return r
REFTAB = {"42": {"2022": 0.0717, "2025": 0.5823, "2024-26": 1.2580, "full": 0.6013}, "2027": {"2022": 0.0717, "2025": 0.7097, "2024-26": 1.3225, "full": 0.6437}}
for s in ("42", "2027"):
    A = np.load("%s/dev_alt/probe_artifacts/w10_ablation_series_M1_UCRYPTO_prod_s%s_ccal.npz" % (H, s), allow_pickle=True); B = np.load("%s/dev_raw/probe_artifacts/w10_ablation_series_RAW_M1_UCRYPTO_s%s.npz" % (H, s), allow_pickle=True)
    Ra, Rb = A["d30_n2_c42_rec"], B["d30_n2_c42_rec"]; Wa, Wb = A["d30_n2_c42_W"], B["d30_n2_c42_W"]; ts = Ra[:, 0].astype(np.int64); assert (ts == Rb[:, 0].astype(np.int64)).all()
    dW = np.abs(Wa.astype(np.float64) - Wb.astype(np.float64)).max(1); chW = np.where(dW > 0)[0]
    print("== seed %s == weight matrix differs at %d/%d anchors (first %s), fires total old %d new %d, w3_king mean old %.4f new %.4f" % (s, len(chW), len(ts), T(ts[chW[0]]) if len(chW) else "-", int(Ra[:, C["fires"]].sum()), int(Rb[:, C["fires"]].sum()), Ra[:, C["w3_king"]].mean(), Rb[:, C["w3_king"]].mean()))
    # (ii) fixed-weight accounting: OLD arm's smr x raw target, per gross
    g_fix = np.zeros(len(ts)); g_old = Ra[:, C["net_ex"]] / Ra[:, C["gross_total"]]
    for p, t in enumerate(ts):
        i, m = mem_at(t); smr = smr_of(Wa[p].astype(np.float64)); G = float(Ra[p, C["gross_total"]])
        if G <= 0: g_fix[p] = g_old[p]; continue
        d = float((smr[m] * (np.nan_to_num(y4r[i, m].astype(np.float64)) - np.nan_to_num(y4o[i, m].astype(np.float64)))).sum() * 1e4)
        g_fix[p] = g_old[p] + d / G
    yr = np.array([time.gmtime(int(v)).tm_year for v in ts]); m_cut = ts <= CUT
    for w, sel in (("2022", yr == 2022), ("2025", yr == 2025), ("2024-26", ts >= calendar.timegm((2024, 1, 1, 0, 0, 0))), ("full", np.ones(len(ts), bool))):
        sel = sel & m_cut; v = g_fix[sel]; vb = (Rb[:, C["net_ex"]] / Rb[:, C["gross_total"]])[sel]
        print("  %-8s fixed-weight chain accounting %+.4f (S %.2f) | patch-table %+.4f | behaviour-inclusive replay %+.4f | recorded %+.4f" % (w, v.mean(), v.mean() / v.std(ddof=1) * np.sqrt(APY), REFTAB[s][w], vb.mean(), g_old[sel].mean()))
