#!/usr/bin/env python3
"""dlarch_s1s3.py — PREREG docs/PREREG_dlarch_supplementary_S1S3_2026-09-24.md (4cb7b5d9f).

S1  book-layer correlation between the King book kc and the F10 book fc (the ladder only measured the
    SCORE layer, rho = +0.04..+0.11). Three quantities reported SIDE BY SIDE; deriving one from another
    is forbidden by the prereg (受据 full_gradient_window_buys_nothing retraction).
S2  the share of F10's leg-layer paper return that lies in the SPAN of the D/E/J families (the only
    families that passed the 2026-08-22 F8 pre-gate). EXACT linear identity u(z)==u(z_fit)+u(z_res),
    plus a column-count-matched placebo. THIS IS NOT AN ABLATION — an ablation needs a retrain (GPU).
S3  single-parameter counterfactual rechain of the dead band |trade| < 0.00025: a bitwise parity arm
    first (proves the harness IS the production path), then band=0. A zero difference is reported as
    SWITCH_NOT_WIRED, never as "the band is worthless".

READ-ONLY apart from this device's own outputs. No GPU, no venue calls, no writes under /dev/shm.

usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B dlarch_s1s3.py \
         PATH,HOME,LC_CTYPE <outdir> [S1,S2,S3]
"""
import os, sys, ast, json, time, hashlib, calendar, copy

import numpy as np

W = "/dev/shm/news2_2026-09-23"
LAB = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz"
LAB_SHA = "ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62"
F8_SRC = f"{W}/treeNC5_deploy/fea171/f8_higher_order_features.py"
MASK_PATH = "/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"
SEEDS = (42, 2027)
POLICIES = ("literal", "scaled_diagnostic")
SEG = {"2023H2": ("2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z"),
       "2024": ("2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z"),
       "2025": ("2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z"),
       "pre2026": ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z"),
       "2026_descriptive_only": ("2026-01-01T00:00:00Z", "2026-08-31T00:00:00Z")}
MAIN = "pre2026"
RNG_BASE = 20260924
S1_NULL_DRAWS = 20          # prereg §3
S1_K_SE = 3.0               # gate FORM ruled by lead (AMENDMENT 1); dlarch did not choose it
S2_PLACEBO_SEEDS = 5        # prereg §4
TOL = 1e-9


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def log(*a): print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def stats1(v):
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    if not len(v): return {"NO_MEASUREMENT": "0 finite values"}
    se = float(v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 1 else float("nan")
    return {"n": int(len(v)), "mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else None,
            "se": se, "t": float(v.mean() / se) if se and np.isfinite(se) and se > 0 else None,
            "p10": float(np.percentile(v, 10)), "median": float(np.median(v)), "p90": float(np.percentile(v, 90))}


def f89_names():
    """Rebuild X89's column names from the source that ACTUALLY produced X89 (sha bound by P2B_FEATURES)."""
    want = json.load(open(f"{W}/receipts/P2B_FEATURES.json"))["tree_outputs"]["fea171/f8_higher_order_features.py"]
    got = sha(F8_SRC)
    assert got == want, f"f8 source sha {got[:16]} != the one that built X89 {want[:16]}"
    tree = ast.parse(open(F8_SRC, "rb").read(), F8_SRC)
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build"]
    assert len(fn) == 1, "build() not found"
    # one namespace used as BOTH globals and locals: a list comprehension's inner scope resolves free
    # names through globals, so passing a separate locals dict makes `order` invisible inside it.
    ns = {"__builtins__": {}}
    need = ["order", "all_rank_names", "H_names", "I_names", "names"]
    found = {}
    for node in ast.walk(fn[0]):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            nm = node.targets[0].id
            if nm in need and nm not in found: found[nm] = node.value
    for nm in need:
        assert nm in found, f"assignment {nm} not found in build()"
        ns[nm] = eval(compile(ast.Expression(found[nm]), F8_SRC, "eval"), ns)
    nm = list(ns["names"])
    assert len(nm) == 89, f"rebuilt names has {len(nm)} entries, expected 89"
    return nm, got


def main():
    WLIST = set(sys.argv[1].split(","))
    extra = sorted(set(os.environ) - WLIST)
    assert not extra, f"env outside whitelist: {extra}"
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    todo = set((sys.argv[3] if len(sys.argv) > 3 else "S1,S2,S3").split(","))
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[k] = "4"
    sys.path.insert(0, f"{W}/devices")
    from scipy.stats import rankdata, spearmanr

    rec = {"device": "dlarch_s1s3.py", "self_sha256": sha(os.path.abspath(__file__)),
           "prereg": {"path": "docs/PREREG_dlarch_supplementary_S1S3_2026-09-24.md", "commit": "4cb7b5d9f"},
           "caliber": {"label": "dlw_targets.npz y4s — NOT the v4 RAW accounting caliber (KB-05); for contrast only",
                       "unit": "bps per anchor per unit gross"},
           "utc_start": iso(time.time()), "sections": sorted(todo), "inputs": {}, "S1": {}, "S2": {}, "S3": {}}

    log("hashing inputs")
    fpath = f"{W}/work/NEWS_FEATURES.npz"; lpath = f"{W}/work/legs.npz"
    fsha = sha(fpath); lsha = sha(lpath)
    assert json.load(open(f"{W}/receipts/P2B_FEATURES.json"))["sha256"] == fsha
    assert json.load(open(f"{W}/receipts/P3_LEGS.json"))["sha256"] == lsha
    assert sha(LAB) == LAB_SHA
    rec["inputs"].update({fpath: fsha, lpath: lsha, LAB: LAB_SHA})

    F = np.load(fpath); leg = np.load(lpath); lab = np.load(LAB, allow_pickle=True)
    a = F["anchors"].astype(np.int64); syms = F["symbols"]
    ya = lab["E_ts"].astype(np.int64); Y = lab["y4s"]
    assert np.array_equal(lab["symbols"], syms)
    off = F["off"]; mm = F["m"].astype(np.int64)
    members = [mm[off[i]:off[i + 1]] for i in range(len(a))]
    ready = leg["ready"]
    iy = np.searchsorted(ya, a); lab_ok = (iy < len(ya)) & (ya[np.minimum(iy, len(ya) - 1)] == a)
    masks = {s: (a >= ts(lo)) & (a <= ts(hi)) for s, (lo, hi) in SEG.items()}
    f10P = {}
    for sd in SEEDS:
        p = f"{W}/work/f10_s{sd}/F10_OOF.npz"
        assert json.load(open(f"{W}/work/f10_s{sd}/TRAIN_RECEIPT.json"))["pred_sha256"] == sha(p)
        rec["inputs"][p] = sha(p); f10P[sd] = np.load(p)["P"]

    # ─────────────────────────── S1 ───────────────────────────
    if "S1" in todo:
        log("S1 book-layer correlation")
        for sd in SEEDS:
            tr = json.load(open(f"{W}/work/combo_s{sd}/TARGET_RECEIPT.json"))
            for pol in POLICIES:
                cp = f"{W}/work/combo_s{sd}/{pol}.npz"; h = sha(cp)
                assert tr["policies"][pol]["sha"] == h
                rec["inputs"][cp] = h
                C = np.load(cp); ca = C["E_ts"].astype(np.int64)
                kc = C["kc"]; fc = C["fc"]
                ci = np.searchsorted(a, ca); assert np.all(a[ci] == ca)
                out = {}
                for s in SEG:
                    sel = np.flatnonzero(masks[s][ci] & ready[ci] & lab_ok[ci])
                    if not len(sel): out[s] = {"NO_ANCHORS": True}; continue
                    wp, wsp, canc, ukc, ufc = [], [], [], [], []
                    for j in sel:
                        i = ci[j]; yv = np.nan_to_num(Y[iy[i]], nan=0.0)
                        k = kc[j]; f = fc[j]
                        nz = (np.abs(k) > 1e-12) | (np.abs(f) > 1e-12)
                        if nz.sum() >= 20 and k[nz].std() > 0 and f[nz].std() > 0:
                            wp.append(float(np.corrcoef(k[nz], f[nz])[0, 1]))
                            r = spearmanr(k[nz], f[nz]).statistic
                            if np.isfinite(r): wsp.append(float(r))
                        gk = float(np.abs(k).sum()); gf = float(np.abs(f).sum())
                        den = .55 * gk + .45 * gf
                        if den > 1e-9: canc.append(float(np.abs(.55 * k + .45 * f).sum()) / den)
                        if gk > 1e-9: ukc.append(1e4 * float((k * yv).sum()) / gk)
                        if gf > 1e-9: ufc.append(1e4 * float((f * yv).sum()) / gf)
                    n = min(len(ukc), len(ufc))
                    rr = {"n_anchors": int(len(sel)),
                          "Q1_weight_corr_pearson": stats1(wp), "Q1_weight_corr_spearman": stats1(wsp),
                          "Q3_cancellation_coef": stats1(canc)}
                    if n > 2:
                        x = np.asarray(ukc[:n]); y2 = np.asarray(ufc[:n])
                        rr["Q2_return_corr_pearson"] = float(np.corrcoef(x, y2)[0, 1])
                        rr["Q2_return_corr_spearman"] = float(spearmanr(x, y2).statistic)
                        rr["Q2_n_paired_anchors"] = int(n)
                    else:
                        rr["Q2"] = {"NO_MEASUREMENT": f"only {n} paired anchors"}
                    out[s] = rr
                # null control on the MAIN window: shuffle fc's NAME axis within the anchor
                sel = np.flatnonzero(masks[MAIN][ci] & ready[ci] & lab_ok[ci])
                nulls, n_equal = [], 0
                base = out[MAIN]["Q1_weight_corr_pearson"].get("mean")
                for b in range(S1_NULL_DRAWS):
                    rng = np.random.default_rng([RNG_BASE, 1, b]); vals = []
                    for j in sel:
                        k = kc[j]; f = fc[j].copy(); rng.shuffle(f)
                        nz = (np.abs(k) > 1e-12) | (np.abs(f) > 1e-12)
                        if nz.sum() >= 20 and k[nz].std() > 0 and f[nz].std() > 0:
                            vals.append(float(np.corrcoef(k[nz], f[nz])[0, 1]))
                    m = float(np.mean(vals)) if vals else float("nan")
                    nulls.append(m)
                    if base is not None and np.isfinite(m) and abs(m - base) <= 1e-12: n_equal += 1
                nv = np.asarray(nulls, float)
                se = float(nv.std(ddof=1) / np.sqrt(len(nv)))
                out["NULL_CONTROL"] = {"draws": S1_NULL_DRAWS, "mean": float(nv.mean()), "sd": float(nv.std(ddof=1)),
                                       "se": se, "gate_rhs_3se": S1_K_SE * se,
                                       "PASS": bool(abs(float(nv.mean())) <= S1_K_SE * se) if se > 0 else False,
                                       "draws_equal_to_unpermuted": n_equal,
                                       "unpermuted_mean_for_reference": base}
                rec["S1"][f"s{sd}_{pol}"] = out
                log("S1", sd, pol, "pre2026 wcorr", out[MAIN]["Q1_weight_corr_pearson"].get("mean"),
                    "rcorr", out[MAIN].get("Q2_return_corr_pearson"), "canc", out[MAIN]["Q3_cancellation_coef"].get("mean"),
                    "null", out["NULL_CONTROL"]["mean"], out["NULL_CONTROL"]["PASS"])

    # ─────────────────────────── S2 ───────────────────────────
    if "S2" in todo:
        log("S2 D/E/J span share")
        names89, f8sha = f89_names()
        rec["inputs"][F8_SRC] = f8sha
        fam = {}
        for k, nm in enumerate(names89): fam.setdefault(nm.split(":")[0], []).append(k)
        dej = sorted(fam["D"] + fam["E"] + fam["J"])
        others = sorted(set(range(89)) - set(dej))
        rec["S2"]["columns"] = {"family_sizes": {k: len(v) for k, v in sorted(fam.items())},
                                "DEJ_cols_in_X89": dej, "n_DEJ": len(dej), "n_other": len(others),
                                "names_DEJ": [names89[k] for k in dej],
                                "source": F8_SRC, "source_sha256": f8sha}
        log("S2 families", rec["S2"]["columns"]["family_sizes"], "n_DEJ", len(dej))
        X89 = F["X89"]
        rows = np.flatnonzero(ready & lab_ok & masks[MAIN])
        segs_of = {i: [s for s in SEG if masks[s][i]] for i in rows}
        worst = 0.0
        for sd in SEEDS:
            acc = {s: {"u_total": [], "u_fit": [], "u_res": [], "r2": [], "u_hardrank": []} for s in SEG}
            plac = {s: {k: [] for k in range(S2_PLACEBO_SEEDS)} for s in SEG}
            rankdef = 0; red_ok = True; red_checked = False
            pl_cols = {k: np.sort(np.random.default_rng([RNG_BASE, 100 + k]).choice(others, size=len(dej), replace=False))
                       for k in range(S2_PLACEBO_SEEDS)}
            nzcount = np.zeros(len(dej), np.int64)
            for i in rows:
                m = members[i]; sl = slice(off[i], off[i + 1])
                p = f10P[sd][i][m]; ok = np.isfinite(p)
                if ok.sum() < 20: continue
                yv = np.nan_to_num(Y[iy[i]][m], nan=0.0)
                z = np.zeros(len(m)); zz = p[ok].astype(np.float64)
                z[ok] = (zz - zz.mean()) / (zz.std() + 1e-8)
                Xd = X89[sl][:, dej].astype(np.float64)[ok]
                nzcount += (np.abs(X89[sl][:, dej].astype(np.float64)) > 0).sum(0)
                Xd = (Xd - Xd.mean(0)) / (Xd.std(0) + 1e-12)
                A = np.column_stack([np.ones(Xd.shape[0]), Xd])
                sol, _, rk, _ = np.linalg.lstsq(A, z[ok], rcond=None)
                if rk < A.shape[1]: rankdef += 1
                zf = np.zeros(len(m)); zf[ok] = A @ sol
                zr = z - zf
                den = float(np.abs(z).sum())
                if den <= 1e-9: continue
                ut = float((z * yv).sum()); uf = float((zf * yv).sum()); ur = float((zr * yv).sum())
                scale = max(abs(ut), abs(uf), abs(ur), 1.0)
                worst = max(worst, abs(ut - (uf + ur)) / scale)
                r2 = 1.0 - float(np.var(zr[ok])) / max(float(np.var(z[ok])), 1e-30)
                # production hard-rank leg on the same anchors, for the bridge demanded by the prereg
                zh = np.zeros(len(m)); zh[ok] = rankdata(p[ok]) / max(ok.sum() - 1, 1) - .5
                okl = np.isfinite(Y[iy[i]][m])
                zhh = np.where(okl, zh, 0.0); zhh = zhh - (zhh[okl].mean() if okl.sum() else 0.0)
                gh = float(np.abs(zhh).sum())
                uh = 1e4 * float((zhh / gh * yv).sum()) if gh > 1e-9 else 0.0
                # placebo
                pv = {}
                for k, cols in pl_cols.items():
                    Xp = X89[sl][:, cols].astype(np.float64)[ok]
                    Xp = (Xp - Xp.mean(0)) / (Xp.std(0) + 1e-12)
                    Ap = np.column_stack([np.ones(Xp.shape[0]), Xp])
                    sp, _, _, _ = np.linalg.lstsq(Ap, z[ok], rcond=None)
                    zpf = np.zeros(len(m)); zpf[ok] = Ap @ sp
                    pv[k] = 1e4 * float((zpf * yv).sum()) / den
                if not red_checked:                     # N1-style red capability: zero design matrix
                    A0 = np.ones((Xd.shape[0], 1))
                    s0, _, _, _ = np.linalg.lstsq(A0, z[ok], rcond=None)
                    z0 = np.zeros(len(m)); z0[ok] = A0 @ s0
                    red_ok = bool(abs(float((z0 * yv).sum())) <= 1e-9 * scale + 1e-9)
                    rec["S2"].setdefault("red_capability", {})[f"s{sd}"] = {
                        "anchor": iso(a[i]), "intercept_only_u_fit": float((z0 * yv).sum()),
                        "full_u_fit": uf, "zero_design_gives_zero_fit": red_ok}
                    red_checked = True
                for s in segs_of[i]:
                    acc[s]["u_total"].append(1e4 * ut / den); acc[s]["u_fit"].append(1e4 * uf / den)
                    acc[s]["u_res"].append(1e4 * ur / den); acc[s]["r2"].append(r2)
                    acc[s]["u_hardrank"].append(uh)
                    for k in pl_cols: plac[s][k].append(pv[k])
            out = {"rank_deficient_anchors": rankdef,
                   "nonzero_cells_per_DEJ_col": {names89[c]: int(nzcount[q]) for q, c in enumerate(dej)}}
            for s in SEG:
                if not acc[s]["u_total"]: out[s] = {"NO_ANCHORS": True}; continue
                pm = {k: float(np.mean(plac[s][k])) for k in pl_cols}
                fitm = float(np.mean(acc[s]["u_fit"]))
                out[s] = {"n": len(acc[s]["u_total"]),
                          "u_total_linear": stats1(acc[s]["u_total"]), "u_fit_DEJ": stats1(acc[s]["u_fit"]),
                          "u_res": stats1(acc[s]["u_res"]), "R2": stats1(acc[s]["r2"]),
                          "bridge_hardrank_leg": stats1(acc[s]["u_hardrank"]),
                          "share_fit_over_total": (fitm / float(np.mean(acc[s]["u_total"]))) if abs(np.mean(acc[s]["u_total"])) > 1e-12 else None,
                          "placebo_u_fit_means": pm, "placebo_max": max(pm.values()),
                          "BEATS_PLACEBO": bool(fitm > max(pm.values()))}
            rec["S2"][f"s{sd}"] = out
            log("S2", sd, "pre2026 u_total", round(out[MAIN]["u_total_linear"]["mean"], 4),
                "u_fit", round(out[MAIN]["u_fit_DEJ"]["mean"], 4), "u_res", round(out[MAIN]["u_res"]["mean"], 4),
                "R2", round(out[MAIN]["R2"]["mean"], 4), "placebo_max", round(out[MAIN]["placebo_max"], 4),
                "beats", out[MAIN]["BEATS_PLACEBO"])
        rec["S2"]["identity_worst_rel_err"] = worst
        assert worst <= TOL, f"S2 linear identity failed: {worst}"

    # ─────────────────────────── S3 ───────────────────────────
    if "S3" in todo:
        log("S3 dead-band counterfactual rechain")
        from continuous_combo import evolve
        from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA
        import combo_target
        assert sha(f"{W}/vendor_live/fea171/combo_stage.py") == combo_target.EXPECTED, "producer source"
        assert sha(UNIVERSE_PATH) == UNIVERSE_SHA
        rec["inputs"][f"{W}/vendor_live/fea171/combo_stage.py"] = combo_target.EXPECTED
        rec["inputs"][UNIVERSE_PATH] = UNIVERSE_SHA
        rec["inputs"][MASK_PATH] = sha(MASK_PATH)
        universe = np.load(UNIVERSE_PATH)
        mk = np.load(MASK_PATH); assert np.array_equal(mk["ts"].astype(np.int64), a)
        crypto = np.load(f"{W}/receipts/P1_members_2025H2on.npz")["crypto"]
        cand = mk["mask"] & crypto[None, :]
        use = (a >= 1672531200) & (a <= universe["ts"][-1]); au = a[use]
        book_legal = align_universe(au, syms, universe) & cand[use]
        params = json.loads(open(f"{W}/inputs/bundle_config.json").read())["params"]
        mem_u = [members[i] for i in np.flatnonzero(use)]
        args = dict(anchors=au, king=leg["KZ"][use].astype(np.float64), fund=leg["ZFD"][use].astype(np.float64),
                    seats=leg["WL"][use].astype(np.float64), rn8=leg["RN8"][use].astype(np.float64),
                    members=mem_u, qv=leg["QV"][use].astype(np.float64), legal=book_legal, ready=leg["ready"][use])
        ci = np.searchsorted(a, au); assert np.all(a[ci] == au)
        for sd in SEEDS:
            f10 = f10P[sd][use].astype(np.float64)
            for pol in POLICIES:
                arch = np.load(f"{W}/work/combo_s{sd}/{pol}.npz")
                # ----承重 1: PARITY arm must reproduce the archive array-for-array ----
                t0 = time.monotonic()
                P_ = evolve(f10=f10, params=params, publication=pol, **args)
                par = {k: bool(np.array_equal(P_[k], arch[k])) for k in ("kc", "fc", "raw", "weights", "trade_mask", "reason")}
                rec["S3"].setdefault(f"s{sd}_{pol}", {})["PARITY"] = {
                    "arrays_identical": par, "ALL": all(par.values()), "seconds": time.monotonic() - t0}
                log("S3 parity", sd, pol, par)
                assert all(par.values()), f"S3 parity failed s{sd} {pol}: {par}"
                # ---- counterfactual: band = 0 ----
                p0 = copy.deepcopy(params); p0["band"] = 0.0
                B_ = evolve(f10=f10, params=p0, publication=pol, **args)
                diff_anchor = np.array([int((np.abs(B_["fc"][j] - P_["fc"][j]) > 0).sum()) for j in range(len(au))])
                # ---- 承重 2: the switch must actually be wired ----
                n_diff_anchors = int((diff_anchor > 0).sum())
                first = int(np.argmax(diff_anchor > 0)) if n_diff_anchors else None
                tm_diff = np.flatnonzero(B_["trade_mask"] != P_["trade_mask"])
                ent = {"n_anchors_with_any_fc_diff": n_diff_anchors,
                       "first_diff_anchor": iso(au[first]) if first is not None else None,
                       "SWITCH_WIRED": bool(n_diff_anchors > 0),
                       "trade_mask_first_divergence": iso(au[int(tm_diff[0])]) if len(tm_diff) else None,
                       "n_anchors_trade_mask_differs": int(len(tm_diff))}
                rec["S3"][f"s{sd}_{pol}"]["SWITCH"] = ent
                if not ent["SWITCH_WIRED"]:
                    rec["S3"][f"s{sd}_{pol}"]["VERDICT"] = "SWITCH_NOT_WIRED"
                    log("S3 SWITCH_NOT_WIRED", sd, pol); continue
                seg_out = {}
                for s in SEG:
                    sel = np.flatnonzero(masks[s][ci] & ready[ci] & lab_ok[ci])
                    if not len(sel): seg_out[s] = {"NO_ANCHORS": True}; continue
                    cut_frac, cut_mass, ufcP, ufcB, urawP, urawB, turnP, turnB = [], [], [], [], [], [], [], []
                    prevP = np.zeros(len(syms)); prevB = np.zeros(len(syms))
                    for j in sel:
                        i = ci[j]; yv = np.nan_to_num(Y[iy[i]], nan=0.0)
                        fP = P_["fc"][j]; fB = B_["fc"][j]
                        d = np.abs(fB - fP) > 0
                        nzB = int((np.abs(fB) > 1e-12).sum())
                        cut_frac.append(d.sum() / max(nzB, 1))
                        gB = float(np.abs(fB).sum())
                        cut_mass.append(float(np.abs(fB[d] - fP[d]).sum()) / gB if gB > 1e-9 else 0.0)
                        gP = float(np.abs(fP).sum())
                        if gP > 1e-9: ufcP.append(1e4 * float((fP * yv).sum()) / gP)
                        if gB > 1e-9: ufcB.append(1e4 * float((fB * yv).sum()) / gB)
                        rP = P_["raw"][j]; rB = B_["raw"][j]
                        grP = float(np.abs(rP).sum()); grB = float(np.abs(rB).sum())
                        if grP > 1e-9: urawP.append(1e4 * float((rP * yv).sum()) / grP)
                        if grB > 1e-9: urawB.append(1e4 * float((rB * yv).sum()) / grB)
                        turnP.append(float(np.abs(fP - prevP).sum())); turnB.append(float(np.abs(fB - prevB).sum()))
                        prevP, prevB = fP, fB
                    seg_out[s] = {"n_anchors": int(len(sel)),
                                  "cells_held_by_band_frac_of_nonzero": stats1(cut_frac),
                                  "mass_held_by_band_frac_of_gross": stats1(cut_mass),
                                  "u_fc_band_on": stats1(ufcP), "u_fc_band_off": stats1(ufcB),
                                  "u_raw_band_on": stats1(urawP), "u_raw_band_off": stats1(urawB),
                                  "turnover_fc_band_on": stats1(turnP), "turnover_fc_band_off": stats1(turnB),
                                  "publish_rate_band_on": float((P_["trade_mask"][sel]).mean()),
                                  "publish_rate_band_off": float((B_["trade_mask"][sel]).mean())}
                rec["S3"][f"s{sd}_{pol}"]["segments"] = seg_out
                rec["S3"][f"s{sd}_{pol}"]["VERDICT"] = "MEASURED"
                m = seg_out[MAIN]
                log("S3", sd, pol, "cells_held", round(m["cells_held_by_band_frac_of_nonzero"]["mean"], 4),
                    "mass", round(m["mass_held_by_band_frac_of_gross"]["mean"], 5),
                    "u_fc on/off", round(m["u_fc_band_on"]["mean"], 4), round(m["u_fc_band_off"]["mean"], 4),
                    "turn on/off", round(m["turnover_fc_band_on"]["mean"], 5), round(m["turnover_fc_band_off"]["mean"], 5))

    rec["utc_end"] = iso(time.time())
    op = os.path.join(outdir, "S1S3.json")
    tmp = op + ".tmp"; open(tmp, "w").write(json.dumps(rec, indent=1, allow_nan=False)); os.replace(tmp, op)
    print(f"S1S3 DONE sections={sorted(todo)} json={sha(op)[:16]}", flush=True)


if __name__ == "__main__":
    main()
