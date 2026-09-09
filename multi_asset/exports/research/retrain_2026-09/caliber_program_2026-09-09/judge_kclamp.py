"""PREREG_king_clip_label_ablation §4 judge. Frozen: 2025-03-01 -> 2026-08-10 20Z, UTC day-block bootstrap 2000, seed 20260905.
(A) promote  = point>0 AND CI lower>0 on BOTH seeds ; (B) reject = CI upper<0 on both ; (C) otherwise UNDECIDED.
§5: the book layer is judged on the CLIP-CORRECTED P&L series, each arm corrected with ITS OWN smr weights."""
import numpy as np, os, time, calendar, csv, json
HC = "/workspace/review_scratch/health_check"; D = "/workspace/review_scratch/clip_kl"
COLS = ["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C = {c: i for i, c in enumerate(COLS)}
T0 = calendar.timegm((2025, 3, 1, 0, 0, 0)); CUT = calendar.timegm((2026, 8, 10, 20, 0, 0)); APY = 2190
MT = np.load("%s/dev_alt/pod_backup_2026-08-21/wide_fea_hist_meta.npz" % HC, allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); y4 = MT["y4"]; qvk = MT["qvk"]
MEM = np.empty(len(E_ts), dtype=object)
for i in range(len(E_ts)):
    q = np.nan_to_num(qvk[i], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5]
    MEM[i] = np.sort(o[:829]).astype(np.int64)
PW = np.load("%s/dev_alt/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz" % HC, allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
UZ = np.load("%s/masks/umask_UPIT_CRYPTO.npz" % HC, allow_pickle=True)
umap = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"])
UROW = {j: UM[umap[int(t)]] for j, t in enumerate(PW["ts"].astype(np.int64)) if int(t) in umap}
F = np.load("/workspace/review_scratch/clip_flags.npz", allow_pickle=True)
fts = F["E_ts"].astype(np.int64); has = F["has"]; syms = [str(s) for s in F["symbols"]]
gi = {int(t): i for i, t in enumerate(fts)}; ei = {int(t): i for i, t in enumerate(E_ts)}
CA = {}
def closes(s, ym):
    k = (s, ym)
    if k in CA: return CA[k]
    p = os.path.join(D, "%s_%s.csv" % (s, ym)); d = {}
    if os.path.exists(p):
        for r in csv.reader(open(p)):
            try: d[int(r[0]) // 1000] = float(r[4])
            except Exception: pass
    CA[k] = d; return d
def close_at(s, t):
    ym = time.strftime("%Y-%m", time.gmtime(t)); c = closes(s, ym)
    if t in c: return c[t]
    y, m = map(int, ym.split("-")); m -= 1
    if m == 0: y, m = y - 1, 12
    return closes(s, "%04d-%02d" % (y, m)).get(t)
def true_y(s, t):
    a = close_at(s, t); b = close_at(s, t - 14400)
    return None if (a is None or b is None or b <= 0) else a / b - 1.0
def smr_of(sm):
    nz = np.abs(sm) > 1e-12; r = sm.copy()
    if nz.any():
        r[nz] -= r[nz].mean(); g0 = np.abs(sm).sum(); g1 = np.abs(r).sum()
        if g1 > 1e-12: r *= g0 / g1
    return r
def mem_at(t):
    i = ei[int(t)]; j = pw_row.get(int(t)); m = MEM[i]
    if j is not None and j in UROW: m = m[UROW[j][m]]
    return i, m
def load(tag):
    A = np.load("%s/dev_alt/probe_artifacts/w10_ablation_series_%s.npz" % (HC, tag), allow_pickle=True)
    R = A["d30_n2_c42_rec"]; W = A["d30_n2_c42_W"]; ts = R[:, 0].astype(np.int64)
    g = R[:, C["net_ex"]] / R[:, C["gross_total"]]
    err = []
    for p, t in enumerate(ts):
        i, m = mem_at(t); smr = smr_of(W[p].astype(np.float64))
        yv = np.nan_to_num(y4[i, m].astype(np.float64), nan=0.0)
        err.append(abs(float((smr[m] * yv).sum() * 1e4) - float(R[p, C["pnl_ex"]])))
    assert max(err) < 1e-3, "%s: smr reconstruction failed (max %.3e)" % (tag, max(err))
    gc = g.copy()
    for p, t in enumerate(ts):
        t = int(t)
        if t not in gi: continue
        i, m = mem_at(t); smr = smr_of(W[p].astype(np.float64)); G = float(R[p, C["gross_total"]])
        if G <= 0: continue
        hit = has[gi[t]][m] & (np.abs(smr[m]) > 0)
        if not hit.any(): continue
        d = 0.0
        for k in np.where(hit)[0]:
            jj = m[k]; ty = true_y(syms[jj], t); ry = float(y4[i, jj])
            if ty is None or not np.isfinite(ry): continue
            d += smr[jj] * (ty - ry)
        gc[p] = g[p] + d / G * 1e4
    return ts, g, gc, R
rng = np.random.default_rng(20260905)
def boot(d, days):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    S = np.bincount(inv, weights=d, minlength=nd); N = np.bincount(inv, minlength=nd)
    idx = rng.integers(0, nd, size=(2000, nd)); mn = S[idx].sum(1) / N[idx].sum(1)
    return float(d.mean()), float(np.percentile(mn, 2.5)), float(np.percentile(mn, 97.5)), float((mn > 0).mean())
if __name__ == "__main__":
    A = {}
    for s in ("42", "2027"):
        for arm in ("OLD", "CLAMP", "DROP138"):
            for k in ("dyn", "fix"):
                tag = "KCL_%s_%s_s%s" % (arm, k, s)
                A[(arm, k, s)] = load(tag)
                print("loaded %s (self-check ok)" % tag, flush=True)
    out = {}
    print("\n== PREREG §4 book layer | frozen 2025-03-01 -> 2026-08-10 20Z | CLIP-CORRECTED series ==")
    print("%-22s %-5s %-6s | %9s %20s %6s | %s" % ("contrast", "seat", "seed", "delta", "CI95", "P>0", "levels OLD -> arm"))
    for arm in ("CLAMP", "DROP138"):
        for k in ("dyn", "fix"):
            for s in ("42", "2027"):
                ts0, g0, gc0, R0 = A[("OLD", k, s)]; ts1, g1, gc1, R1 = A[(arm, k, s)]
                assert ts0.shape == ts1.shape and (ts0 == ts1).all(), "axis mismatch"
                m = (ts0 >= T0) & (ts0 <= CUT); dd = (gc1 - gc0)[m]; days = ts0[m] // 86400
                mu, lo, hi, p = boot(dd, days)
                ddr = (g1 - g0)[m]; mur, lor, hir, pr = boot(ddr, days)
                out["%s|%s|%s" % (arm, k, s)] = {"delta_corrected": mu, "ci95": [lo, hi], "p_gt0": p,
                                                 "delta_recorded": mur, "ci95_recorded": [lor, hir],
                                                 "level_OLD": float(gc0[m].mean()), "level_arm": float(gc1[m].mean()), "n": int(m.sum())}
                print("%-22s %-5s %-6s | %+9.4f [%+8.4f,%+8.4f] %6.3f | %+7.4f -> %+7.4f  (uncorrected Δ %+9.4f [%+8.4f,%+8.4f])"
                      % ("%s - OLD" % arm, k, s, mu, lo, hi, p, gc0[m].mean(), gc1[m].mean(), mur, lor, hir))
    def verdict(arm, k):
        r = [out["%s|%s|%s" % (arm, k, s)] for s in ("42", "2027")]
        if all(x["delta_corrected"] > 0 and x["ci95"][0] > 0 for x in r): return "(A) PROMOTE"
        if all(x["ci95"][1] < 0 for x in r): return "(B) REJECT"
        return "(C) UNDECIDED"
    print("\n== VERDICTS (frozen §4) ==")
    for arm in ("CLAMP", "DROP138"):
        for k in ("dyn", "fix"):
            print("  %-6s vs OLD, %-3s seat : %s" % (arm, k, verdict(arm, k)))
    json.dump(out, open("/workspace/review_scratch/king_clamp_ablation/JUDGE.json", "w"), indent=1)
