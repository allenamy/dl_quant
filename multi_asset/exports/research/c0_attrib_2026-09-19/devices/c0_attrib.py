#!/usr/bin/env python3
"""c0_attrib.py — stream C0 step 3: descriptive per-name / per-cohort attribution of the in-role replay book (realcost A0, s42 and s2027).
Implements §1 of docs/RESULT_c0_attribution_2026-09-19.md VERBATIM; §1 and this device were committed BEFORE this device's first run
(no cohort P&L existed before that commit). pod2, CPU, read-only on every input; writes only OUT_DIR.

Accounting (c0_lib.per_name = w10_health.py 8684d9a9 L284–325, reproduced on every anchor by c0_repro.py, and re-gated here):
  per anchor E and member name k: price_k = smr_k·y4_k·1e4, carry_k = smr_k·f_k·4/iv_k·1e4 (+ = pays), fee_k = |smr_k − smr_k(prev)|·blend_k;
  judge units: divide by gross_total(E); a window's cohort value = (1/N_E) Σ_{E in window} Σ_{k in cohort(E)} x_k/gt(E).
  net = price − carry − fee. Σ over the cohorts of any characteristic (incl. NA) = the window's g component exactly (checked).
  Names held outside the member set = pseudo-cohort OUT: gross only, zero P&L by device construction.
Side: long if smr_k(E) > 0, short if < 0; if smr_k(E) == 0 the side of the previous recorded anchor (exit fees); both 0 ⇒ nothing.
Cohorts at E (values from c0_chars.npz; see §1 for the reasons):
  AGE   fixed: <90d, 90–180d, 180–365d, 365–730d, >=730d  (left-censored names: first traded bar 2022-01-01T00:05Z ⇒ always in >=730d)
  FUND  fixed on RN8 in bp/8h: <=−10 | (−10,0) | [0, 0.999) | base [0.999, 1.001] | (1.001, 5] | >5
  MOM7, MOM30, LIQ, TBF   terciles among the anchor's members with a finite value: q = np.quantile(v, [1/3, 2/3]); L: v < q1, H: v > q2,
                          M: closed middle (same rule as G0 §2); NaN ⇒ NA
  FSIG  fixed thirds of the fund leg's own rank position z in the 829 base: z < −1/6 | [−1/6, 1/6] | z > 1/6
Windows: every UTC month 2025-01 … 2026-08 (last anchor = UB 2026-08-30T20Z), 2025, 2026H1 (2026-01-01 … 06-30), ALL (2025-01 … 2026-08).
Outputs: OUT_DIR/C0_ATTRIB.json (every number) + OUT_DIR/C0_TABLES.md (every table, both seeds, every cohort) + receipt.
usage: python c0_attrib.py <OUT_DIR> <CHARS_NPZ>
"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c0_lib as L

T0 = time.time(); OUT = sys.argv[1]; CHARS = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
CHARS_SHA = "403957a21ff7d4be7f06c1c1a038a2b841bb14a567fade1181b3faa29d89c5be"   # c0_chars.py f4c13d76 output (RECEIPT_c0_chars.json 7ce6d737)
chk = L.Checks(T0)
rec = {"device": "c0_attrib.py", "self_sha256": L.sha(os.path.abspath(__file__)), "lib_sha256": L.sha(L.__file__), "numpy": np.__version__, "argv": sys.argv,
       "env": {k: os.environ[k] for k in sorted(os.environ)}, "utc_start": L.utc(time.time())}
rec["inputs"] = L.verify_inputs(chk, L.INPUTS)
got = L.sha(CHARS); rec["inputs"]["CHARS"] = {"path": CHARS, "sha256": got}; chk("input_sha.CHARS", got == CHARS_SHA, {"expected": CHARS_SHA[:12], "got": got[:12]})
if chk.fails:
    json.dump(rec | {"checks": chk.rows, "failed": chk.fails, "VERDICT": "REFUSED"}, open(f"{OUT}/RECEIPT_c0_attrib.json", "w"), indent=1); sys.exit(3)

C = L.load_common(chk)
Z = np.load(CHARS, allow_pickle=True); AX = Z["ts"].astype(np.int64); NA_ = len(AX); SYM = [str(s) for s in Z["symbols"]]
chk("chars.symbols", SYM == C["SYM"])
MEMB = Z["member"]
CENS_TS = 1640995500   # 2022-01-01T00:05Z = first traded bar of the cache (row 1); 136 names start there
first_ts = Z["first_trade_ts"].astype(np.int64)
rec["age_left_censored_names"] = int(((first_ts > 0) & (first_ts <= CENS_TS)).sum())

# ---------------- cohort labels (frozen §1) ----------------
def lab_fixed_age(x):
    out = np.full(x.shape, -1, np.int8); ok = np.isfinite(x)
    out[ok] = np.digitize(x[ok], [90.0, 180.0, 365.0, 730.0]).astype(np.int8); return out
def lab_fund(rn8):
    b = rn8 * 1e4; out = np.full(b.shape, -1, np.int8); ok = np.isfinite(b)
    out[ok & (b <= -10)] = 0; out[ok & (b > -10) & (b < 0)] = 1; out[ok & (b >= 0) & (b < 0.999)] = 2
    out[ok & (b >= 0.999) & (b <= 1.001)] = 3; out[ok & (b > 1.001) & (b <= 5)] = 4; out[ok & (b > 5)] = 5; return out
def lab_terc(X):
    out = np.full(X.shape, -1, np.int8)
    for a in range(X.shape[0]):
        v = X[a].astype(np.float64); mk = MEMB[a] & np.isfinite(v)
        if mk.sum() < 3: continue
        q1, q2 = np.quantile(v[mk], [1 / 3, 2 / 3]); f = np.isfinite(v)
        out[a, f] = np.where(v[f] < q1, 0, np.where(v[f] > q2, 2, 1)).astype(np.int8)
    return out
def lab_fsig(z):
    out = np.full(z.shape, -1, np.int8); ok = np.isfinite(z)
    out[ok & (z < -1 / 6)] = 0; out[ok & (z >= -1 / 6) & (z <= 1 / 6)] = 1; out[ok & (z > 1 / 6)] = 2; return out
CHAR_DEF = {
    "AGE": (lab_fixed_age(Z["AGE"].astype(np.float64)), ["<90d", "90-180d", "180-365d", "365-730d", ">=730d"]),
    "FUND": (lab_fund(Z["RN8"].astype(np.float64)), ["<=-10bp", "(-10,0)bp", "[0,base)", "base 1bp", "(base,5]bp", ">5bp"]),
    "MOM7": (lab_terc(Z["MOM7"]), ["L", "M", "H"]), "MOM30": (lab_terc(Z["MOM30"]), ["L", "M", "H"]),
    "LIQ": (lab_terc(Z["LIQ"]), ["L", "M", "H"]), "TBF": (lab_terc(Z["TBF"]), ["L", "M", "H"]),
    "FSIG": (lab_fsig(Z["FSIG"].astype(np.float64)), ["bottom", "mid", "top"]),
}
EXCL_DEF = {"LIQ": lab_terc(Z["LIQ_EXCL"]), "TBF": lab_terc(Z["TBF_EXCL"])}
CHARV = {k: Z[k].astype(np.float64) for k in ("AGE", "RN8", "MOM7", "MOM30", "LIQ", "TBF", "FSIG")}
chk.log("labels built")

mon = np.array([time.strftime("%Y-%m", time.gmtime(int(t))) for t in AX]); day = np.array([time.strftime("%Y-%m-%d", time.gmtime(int(t))) for t in AX])
months = sorted(set(mon.tolist()))
WINDOWS = {**{m_: mon == m_ for m_ in months}, "2025": np.char.startswith(mon, "2025"), "2026H1": np.isin(mon, ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]),
           "ALL": np.ones(NA_, bool)}
chk("windows.2026H1_anchor_count_equals_G0", int(WINDOWS["2026H1"].sum()) == 1086, {"n": int(WINDOWS["2026H1"].sum())})
TOP_MONTHS = ["2026-04", "2026-06", "2026-07", "2026-08"]
res = {"definitions": __doc__, "months": months, "seeds": {}}

for seed in L.SEEDS:
    A = L.load_arm(seed, chk); R = A["R"]; cols = A["cols"]; ts = R[:, 0].astype(np.int64); col = lambda n: R[:, cols.index(n)]
    rows = np.nonzero((ts >= AX[0]) & (ts <= AX[-1]))[0]
    chk(f"s{seed}.axis_equals_chars", bool(np.array_equal(ts[rows], AX)))
    keep = np.zeros(len(ts), bool); keep[rows] = True; keep[rows[0] - 1] = True        # + the row before (previous side for exits)
    P, S = L.per_name(A, C, keep_rows=keep)
    # re-gate the accounting on the window rows (identical to c0_repro R1–R3)
    for nm, sab in (("pnl_ex", "S_abs_price"), ("carry_ex", "S_abs_carry"), ("cost_ex", "S_abs_cost")):
        d = np.abs(S[nm][rows] - col(nm)[rows]); tol = 1e-6 * np.maximum(np.abs(col(nm)[rows]), S[sab][rows])
        chk(f"s{seed}.regate_{nm}", bool((d <= tol).all()), {"max_abs_diff": float(d.max())})
    smr_all = P["smr"]; prev_side = np.sign(smr_all[0]); smr = smr_all[1:]; inm = P["inm"][1:]
    gt = col("gross_total")[rows]
    Pn = P["price"][1:] / gt[:, None]; Cn = P["carry"][1:] / gt[:, None]; Fn = P["fee"][1:] / gt[:, None]; Gn = np.abs(smr) / gt[:, None]
    sgn = np.sign(smr); prv = np.vstack([prev_side[None, :], np.sign(smr[:-1])]); sgn = np.where(sgn == 0, prv, sgn)
    valid = inm & (sgn != 0)
    Nn = Pn - Cn - Fn
    OUTG = (np.abs(smr) * (~inm)).sum(1) / gt
    # identity: per-anchor sums of the normalised, side-masked per-name terms = the same device's per-anchor sums / gt (nothing dropped by the
    # side/validity masks); equality with the rec columns is the regate above (float32-W scale tolerance, c0_repro R1–R3)
    for nm, X in (("pnl_ex", Pn), ("carry_ex", Cn), ("cost_ex", Fn)):
        d = np.abs(np.where(valid, X, 0).sum(1) - S[nm][rows] / gt)
        chk(f"s{seed}.identity_{nm}_per_anchor", bool((d <= 1e-9 * np.maximum(1, np.abs(S[nm][rows] / gt))).all()), {"max_abs": float(d.max())})
    SR = {}
    rec_cols = {"leg_fund": col("leg_fund")[rows], "w3_fund": col("w3_fund")[rows], "leg_king": col("leg_king")[rows], "w3_king": col("w3_king")[rows]}
    lmap = {int(t): k for k, t in enumerate(A["legs_ts"])}; li = np.array([lmap[int(t)] for t in ts[rows]])
    legs_fund_si = A["legs_fund"][li]; legs_king_si = A["legs_king"][li]; leg_fund_raw = S["leg_fund_raw"][rows]

    def cohort_table(W, lab, ncode):
        N = int(W.sum()); key_ok = valid & W[:, None]
        key = (np.where(sgn > 0, 0, 1) * (ncode + 1) + (lab.astype(np.int64) + 1))[key_ok]
        out = {}
        for nm, X in (("price", Pn), ("carry", Cn), ("fee", Fn), ("net", Nn), ("gross", Gn)):
            v = np.bincount(key, weights=X[key_ok], minlength=2 * (ncode + 1)) / N
            out[nm] = {"long": v[:ncode + 1].tolist(), "short": v[ncode + 1:].tolist()}     # index 0 = NA, 1.. = codes
        return out

    seedres = {"windows": {}, "top20": {}, "concentration": {}, "days": {}, "legs": {}, "excl_sensitivity": {}}
    for wn, W in WINDOWS.items():
        N = int(W.sum())
        comp = {k: float(np.where(valid & W[:, None], X, 0).sum() / N) for k, X in (("price", Pn), ("carry", Cn), ("fee", Fn), ("net", Nn))}
        ref = {k: float((col(c)[rows][W] / gt[W]).mean()) for k, c in (("price", "pnl_ex"), ("carry", "carry_ex"), ("fee", "cost_ex"))}
        ref["net"] = float((col("net_ex")[rows][W] / gt[W]).mean())
        chk(f"s{seed}.{wn}.components_equal_judge_means", all(abs(comp[k] - ref[k]) <= 1e-6 * max(1, abs(ref[k])) for k in comp), {"attrib": comp, "judge": ref}) if wn in ("ALL", "2026H1", "2026-08") else None
        wr = {"N": N, "components": comp, "judge_components": ref, "gross_member": float(np.where(valid & W[:, None], Gn, 0).sum() / N), "gross_outside_members": float(OUTG[W].mean()),
              "by_side": {sd: {k: float(np.where(valid & W[:, None] & ((sgn > 0) if sd == "long" else (sgn < 0)), X, 0).sum() / N) for k, X in (("price", Pn), ("carry", Cn), ("fee", Fn), ("net", Nn), ("gross", Gn))}
                          for sd in ("long", "short")}, "chars": {}}
        for cn, (lab, names) in CHAR_DEF.items():
            t = cohort_table(W, lab, len(names)); t["codes"] = ["NA"] + names
            for sd in ("long", "short"):   # identity: Σ cohorts = side totals
                for k in ("price", "carry", "fee", "net"):
                    if abs(sum(t[k][sd]) - wr["by_side"][sd][k]) > 1e-9 * max(1, abs(wr["by_side"][sd][k])): chk(f"s{seed}.{wn}.{cn}.{sd}.{k}.cohorts_sum_to_side", False)
            wr["chars"][cn] = t
        seedres["windows"][wn] = wr
    chk(f"s{seed}.cohort_identities_all_windows", True, {"windows": len(WINDOWS)})

    # ---------------- per-name windows: top-20, concentration ----------------
    def per_name_window(W):
        N = int(W.sum()); m_ = valid & W[:, None]
        d = {k: np.where(m_, X, 0).sum(0) / N for k, X in (("price", Pn), ("carry", Cn), ("fee", Fn), ("net", Nn), ("gross", Gn))}
        held = (m_ & (smr != 0)); d["held"] = held.sum(0); d["long_share"] = np.where(d["held"] > 0, (held & (smr > 0)).sum(0) / np.maximum(d["held"], 1), np.nan)
        for sd, sm_ in (("long", sgn > 0), ("short", sgn < 0)):
            d[f"price_{sd}"] = np.where(m_ & sm_, Pn, 0).sum(0) / N; d[f"net_{sd}"] = np.where(m_ & sm_, Nn, 0).sum(0) / N
        return d, held
    for wn in TOP_MONTHS + ["2026H1"]:
        W = WINDOWS[wn]; d, held = per_name_window(W)
        order = np.argsort(-np.abs(d["net"]))[:20]
        lst = []
        for k in order:
            hk = held[:, k]; med = {cn: (float(np.median(CHARV[cn][hk, k])) if hk.any() else None) for cn in CHARV}
            labs = {cn: (CHAR_DEF[cn][1][int(np.bincount(CHAR_DEF[cn][0][hk, k][CHAR_DEF[cn][0][hk, k] >= 0]).argmax())] if (hk.any() and (CHAR_DEF[cn][0][hk, k] >= 0).any()) else "NA") for cn in CHAR_DEF}
            lst.append({"symbol": SYM[k], **{x: float(d[x][k]) for x in ("net", "price", "carry", "fee", "gross", "price_long", "price_short")}, "held_anchors": int(d["held"][k]),
                        "long_share": float(d["long_share"][k]) if np.isfinite(d["long_share"][k]) else None, "median_chars": med, "modal_cohort": labs})
        if wn in TOP_MONTHS: seedres["top20"][wn] = lst
        # concentration
        net = d["net"]; pr = d["price"]; act = d["gross"] > 0
        c = {"total_net": float(net.sum()), "total_price": float(pr.sum()), "n_names_held": int(act.sum()), "n_names_net_neg": int((act & (net < 0)).sum()),
             "gross_share_in_net_neg_names": float(d["gross"][act & (net < 0)].sum() / d["gross"][act].sum()),
             "effective_n_abs_net": float(np.abs(net).sum() ** 2 / max((net ** 2).sum(), 1e-300))}
        s_ = np.sort(net)
        for kk in (5, 10, 20, 50):
            c[f"worst{kk}_net_sum"] = float(s_[:kk].sum()); c[f"best{kk}_net_sum"] = float(s_[-kk:].sum()); c[f"leave_worst{kk}_out_net"] = float(net.sum() - s_[:kk].sum())
            c[f"leave_best{kk}_out_net"] = float(net.sum() - s_[-kk:].sum())
        for sd in ("long", "short"):
            v = d[f"net_{sd}"]; sv = np.sort(v)
            c[f"{sd}_total_net"] = float(v.sum()); c[f"{sd}_worst10_net_sum"] = float(sv[:10].sum()); c[f"{sd}_best10_net_sum"] = float(sv[-10:].sum())
            c[f"{sd}_price_total"] = float(d[f"price_{sd}"].sum())
        seedres["concentration"][wn] = c
        # days
        dd = {}
        for dy in sorted(set(day[W].tolist())):
            Wd = W & (day == dy)
            dd[dy] = {k: float(np.where(valid & Wd[:, None] & sm_, X, 0).sum() / W.sum()) for k, X, sm_ in
                      (("price_long", Pn, sgn > 0), ("price_short", Pn, sgn < 0), ("carry", Cn, sgn != 0), ("net", Nn, sgn != 0))}
        nets = np.array([v["net"] for v in dd.values()]); srt = np.sort(nets)
        seedres["days"][wn] = {"by_day": dd, "n_days": len(dd), "worst5_days_net_sum": float(srt[:5].sum()), "best5_days_net_sum": float(srt[-5:].sum()), "total_net": float(nets.sum()),
                               "n_days_net_neg": int((nets < 0).sum())}
    # ---------------- legs per month ----------------
    for wn in months + ["2025", "2026H1", "ALL"]:
        W = WINDOWS[wn]; w3f = rec_cols["w3_fund"][W]; w3k = rec_cols["w3_king"][W]; okf = w3f > 0.05; okk = w3k > 0.05
        seedres["legs"][wn] = {"N": int(W.sum()), "w3_fund_mean": float(w3f.mean()), "w3_king_mean": float(w3k.mean()),
                               "leg_fund_seatweighted_mean": float(rec_cols["leg_fund"][W].mean()), "leg_king_seatweighted_mean": float(rec_cols["leg_king"][W].mean()),
                               "fund_raw_by_division_mean": float((rec_cols["leg_fund"][W][okf] / w3f[okf]).mean()) if okf.any() else None, "fund_division_n_used": int(okf.sum()),
                               "fund_raw_recomputed_mean": float(leg_fund_raw[W].mean()), "fund_raw_recomputed_mean_same_anchors": float(leg_fund_raw[W][okf].mean()) if okf.any() else None,
                               "fund_seat_input_mean": float(legs_fund_si[W].mean()),
                               "king_raw_by_division_mean": float((rec_cols["leg_king"][W][okk] / w3k[okk]).mean()) if okk.any() else None, "king_division_n_used": int(okk.sum()),
                               "king_seat_input_mean": float(legs_king_si[W].mean())}
    # ---------------- EXCL sensitivity (LIQ, TBF) ----------------
    for wn in ("2026-08", "2026H1"):
        W = WINDOWS[wn]; m_ = valid & W[:, None]
        for cn, labx in EXCL_DEF.items():
            labi = CHAR_DEF[cn][0]; diff = m_ & (labi != labx)
            seedres["excl_sensitivity"][f"{wn}.{cn}"] = {"gross_share_label_differs": float(Gn[diff].sum() / Gn[m_].sum()), "table_excl": cohort_table(W, labx, 3)}
    res["seeds"][f"A0_s{seed}"] = seedres
    chk.log("seed done", seed)

json.dump(res, open(f"{OUT}/C0_ATTRIB.json", "w"), indent=0, default=float)

# ---------------- render tables ----------------
f2 = lambda x: "—" if x is None else f"{x:+.2f}"
f3 = lambda x: "—" if x is None else f"{x:.3f}"
Lm = [f"# C0 attribution tables (c0_attrib.py {rec['self_sha256'][:8]}; both in-role arms A0 s42 / s2027; unit = bps per anchor per unit gross, judge caliber)", "",
      "Every cohort, every month, both seeds. Cohort cells are additive: Σ over a characteristic's cohorts (incl. NA) = the side total; long + short = the window's g component.",
      "price = price P&L contribution; carry = funding PAID (+ = paid; enters g with a minus sign); net = price − carry − fee; gross = mean share of gross_total held in the cohort.", ""]
wl = months + ["2025", "2026H1", "ALL"]
for sk, sr in res["seeds"].items():
    Lm += [f"## {sk}", "", "### Window totals", "", "| window | N | price | carry | fee | net (= g) | long price | long carry | short price | short carry | gross member | gross outside members |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for wn in wl:
        w = sr["windows"][wn]; c_ = w["components"]; b = w["by_side"]
        Lm.append(f"| {wn} | {w['N']} | {f2(c_['price'])} | {f2(c_['carry'])} | {f2(c_['fee'])} | {f2(c_['net'])} | {f2(b['long']['price'])} | {f2(b['long']['carry'])} | {f2(b['short']['price'])} | {f2(b['short']['carry'])} | {f3(w['gross_member'])} | {f3(w['gross_outside_members'])} |")
    Lm.append("")
    for cn in CHAR_DEF:
        codes = sr["windows"]["ALL"]["chars"][cn]["codes"]
        for comp_ in ("price", "carry", "net", "gross", "price_per_gross"):
            hdr = [f"L:{c}" for c in codes] + [f"S:{c}" for c in codes]
            Lm += [f"### {sk} · {cn} · {comp_}" + (" (= price / gross: the cohort's price return per unit of its own gross; — if gross < 0.002)" if comp_ == "price_per_gross" else ""), "",
                   "| window | " + " | ".join(hdr) + " |", "|---|" + "---|" * len(hdr)]
            for wn in wl:
                tc = sr["windows"][wn]["chars"][cn]
                if comp_ == "price_per_gross":
                    vals = [(p / g if g >= 0.002 else None) for p, g in zip(tc["price"]["long"] + tc["price"]["short"], tc["gross"]["long"] + tc["gross"]["short"])]
                else:
                    vals = tc[comp_]["long"] + tc[comp_]["short"]
                Lm.append(f"| {wn} | " + " | ".join((f3(v) if comp_ == "gross" else f2(v)) for v in vals) + " |")
            Lm.append("")
    for wn, lst in sr["top20"].items():
        Lm += [f"### {sk} · top-20 names by |net| · {wn}", "", "| # | symbol | net | price | carry | fee | gross | held anchors | long share | AGE d | RN8 bp | MOM7 | MOM30 | LIQ | TBF | FSIG | modal cohorts (AGE/FUND/MOM7/MOM30/LIQ/TBF/FSIG) |",
               "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r_, x in enumerate(lst, 1):
            mc = x["median_chars"]; ml = x["modal_cohort"]
            def g_(k, s=1.0, fmt="{:.2f}"): return "—" if mc[k] is None else fmt.format(mc[k] * s)
            ls_ = "—" if x["long_share"] is None else "{:.2f}".format(x["long_share"])
            Lm.append(f"| {r_} | {x['symbol']} | {f2(x['net'])} | {f2(x['price'])} | {f2(x['carry'])} | {f2(x['fee'])} | {x['gross']:.4f} | {x['held_anchors']} | {ls_} | "
                      f"{g_('AGE', fmt='{:.0f}')} | {g_('RN8', 1e4)} | {g_('MOM7', fmt='{:+.3f}')} | {g_('MOM30', fmt='{:+.3f}')} | {g_('LIQ')} | {g_('TBF', fmt='{:.3f}')} | {g_('FSIG', fmt='{:+.2f}')} | "
                      + "/".join(ml[c] for c in CHAR_DEF) + " |")
        Lm.append("")
    Lm += [f"### {sk} · concentration", "", "| window | total net | worst5 | worst10 | worst20 | worst50 | best5 | best10 | best20 | leave-worst10-out | leave-best10-out | names held | names net<0 | gross share in net<0 names | eff. N (|net|) | long net | short net | long worst10 | short worst10 |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for wn, c_ in sr["concentration"].items():
        Lm.append(f"| {wn} | {f2(c_['total_net'])} | {f2(c_['worst5_net_sum'])} | {f2(c_['worst10_net_sum'])} | {f2(c_['worst20_net_sum'])} | {f2(c_['worst50_net_sum'])} | {f2(c_['best5_net_sum'])} | {f2(c_['best10_net_sum'])} | {f2(c_['best20_net_sum'])} | "
                  f"{f2(c_['leave_worst10_out_net'])} | {f2(c_['leave_best10_out_net'])} | {c_['n_names_held']} | {c_['n_names_net_neg']} | {f3(c_['gross_share_in_net_neg_names'])} | {c_['effective_n_abs_net']:.1f} | {f2(c_['long_total_net'])} | {f2(c_['short_total_net'])} | {f2(c_['long_worst10_net_sum'])} | {f2(c_['short_worst10_net_sum'])} |")
    Lm += ["", f"### {sk} · days (contribution of each UTC day to the window mean)", "", "| window | days | days net<0 | total net | worst-5-day sum | best-5-day sum |", "|---|---|---|---|---|---|"]
    for wn, dd in sr["days"].items():
        Lm.append(f"| {wn} | {dd['n_days']} | {dd['n_days_net_neg']} | {f2(dd['total_net'])} | {f2(dd['worst5_days_net_sum'])} | {f2(dd['best5_days_net_sum'])} |")
    Lm += ["", f"#### {sk} · 2026-08 by day", "", "| day | price long | price short | carry | net |", "|---|---|---|---|---|"]
    for dy, v in sr["days"]["2026-08"]["by_day"].items():
        Lm.append(f"| {dy} | {f2(v['price_long'])} | {f2(v['price_short'])} | {f2(v['carry'])} | {f2(v['net'])} |")
    Lm += ["", f"### {sk} · legs per month (bps per anchor per unit LEG gross; target legs before EMA; not additive with g)", "",
           "| window | N | seat fund | seat king | fund seat-weighted (rec leg_fund) | fund RAW = leg_fund/seat, seat>0.05 [n] | fund RAW recomputed (all anchors) | fund seat-input (demeaned, saved legs_fund) | king seat-weighted | king RAW = leg_king/seat, seat>0.05 [n] | king seat-input |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for wn, v in sr["legs"].items():
        Lm.append(f"| {wn} | {v['N']} | {f3(v['w3_fund_mean'])} | {f3(v['w3_king_mean'])} | {f2(v['leg_fund_seatweighted_mean'])} | {f2(v['fund_raw_by_division_mean'])} [{v['fund_division_n_used']}] | {f2(v['fund_raw_recomputed_mean'])} | {f2(v['fund_seat_input_mean'])} | "
                  f"{f2(v['leg_king_seatweighted_mean'])} | {f2(v['king_raw_by_division_mean'])} [{v['king_division_n_used']}] | {f2(v['king_seat_input_mean'])} |")
    Lm += ["", f"### {sk} · holefix EXCL sensitivity (LIQ, TBF)", "", "| window.char | gross share whose label differs INCL vs EXCL |", "|---|---|"]
    for k, v in sr["excl_sensitivity"].items(): Lm.append(f"| {k} | {v['gross_share_label_differs']:.4f} |")
    Lm.append("")
open(f"{OUT}/C0_TABLES.md", "w").write("\n".join(Lm) + "\n")
rec["outputs"] = {k: {"path": f"{OUT}/{k}", "sha256": L.sha(f"{OUT}/{k}")} for k in ("C0_ATTRIB.json", "C0_TABLES.md")}
rec.update({"checks": chk.rows, "n_checks": len(chk.rows), "failed": chk.fails, "VERDICT": "PASS" if not chk.fails else "FAIL", "runtime_s": round(time.time() - T0, 1), "utc_end": L.utc(time.time())})
json.dump(rec, open(f"{OUT}/RECEIPT_c0_attrib.json", "w"), indent=1, default=str)
chk.log("VERDICT", rec["VERDICT"], "failed", chk.fails)
sys.exit(0 if not chk.fails else 3)
