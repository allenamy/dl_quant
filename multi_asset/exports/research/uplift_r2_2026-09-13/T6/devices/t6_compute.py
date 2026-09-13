#!/usr/bin/env python3
"""t6_compute.py -- T6 step 2b/3 (local CPU). Implements FAMILY_T6.md §4 exactly (frozen in commit c0ed46c8):
GATE-0 reproduction, GATE-I implementation, GATE-C synthetic controls, then (only if all pass) CSCV-PBO, DSR and nested
walk-forward selection on the frozen member matrices. Writes receipts/RECEIPT_T6_compute.json and prints a SUMMARY line.
Usage: python3 t6_compute.py <env_whitelist_csv> <receipts_dir>
"""
import os, sys, json, time, math, hashlib, calendar, itertools
WHITE = set(x for x in sys.argv[1].split(",") if x); assert WHITE, "non-empty env whitelist required"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
RD = sys.argv[2]
import numpy as np
from scipy import stats
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
ANN = math.sqrt(2190.0); S = 16; NB = 2000; GAMMA = 0.5772156649015329
EXT = json.load(open(os.path.join(RD, "RECEIPT_T6_extract.json")))
assert EXT["family_sha256"] == "7ad53ccec6da11db6e7d9a9beac183d025085087c55ffd3ae6e90a46b2eb32c7"
DATA = {}
for s in ("42", "2027"):
    p = os.path.join(RD, "T6_SERIES_s%s.npz" % s); assert sha(p) == EXT["seeds"][s]["out_sha256"] and EXT["seeds"][s]["gate_X_pass"], ("GATE-X / sha", s)
    Z = np.load(p); DATA[s] = {k: Z[k] for k in Z.files}
TS = DATA["42"]["ts"].astype(np.int64); assert np.array_equal(TS, DATA["2027"]["ts"]) and len(TS) == 10038
def ut(y, m, d, h=0): return calendar.timegm((y, m, d, h, 0, 0))
WF = np.ones(len(TS), bool); WA = WF.copy(); WA[:900] = False
FR = (TS >= ut(2025, 3, 1)) & (TS <= ut(2026, 8, 10, 20)); assert WA.sum() == 9138 and FR.sum() == 3168
DAY = TS // 86400
def SR(x): return float(x.mean() / x.std(ddof=1) * ANN)
def SRcols(X): return X.mean(0) / X.std(0, ddof=1) * ANN
# ------------------------------------------------------------------ GATE-0 reproduction
def idx_of(s, stem):
    w = np.nonzero(DATA[s]["stem"] == stem)[0]; assert len(w) == 1, (s, stem); return int(w[0])
a42 = DATA["42"]["G"][:, idx_of("42", "A0_PWR230k_s42")]; a27 = DATA["2027"]["G"][:, idx_of("2027", "A0_PWR230k_s2027")]
G0 = dict(
    s42_WALPHA_g=(float(a42[WA].mean()), 0.6341957, 5e-7), s42_WALPHA_SR=(SR(a42[WA]), 1.2912, 5e-5),
    s42_WFULL_g=(float(a42.mean()), 0.5608, 5e-5), s42_WFULL_SR=(SR(a42), 1.1062, 5e-5),
    s42_FROZEN_SR=(SR(a42[FR]), 2.93571303735249, 1e-9), s2027_FROZEN_SR=(SR(a27[FR]), 2.9021, 5e-5),
    s2027_WALPHA_g=(float(a27[WA].mean()), 0.6579, 5e-5), s2027_WALPHA_SR=(SR(a27[WA]), 1.3299, 5e-5))
GATE0 = {k: dict(got=v[0], want=v[1], tol=v[2], pass_=bool(abs(v[0] - v[1]) <= v[2])) for k, v in G0.items()}
GATE0_PASS = all(v["pass_"] for v in GATE0.values())
# ------------------------------------------------------------------ CSCV machinery
COMBOS = np.array(list(itertools.combinations(range(S), S // 2)), dtype=np.int64); assert len(COMBOS) == 12870
MEMB = np.zeros((len(COMBOS), S)); MEMB[np.arange(len(COMBOS))[:, None], COMBOS] = 1.0
def blocks(X):
    T = X.shape[0]; drop = T % S; Y = X[drop:]; L = Y.shape[0] // S; assert L * S == Y.shape[0]
    B = Y.reshape(S, L, -1); return B.sum(1), (B ** 2).sum(1), L, drop
def cscv(X, names=None):
    sm, sq, L, drop = blocks(X); N = X.shape[1]
    tot, totq = sm.sum(0), sq.sum(0); n = (S // 2) * L
    isum = MEMB @ sm; isq = MEMB @ sq; osum = tot - isum; osq = totq - isq
    def sr(a, q):
        m = a / n; v = (q - n * m * m) / (n - 1); return m / np.sqrt(v) * ANN
    SRi, SRo = sr(isum, isq), sr(osum, osq)
    nstar = SRi.argmax(1); r = np.arange(len(COMBOS))
    so = SRo[r, nstar]; si = SRi[r, nstar]
    below = (SRo < so[:, None]).sum(1); equal = (SRo == so[:, None]).sum(1)
    rank = below + 0.5 * (equal - 1) + 1.0; omega = rank / (N + 1); lam = np.log(omega / (1 - omega))
    slope, intercept, rr, _, _ = stats.linregress(si, so)
    cnt = np.bincount(nstar, minlength=N); top = np.argsort(-cnt)[:5]
    return dict(N=N, T_used=int(X.shape[0] - drop), dropped_first=int(drop), block_len=int(L), PBO=float((lam <= 0).mean()), median_logit=float(np.median(lam)),
                slope=float(slope), intercept=float(intercept), corr=float(rr), P_oos_loss=float((so < 0).mean()), mean_SR_IS_sel=float(si.mean()), mean_SR_OOS_sel=float(so.mean()),
                top_selected=[dict(member=(str(names[i]) if names is not None else int(i)), count=int(cnt[i]), share=float(cnt[i] / len(COMBOS))) for i in top]), (SRi, SRo, sm, sq, L, drop)
def gate_I(X):
    res, (SRi, SRo, sm, sq, L, drop) = cscv(X); Y = X[drop:]
    rng = np.random.default_rng([20260905, 999]); pick = rng.choice(len(COMBOS), 20, replace=False); mx = 0.0
    for c in pick:
        mask = np.zeros(S, bool); mask[COMBOS[c]] = True
        rows_is = np.concatenate([np.arange(b * L, (b + 1) * L) for b in range(S) if mask[b]]); rows_os = np.concatenate([np.arange(b * L, (b + 1) * L) for b in range(S) if not mask[b]])
        mx = max(mx, float(np.abs(SRcols(Y[rows_is]) - SRi[c]).max()), float(np.abs(SRcols(Y[rows_os]) - SRo[c]).max()))
    equal_blocks = bool(L * S == Y.shape[0])
    return dict(n_combos=int(len(COMBOS)), block_len=int(L), equal_blocks=equal_blocks, max_abs_diff=mx, pass_=bool(mx <= 1e-9 and equal_blocks and len(COMBOS) == 12870))
# ------------------------------------------------------------------ DSR
def psr(sr_pp, T, g3, g4, sr_star):
    den = 1.0 - g3 * sr_pp + (g4 - 1.0) / 4.0 * sr_pp ** 2
    return float(stats.norm.cdf((sr_pp - sr_star) * math.sqrt(T - 1) / math.sqrt(den)))
def sr0(V, N):
    flag = N < 2; N = max(N, 2.0)
    return float(math.sqrt(V) * ((1 - GAMMA) * stats.norm.ppf(1 - 1.0 / N) + GAMMA * stats.norm.ppf(1 - 1.0 / (N * math.e)))), bool(flag)
def dsr(X, names, a0_idx, Ns_extra=(300, 825, 1221)):
    T, N = X.shape; srpp = X.mean(0) / X.std(0, ddof=1); V = float(np.var(srpp, ddof=1))
    C = np.corrcoef(X.T); ev = np.linalg.eigvalsh(C); Neff = float(ev.sum() ** 2 / (ev ** 2).sum())
    out = dict(T=T, N_raw=N, N_eff=Neff, V_SR_pp=V, sd_SR_annual=float(math.sqrt(V) * ANN), SR_annual_min=float(srpp.min() * ANN), SR_annual_median=float(np.median(srpp) * ANN), SR_annual_max=float(srpp.max() * ANN))
    Nset = [("N_eff", Neff), ("N_raw", float(N))] + [("N_%d" % n, float(n)) for n in Ns_extra]
    sel = int(srpp.argmax()); targets = [("SEL", sel), ("A0", a0_idx)] if a0_idx is not None else [("SEL", sel)]
    for tn, k in targets:
        g = X[:, k]; g3 = float(stats.skew(g, bias=False)); g4 = float(stats.kurtosis(g, fisher=False, bias=False)); s = float(srpp[k])
        d = dict(member=str(names[k]), SR_annual=s * ANN, SR_pp=s, skew=g3, kurt=g4, PSR_0=psr(s, T, g3, g4, 0.0), PSR_3=psr(s, T, g3, g4, 3.0 / ANN), rank_in_family=int((srpp > s).sum() + 1))
        for nl, nv in Nset:
            z, fl = sr0(V, nv); d["SR0_annual_" + nl] = z * ANN; d["P_true_SR_gt_0_" + nl] = psr(s, T, g3, g4, z); d["P_true_SR_gt_3_" + nl] = psr(s, T, g3, g4, 3.0 / ANN + z); d["Nfloor_" + nl] = fl
        out[tn] = d
    return out
# ------------------------------------------------------------------ nested walk-forward
_DRAW = {}
def draws(nd):
    if nd not in _DRAW: _DRAW[nd] = np.stack([np.random.default_rng([20260905, k]).integers(0, nd, nd) for k in range(NB)])
    return _DRAW[nd]
def boot_sr_pair(x, y, days):
    ud, inv = np.unique(days, return_inverse=True); nd = len(ud)
    c = np.bincount(inv).astype(float); sx = np.bincount(inv, x); qx = np.bincount(inv, x * x); sy = np.bincount(inv, y); qy = np.bincount(inv, y * y)
    r = draws(nd); n = c[r].sum(1)
    def srb(s_, q_):
        m = s_[r].sum(1) / n; v = (q_[r].sum(1) - n * m * m) / (n - 1); return m / np.sqrt(v) * ANN
    a, b = srb(sx, qx), srb(sy, qy); dd = a - b
    return dict(n_days=int(nd), ci95_x=[float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))], ci95_diff=[float(np.percentile(dd, 2.5)), float(np.percentile(dd, 97.5))], se_diff=float(dd.std(ddof=1)))
def nested(X, names, a0_idx, segs, win_mask):
    SRall = SRcols(X[win_mask]); H = int(SRall.argmax())
    rows = []; parts = []; span = np.zeros(len(TS), bool)
    for (lo, hi) in segs:
        tr = TS < lo; sg = (TS >= lo) & (TS < hi); span |= sg
        srt = SRcols(X[tr]); k = int(srt.argmax()); srs = SRcols(X[sg]); b = int(srs.argmax())
        rows.append(dict(segment="%s .. %s" % (time.strftime("%Y-%m-%d %HZ", time.gmtime(int(TS[sg][0]))), time.strftime("%Y-%m-%d %HZ", time.gmtime(int(TS[sg][-1])))), n=int(sg.sum()),
                         train_n=int(tr.sum()), selected=str(names[k]), SR_train=float(srt[k]), SR_oos=float(srs[k]), mean_g_oos=float(X[sg, k].mean()),
                         A0_SR=(float(srs[a0_idx]) if a0_idx is not None else None), Hstar_SR=float(srs[H]), best_member=str(names[b]), best_SR=float(srs[b]),
                         selected_negative=bool(srs[k] < 0), A0_negative=(bool(srs[a0_idx] < 0) if a0_idx is not None else None), Hstar_negative=bool(srs[H] < 0)))
        parts.append((sg, k))
    xn = np.concatenate([X[sg, k] for sg, k in parts]); dn = np.concatenate([DAY[sg] for sg, k in parts])
    xh = X[span, H]; assert len(xh) == len(xn)
    srn = SR(xn); srh = SR(xh); srspan = SRcols(X[span]); bspan = int(srspan.argmax())
    bt = boot_sr_pair(xn, xh, dn)
    out = dict(Hstar=str(names[H]), SR_Hstar_window=float(SRall[H]), SR_nested=srn, SR_Hstar_span=srh, SR_A0_span=(float(srspan[a0_idx]) if a0_idx is not None else None),
               span_best=str(names[bspan]), SR_span_best=float(srspan[bspan]), haircut_primary=srn - srh, haircut_level=srn - float(SRall[H]),
               ci95_SR_nested=bt["ci95_x"], ci95_haircut_primary=bt["ci95_diff"], se_haircut_primary=bt["se_diff"], n_days_span=bt["n_days"], segments=rows,
               n_span=int(span.sum()))
    return out
SEG_WF = [(ut(2023, 1, 1), ut(2024, 1, 1)), (ut(2024, 1, 1), ut(2025, 1, 1)), (ut(2025, 1, 1), ut(2026, 1, 1)), (ut(2026, 1, 1), ut(2026, 8, 30, 20) + 1)]
SEG_FR = [(ut(2025, 3, 1), ut(2026, 1, 1)), (ut(2026, 1, 1), ut(2026, 8, 10, 20) + 1)]
def year_ref(X, names, a0_idx, H):
    y22 = (TS >= ut(2022, 1, 1)) & (TS < ut(2023, 1, 1)); s = SRcols(X[y22]); b = int(s.argmax())
    return dict(segment="2022 (training only)", n=int(y22.sum()), A0_SR=(float(s[a0_idx]) if a0_idx is not None else None), Hstar_SR=float(s[H]), best_member=str(names[b]), best_SR=float(s[b]))
# ------------------------------------------------------------------ GATE-I on the real F1 s42 matrix (implementation only; no statistic read)
D42 = DATA["42"]; F1m = D42["F1"].astype(bool)
GATEI = gate_I(D42["G"][:, F1m])
# ------------------------------------------------------------------ GATE-C controls
NC = int(F1m.sum()); assert NC == 125
def control(kind, r):
    X = np.empty((len(TS), NC))
    for i in range(NC):
        k = (i if kind == "C1" else 1000 + i) + 10000 * r
        X[:, i] = np.random.default_rng([20260905, k]).standard_normal(len(TS))
    if kind == "C1": X[:, NC - 1] += 4.0 / ANN
    names = np.array(["m%03d" % i for i in range(NC)])
    pb, _ = cscv(X, names); ds = dsr(X, names, None, Ns_extra=()); ne = nested(X, names, None, SEG_WF, WF)
    sel = ds["SEL"]["member"]; picks = sum(1 for row in ne["segments"] if row["selected"] == "m%03d" % (NC - 1))
    Tspan = ne["n_span"]
    if kind == "C1":
        ok = dict(PBO_le_0p05=pb["PBO"] <= 0.05, SEL_is_planted=sel == "m%03d" % (NC - 1), nested_picks_planted_ge3=picks >= 3, DSR_ge_0p95=ds["SEL"]["P_true_SR_gt_0_N_eff"] >= 0.95)
    else:
        ok = dict(PBO_ge_0p30=pb["PBO"] >= 0.30, nested_SR_within_2p5SE=abs(ne["SR_nested"]) <= 2.5 * math.sqrt(2190.0 / Tspan), DSR_lt_0p95=ds["SEL"]["P_true_SR_gt_0_N_eff"] < 0.95)
    return dict(kind=kind, replicate=r, PBO=pb["PBO"], slope=pb["slope"], P_oos_loss=pb["P_oos_loss"], SEL=sel, SEL_SR=ds["SEL"]["SR_annual"], N_eff=ds["N_eff"],
                DSR_SEL_Neff=ds["SEL"]["P_true_SR_gt_0_N_eff"], nested_SR=ne["SR_nested"], nested_picks_planted=picks, Hstar=ne["Hstar"], haircut=ne["haircut_primary"],
                checks={k: bool(v) for k, v in ok.items()}, pass_=bool(all(ok.values())))
CTRL = [control(kind, r) for kind in ("C1", "C2") for r in range(10)]
GATEC_PASS = bool(all(c["pass_"] for c in CTRL if c["replicate"] == 0))
ALLGATES = bool(GATE0_PASS and GATEI["pass_"] and GATEC_PASS)
OUT = dict(device="t6_compute.py", self_sha256=sha(os.path.abspath(__file__)), argv=sys.argv, env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)},
           python=sys.version.split()[0], numpy=np.__version__, scipy=__import__("scipy").__version__, family_sha256=EXT["family_sha256"],
           series_sha256={s: EXT["seeds"][s]["out_sha256"] for s in ("42", "2027")}, GATE_X={s: EXT["seeds"][s]["gate_X_pass"] for s in ("42", "2027")},
           GATE_0=GATE0, GATE_0_PASS=GATE0_PASS, GATE_I=GATEI, GATE_C=CTRL, GATE_C_PASS=GATEC_PASS, ALL_GATES_PASS=ALLGATES)
if ALLGATES:
    RES = {}
    def fam_block(s, fam, windows=("W_FULL", "FROZEN"), full=True):
        D = DATA[s]; m = D[fam].astype(bool); X = D["G"][:, m]; names = D["member_id"][m].astype(str)
        stems = D["stem"][m].astype(str); lab = np.array(["%s:%s" % (a, b) for a, b in zip(names, stems)])
        a0 = [i for i, st in enumerate(stems) if st in ("A0_PWR230k_s42", "A0_PWR230k_s2027")]; a0 = a0[0] if a0 else None
        out = dict(N=int(m.sum()))
        for w in windows:
            mask = dict(W_FULL=WF, FROZEN=FR, W_ALPHA=WA)[w]; Xw = X[mask]
            pb, _ = cscv(Xw, lab); ds = dsr(Xw, lab, a0)
            blk = dict(PBO=pb, DSR=ds)
            if w in ("W_FULL", "FROZEN"):
                ne = nested(X, lab, a0, SEG_WF if w == "W_FULL" else SEG_FR, mask); blk["NESTED"] = ne
                if w == "W_FULL":
                    H = int(np.nonzero(lab == ne["Hstar"])[0][0]); blk["YEAR2022"] = year_ref(X, lab, a0, H)
            out[w] = blk
        return out
    RES["F1_s42"] = fam_block("42", "F1", windows=("W_FULL", "FROZEN", "W_ALPHA"))
    RES["F1_s2027"] = fam_block("2027", "F1")
    for fam in ("F2", "F3", "F4", "F5"): RES[fam + "_s42"] = fam_block("42", fam)
    OUT["RESULTS"] = RES
OUT["wall_s"] = None
json.dump(OUT, open(os.path.join(RD, "RECEIPT_T6_compute.json"), "w"), indent=1, default=float)
c1 = [c for c in CTRL if c["kind"] == "C1" and c["replicate"] == 0][0]; c2 = [c for c in CTRL if c["kind"] == "C2" and c["replicate"] == 0][0]
line = "SUMMARY t6_compute GATE0=%s GATEI=%s(maxabs=%.2e) GATEC=%s [C1 PBO=%.4f SEL=%s picks=%d DSR=%.3f | C2 PBO=%.4f nestedSR=%.3f DSR=%.3f] ALL=%s" % (
    GATE0_PASS, GATEI["pass_"], GATEI["max_abs_diff"], GATEC_PASS, c1["PBO"], c1["SEL"], c1["nested_picks_planted"], c1["DSR_SEL_Neff"], c2["PBO"], c2["nested_SR"], c2["DSR_SEL_Neff"], ALLGATES)
if ALLGATES:
    r = OUT["RESULTS"]["F1_s42"]
    line += " | F1s42 WFULL PBO=%.4f Neff=%.2f nested=%.3f Hstar_span=%.3f haircut=%.3f ; FROZEN PBO=%.4f nested=%.3f Hstar=%.3f haircut=%.3f" % (
        r["W_FULL"]["PBO"]["PBO"], r["W_FULL"]["DSR"]["N_eff"], r["W_FULL"]["NESTED"]["SR_nested"], r["W_FULL"]["NESTED"]["SR_Hstar_span"], r["W_FULL"]["NESTED"]["haircut_primary"],
        r["FROZEN"]["PBO"]["PBO"], r["FROZEN"]["NESTED"]["SR_nested"], r["FROZEN"]["NESTED"]["SR_Hstar_span"], r["FROZEN"]["NESTED"]["haircut_primary"])
line += " self_sha256=%s" % OUT["self_sha256"][:16]
print(line)
sys.exit(0 if ALLGATES else 3)
