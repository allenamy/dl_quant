"""l2_b_judge.py — PREREG_L2 §7 statistics, §8 C5/C6 inputs, §9 frozen reading and verdict. Reads the build, selftest, fit and null receipts
(sha-checked), the data and OOS score files; writes RECEIPT_L2_B_judge.json. Gate cells = {R, L} × {A, B} on FULL / P_all in both seeds;
BASE gives ΔG (C3); DESC and P_neg are descriptive / secondary and never change the verdict."""
import os, sys, time, json
import numpy as np
from scipy.stats import rankdata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C
import l2_b_common as B

T_START = time.time()
envrep = C.check_env(sys.argv); pre = B.check_prereg()
st0 = C.sysstate(); assert st0["gpu"].replace(" ", "") == "0%,2MiB", st0["gpu"]
DEV = ("l2_common.py", "l2_b_common.py", "l2_b_judge.py", "run_l2.sh")
rep = dict(device="l2_b_judge.py", device_sha256={f: C.sha256(os.path.join(C.L2, "devices", f)) for f in DEV}, prereg=pre, env=envrep, sys_before=st0)
R = {}
for nm in ("build", "selftest", "fit", "null"):
    p = os.path.join(C.L2, "receipts", "RECEIPT_L2_B_%s.json" % nm); R[nm] = json.load(open(p)); rep["%s_receipt_sha256" % nm] = C.sha256(p)
PRE_GATES = dict(G_IN=True, selftest=bool(all(R["selftest"]["gates"].values())), fits_96=R["fit"]["n_fits"] == 96)
rep["preconditions"] = PRE_GATES


def within_anchor_spearman(p, v, a, sizes):
    """Mean over anchors of Spearman(p, v) using rows with finite v; anchors with < MIN_ANCHOR finite rows skipped."""
    out = []; starts = np.concatenate([[0], np.cumsum(sizes)[:-1]])
    for q in range(sizes.size):
        sl = slice(starts[q], starts[q] + sizes[q]); pv = p[sl]; vv = v[sl]; ok = np.isfinite(vv)
        if ok.sum() < B.MIN_ANCHOR:
            continue
        x = rankdata(pv[ok]); y = rankdata(vv[ok]); x -= x.mean(); y -= y.mean()
        den = np.sqrt((x * x).sum() * (y * y).sum())
        if den > 0:
            out.append((x * y).sum() / den)
    return float(np.mean(out)) if out else float("nan"), len(out)


verdict_cells = {}
per_seed = {}
for s in C.SEEDS:
    Z = np.load(R["build"]["per_seed"][s]["out"]); assert C.sha256(R["build"]["per_seed"][s]["out"]) == R["build"]["per_seed"][s]["out_sha256"]
    O = np.load(R["fit"]["out"][s]["path"]); assert C.sha256(R["fit"]["out"][s]["path"]) == R["fit"]["out"][s]["sha256"]
    NU = R["null"]["per_seed"][s]
    I = Z["i"].astype(np.int64); Nn = Z["n"].astype(np.int64); YR = Z["year"].astype(np.int64); DAYv = Z["day"].astype(np.int64)
    RN8 = Z["rn8"]; ABS = Z["absmr"]
    S = {}
    for pop_name, pop_mask in (("P_all", np.ones(I.size, bool)), ("P_neg", RN8 < 0)):
        for T in B.TARGETS:
            r = Z["r" + T]; ok = (YR >= 2023) & np.isfinite(r) & pop_mask
            idx, a, sizes, uniq = B.anchor_index(I, ok)
            big = sizes[a] >= B.MIN_ANCHOR
            idx, a, sizes, uniq = B.anchor_index(I, np.isin(np.arange(I.size), idx[big]))
            sv = -1e4 * r[idx]; col = Nn[idx]
            starts = np.concatenate([[0], np.cumsum(sizes)[:-1]])
            day_a = DAYv[idx][starts]; yr_a = YR[idx][starts]
            ud, dinv = B.block_ids(day_a, T); Cm = B.draw_counts(ud.size); cnt = np.bincount(dinv, None, ud.size)
            pop = np.bincount(a, sv, sizes.size) / sizes
            per = {}
            for fs in B.FSETS:
                for m in B.MODELS:
                    p = O["p_%s_%s_%s" % (m, T, fs)][idx]; assert np.isfinite(p).all()
                    top, bot, mm = B.decile_sets(p, a, sizes, col)
                    Dv, Hv = B.anchor_stats(sv, a, sizes, top, bot); Mv = B.anchor_median_stat(sv, a, sizes, top)
                    w = ABS[idx]
                    Dw = np.bincount(a, sv * w * top, sizes.size) / np.bincount(a, w * top, sizes.size) - np.bincount(a, sv * w, sizes.size) / np.bincount(a, w, sizes.size)
                    sd_top = np.sqrt(np.bincount(a, (sv - pop[a]) ** 2 * top, sizes.size) / mm); sd_all = np.sqrt(np.bincount(a, (sv - pop[a]) ** 2, sizes.size) / sizes)
                    per[(m, fs)] = dict(D=Dv, H=Hv, M=Mv, Dw=Dw, sd_ratio=float(np.nanmean(sd_top / np.maximum(sd_all, 1e-12))), p=p)
            cells = {}
            for fs in B.FSETS:
                for m in B.MODELS:
                    q = per[(m, fs)]; Dv, Hv, Mv = q["D"], q["H"], q["M"]
                    cell = dict(n_anchors=int(sizes.size), n_rows=int(idx.size), n_blocks=int(ud.size), block_days=B.BLOCK_DAYS[T],
                                G=float(Dv.mean()), G_ci=B.boot_ci(Cm, np.bincount(dinv, Dv, ud.size), cnt),
                                H=float(Hv.mean()), H_ci=B.boot_ci(Cm, np.bincount(dinv, Hv, ud.size), cnt),
                                TB=float((Dv - Hv).mean()), TB_ci=B.boot_ci(Cm, np.bincount(dinv, Dv - Hv, ud.size), cnt),
                                G_med=float(Mv.mean()), G_gross_weighted=float(np.nanmean(q["Dw"])), top_sd_ratio=q["sd_ratio"],
                                G_years={str(y): (float(Dv[yr_a == y].mean()) if (yr_a == y).any() else None) for y in B.TEST_YEARS},
                                H_years={str(y): (float(Hv[yr_a == y].mean()) if (yr_a == y).any() else None) for y in B.TEST_YEARS},
                                anchors_years={str(y): int((yr_a == y).sum()) for y in B.TEST_YEARS})
                    if fs != "BASE":
                        b = per[(m, "BASE")]["D"]
                        cell["dG_vs_BASE"] = float((Dv - b).mean()); cell["dG_vs_BASE_ci"] = B.boot_ci(Cm, np.bincount(dinv, Dv - b, ud.size), cnt)
                    if fs == "FULL":
                        d2 = per[(m, "DESC")]["D"]
                        cell["dG_vs_DESC"] = float((Dv - d2).mean()); cell["dG_vs_DESC_ci"] = B.boot_ci(Cm, np.bincount(dinv, Dv - d2, ud.size), cnt)
                        ic0, na0 = within_anchor_spearman(q["p"], -sv, a, sizes)
                        cell["rank_ic_score_vs_return"] = ic0; cell["rank_ic_anchors"] = na0
                        if pop_name == "P_all":
                            SH = B.SHIFT_A if T == "A" else B.SHIFT_B; SM = Z["S" + T][idx]
                            spec = {}
                            for c_, h in enumerate(SH):
                                spec[str(h)] = within_anchor_spearman(q["p"], SM[:, c_], a, sizes)[0]
                            fwd = [h for h in SH if h >= 0]
                            cell["shift_spectrum"] = spec
                            cell["shift_peak_forward"] = max(fwd, key=lambda h: spec[str(h)] if np.isfinite(spec[str(h)]) else -9)
                            cell["shift_peak_forward_is_0"] = cell["shift_peak_forward"] == 0
                            nm = "%s_%s" % (m, T)
                            cell["z"] = float(NU["z_obs"][nm]); cell["q05"] = float(NU["family_min_q05"]); cell["null_sd"] = float(NU["sd_null"][nm])
                            cell["null_G_check"] = abs(cell["z"] * cell["null_sd"] - cell["G"]) < 1e-9 * max(1.0, abs(cell["G"]))
                    cells["%s|%s" % (m, fs)] = cell
            S["%s|%s" % (pop_name, T)] = cells
            print("seed %s %s %s anchors %d rows %d" % (s, pop_name, T, sizes.size, idx.size), flush=True)
    # reading per seed for the 4 gate cells
    rd = {}
    for m in B.MODELS:
        for T in B.TARGETS:
            cell = dict(S["P_all|%s" % T]["%s|FULL" % m]); cell["dG"] = cell["dG_vs_BASE"]; cell["dG_ci"] = cell["dG_vs_BASE_ci"]
            assert cell["null_G_check"], ("judge G differs from null device observed G", s, m, T)
            conds, first = B.reading(cell)
            rd["%s_%s" % (m, T)] = dict(conds=conds, first_fail=first)
        # secondary P_neg labels (C1–C4 only)
    sec = {}
    for m in B.MODELS:
        for T in B.TARGETS:
            cell = dict(S["P_neg|%s" % T]["%s|FULL" % m]); cell["dG"] = cell["dG_vs_BASE"]; cell["dG_ci"] = cell["dG_vs_BASE_ci"]
            cell.update(z=None, q05=None, shift_peak_forward_is_0=None)
            conds, first = B.reading(cell)
            sec["%s_%s" % (m, T)] = dict(C1=conds["C1"], C2=conds["C2"], C3=conds["C3"], C4=conds["C4"],
                                         label=next((l for c, l in (("C1", "DIRECTION-ABSENT"), ("C2", "UNSTABLE"), ("C3", "NOT-BEYOND-FUNDING"), ("C4", "VARIANCE")) if not conds[c]), "C1-C4 hold"))
    per_seed[s] = dict(stats=S, reading=rd, secondary_P_neg=sec)
passing = [c for c in ("R_A", "R_B", "L_A", "L_B") if all(all(per_seed[s]["reading"][c]["conds"].values()) for s in C.SEEDS)]
pre_ok = all(PRE_GATES.values())
verdict = "PASS" if (pre_ok and passing) else "FAIL"
# label for FAIL: the cell that got furthest (most conditions in order) — first failing condition in either seed
order = ["C1", "C2", "C3", "C4", "C5", "C6"]
def depth(c):
    d = 6
    for s in C.SEEDS:
        conds = per_seed[s]["reading"][c]["conds"]
        k = next((q for q, k_ in enumerate(order) if not conds[k_]), 6); d = min(d, k)
    return d
best = max(("R_A", "R_B", "L_A", "L_B"), key=depth)
labels = dict(C1="DIRECTION-ABSENT", C2="UNSTABLE", C3="NOT-BEYOND-FUNDING", C4="VARIANCE", C5="NULL", C6="SHIFT")
fail_label = None if verdict == "PASS" else ("PRECONDITION" if not pre_ok else labels[order[depth(best)]])
st1 = C.sysstate(); assert st1["gpu"].replace(" ", "") == "0%,2MiB", st1["gpu"]
rep.update(per_seed=per_seed, passing_cells=passing, verdict=verdict, fail_label=fail_label, closest_cell=best, closest_cell_depth=depth(best),
           sys_after=st1, wall_s=round(time.time() - T_START, 1))
C.jdump(rep, os.path.join(C.L2, "receipts", "RECEIPT_L2_B_judge.json"))
for s in C.SEEDS:
    for c, v in per_seed[s]["reading"].items():
        m, T = c.split("_"); cell = per_seed[s]["stats"]["P_all|%s" % T]["%s|FULL" % m]
        print("seed %s %s G %.3f %s dG %.3f %s TB_ci %s H %.3f %s Gmed %.3f years %s z %.2f q05 %.2f spec0 %s -> %s %s" % (
            s, c, cell["G"], [round(x, 3) for x in cell["G_ci"]], cell["dG_vs_BASE"], [round(x, 3) for x in cell["dG_vs_BASE_ci"]],
            [round(x, 3) for x in cell["TB_ci"]], cell["H"], [round(x, 3) for x in cell["H_ci"]], cell["G_med"],
            {y: (round(g, 2) if g is not None else None) for y, g in cell["G_years"].items()}, cell["z"], cell["q05"], cell["shift_peak_forward_is_0"],
            json.dumps(v["conds"]), v["first_fail"]), flush=True)
print("SUMMARY l2_b_judge verdict=%s label=%s passing=%s closest=%s wall=%.0fs" % (verdict, fail_label, passing, best, rep["wall_s"]), flush=True)
