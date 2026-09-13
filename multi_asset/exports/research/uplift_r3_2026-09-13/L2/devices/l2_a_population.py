"""l2_a_population.py — L2 Stage A, pod2 side: the A0 fund-leg short population and its per-year size (DATA FACTS ONLY).
Population P_i (rec row i in W_FULL): n ∈ device member set m_i (T1MEM) ∧ executed reshaped position smr_n < 0 ∧ fund-leg component of
smr_n < 0 (T1SMR leg 2). Reads no return array (asserted through LoggedNpz); rec is read for ts / gross_total only.
Also writes the per-seed population arrays (mask, smr, fund component, device rn8) for the later coverage join, and the union
(symbol, UTC day) request set a metrics rebuild would need (population days + 1-day halo), per year.
Run: bash devices/run_l2.sh l2_a_population.py   (env -i whitelist, nice 10, taskset 8 cores; foreground)"""
import os, sys, time, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C

T_START = time.time()
envrep = C.check_env(sys.argv)
st0 = C.sysstate()
assert st0["gpu"].replace(" ", "") == "0%,2MiB", ("GPU not idle before run", st0["gpu"])
dev_sha = {f: C.sha256(os.path.join(C.L2, "devices", f)) for f in ("l2_common.py", "l2_a_population.py", "run_l2.sh")}
inputs = C.input_shas(check=True)
D, readers = C.load_axis_and_masks()
YEARS = (2022, 2023, 2024, 2025, 2026)
DAY = 86400
rep = dict(device="l2_a_population.py", device_sha256=dev_sha, env=envrep, sys_before=st0, inputs=inputs,
           definition=dict(population="member(T1MEM) & smr<-1e-12 & smr_fund_component<-1e-12, rec rows 0..10037 (W_FULL, ts<=2026-08-30 20Z)",
                           smr="sum over legs of T1SMR (king,rev24,fund,f10) = executed reshaped position; checked against reshape(W)",
                           rn8_device="f_fund_now*(8/f_fund_iv if >0 else 8), NaN->0 (A0 device _fnp); FTRIM zone rn8<=-0.0010",
                           short_gross="sum |smr| (book units); fund_comp_gross = sum |fund component|",
                           rn8_buckets="ftrim_zone rn8<=-0.0010 | mildneg -0.0010<rn8<0 | exact_zero rn8==0 (incl. NaN->0) | positive rn8>0; negfund_subpop = ftrim_zone+mildneg",
                           halo_days="for each population row: UTC days of E-24h-5min .. E (features need <=24h+1 bar of metrics history)"),
           per_seed={})
yr_all = C.year_of(D["PTS"][:C.N_FULL])
union_days = set(); union_names = {y: set() for y in YEARS}
for s in C.SEEDS:
    A = C.load_arm(s, D)
    ts = A["ts"][:C.N_FULL]; gt = A["rec"][:C.N_FULL, A["cols"].index("gross_total")]
    Pm = np.zeros((C.N_FULL, C.NW), bool); SMR = np.zeros((C.N_FULL, C.NW), np.float32); FC = np.zeros((C.N_FULL, C.NW), np.float32)
    RN8 = np.zeros((C.N_FULL, C.NW), np.float32)
    chk = dict(max_abs_smr_vs_reshapeW=0.0, max_T1ID_sum_legs_minus_smr=float(np.abs(A["T1ID"][:C.N_FULL, 0]).max()),
               mem_vs_qvkfinite_and_umask_mismatch_cells=0, nonmember_nonzero_cells=0, nonmember_abs_smr_sum=0.0,
               max_abs_rn8_device_vs_T1RN_on_members=0.0, max_abs_gross_total_minus_sum_abs_smr=0.0, rows_empty_population=0)
    per_row = dict(n=np.zeros(C.N_FULL, np.int64), g=np.zeros(C.N_FULL), fg=np.zeros(C.N_FULL), bs_n=np.zeros(C.N_FULL, np.int64),
                   bs_g=np.zeros(C.N_FULL), fs_g=np.zeros(C.N_FULL), book_g=np.zeros(C.N_FULL),
                   ftz_n=np.zeros(C.N_FULL, np.int64), ftz_g=np.zeros(C.N_FULL), neg_n=np.zeros(C.N_FULL, np.int64), neg_g=np.zeros(C.N_FULL),
                   pos_n=np.zeros(C.N_FULL, np.int64), pos_g=np.zeros(C.N_FULL), zero_n=np.zeros(C.N_FULL, np.int64), zero_g=np.zeros(C.N_FULL),
                   nan_n=np.zeros(C.N_FULL, np.int64))
    rn8_vals_by_year = {y: [] for y in YEARS}; negnames_by_year = {y: set() for y in YEARS}
    names_by_year = {y: set() for y in YEARS}
    for i in range(C.N_FULL):
        j = i; k = i + C.META_OFF
        mem = A["MEM"][i]
        q = np.nan_to_num(D["QVK"][k], nan=-1.0)
        chk["mem_vs_qvkfinite_and_umask_mismatch_cells"] += int((mem != ((q > -0.5) & D["U"][j])).sum())
        P, smr, fc = C.population_row(A["SMRC"][i], mem)
        chk["max_abs_smr_vs_reshapeW"] = max(chk["max_abs_smr_vs_reshapeW"], float(np.abs(smr - C.reshape_row(A["W"][i])).max()))
        off = (~mem) & (np.abs(smr) > C.DUST)
        chk["nonmember_nonzero_cells"] += int(off.sum()); chk["nonmember_abs_smr_sum"] += float(np.abs(smr[off]).sum())
        rn8 = C.rn8_device(D, j)
        if mem.any():
            chk["max_abs_rn8_device_vs_T1RN_on_members"] = max(chk["max_abs_rn8_device_vs_T1RN_on_members"],
                                                               float(np.nanmax(np.abs(rn8[mem] - A["RN"][i][mem].astype(np.float64)))))
        chk["max_abs_gross_total_minus_sum_abs_smr"] = max(chk["max_abs_gross_total_minus_sum_abs_smr"], abs(float(gt[i]) - float(np.abs(smr).sum())))
        Pm[i] = P; SMR[i, P] = smr[P]; FC[i, P] = fc[P]; RN8[i, P] = rn8[P]
        a = np.abs(smr)
        bs = mem & (smr < -C.DUST); fs = mem & (fc < -C.DUST)
        per_row["n"][i] = int(P.sum()); per_row["g"][i] = float(a[P].sum()); per_row["fg"][i] = float(np.abs(fc[P]).sum())
        per_row["bs_n"][i] = int(bs.sum()); per_row["bs_g"][i] = float(a[bs].sum()); per_row["fs_g"][i] = float(np.abs(fc[fs]).sum())
        per_row["book_g"][i] = float(a.sum())
        fin = np.isfinite(D["FN"][j])
        ftz = P & (rn8 <= C.FTRIM_TH); neg = P & (rn8 > C.FTRIM_TH) & (rn8 < 0.0); pos = P & (rn8 > 0.0); zer = P & (rn8 == 0.0)
        per_row["zero_n"][i] = int(zer.sum()); per_row["zero_g"][i] = float(a[zer].sum())
        per_row["ftz_n"][i] = int(ftz.sum()); per_row["ftz_g"][i] = float(a[ftz].sum())
        per_row["neg_n"][i] = int(neg.sum()); per_row["neg_g"][i] = float(a[neg].sum())
        per_row["pos_n"][i] = int(pos.sum()); per_row["pos_g"][i] = float(a[pos].sum())
        per_row["nan_n"][i] = int((P & ~fin).sum())
        if not P.any():
            chk["rows_empty_population"] += 1
        y = int(yr_all[i])
        rn8_vals_by_year[y].append(rn8[P].astype(np.float32))
        for n in np.nonzero(ftz | neg)[0]:
            negnames_by_year[y].add(int(n))
        idx = np.nonzero(P)[0]
        for n in idx:
            names_by_year[y].add(int(n)); union_names[y].add(int(n))
        if idx.size:
            d_lo = (int(ts[i]) - DAY - 300) // DAY; d_hi = int(ts[i]) // DAY
            for n in idx:
                for d in range(d_lo, d_hi + 1):
                    union_days.add((int(n), d))
    # hard gates on the population instrument
    assert chk["max_abs_smr_vs_reshapeW"] <= 1e-6, ("T1SMR legs do not sum to reshape(W)", chk["max_abs_smr_vs_reshapeW"])
    assert chk["mem_vs_qvkfinite_and_umask_mismatch_cells"] == 0, ("T1MEM != qvk-finite ∩ UMASK", chk["mem_vs_qvkfinite_and_umask_mismatch_cells"])
    assert chk["max_abs_rn8_device_vs_T1RN_on_members"] <= 1e-6, ("device rn8 != T1RN", chk["max_abs_rn8_device_vs_T1RN_on_members"])
    tab = {}
    for y in YEARS:
        r = yr_all == y
        n = per_row["n"][r]; tot_n = int(n.sum())
        tab[str(y)] = dict(
            anchors=int(r.sum()), first=C.utc(ts[r][0]), last=C.utc(ts[r][-1]), anchors_with_population=int((n > 0).sum()),
            population_rows=tot_n, per_anchor_mean=float(n.mean()), per_anchor_median=float(np.median(n)),
            per_anchor_p10=float(np.percentile(n, 10)), per_anchor_p90=float(np.percentile(n, 90)), distinct_names=len(names_by_year[y]),
            population_short_gross_sum=float(per_row["g"][r].sum()), book_short_gross_sum=float(per_row["bs_g"][r].sum()),
            share_of_book_short_gross_in_population=float(per_row["g"][r].sum() / max(per_row["bs_g"][r].sum(), 1e-300)),
            share_of_book_short_count_in_population=float(tot_n / max(int(per_row["bs_n"][r].sum()), 1)),
            fund_comp_short_gross_sum=float(per_row["fs_g"][r].sum()),
            share_of_fund_comp_short_gross_in_population=float(per_row["fg"][r].sum() / max(per_row["fs_g"][r].sum(), 1e-300)),
            population_gross_over_book_gross=float(per_row["g"][r].sum() / max(per_row["book_g"][r].sum(), 1e-300)),
            rn8_ftrim_zone_share_count=float(per_row["ftz_n"][r].sum() / max(tot_n, 1)),
            rn8_ftrim_zone_share_gross=float(per_row["ftz_g"][r].sum() / max(per_row["g"][r].sum(), 1e-300)),
            rn8_mildneg_share_count=float(per_row["neg_n"][r].sum() / max(tot_n, 1)),
            rn8_mildneg_share_gross=float(per_row["neg_g"][r].sum() / max(per_row["g"][r].sum(), 1e-300)),
            rn8_positive_share_count=float(per_row["pos_n"][r].sum() / max(tot_n, 1)),
            rn8_positive_share_gross=float(per_row["pos_g"][r].sum() / max(per_row["g"][r].sum(), 1e-300)),
            rn8_exact_zero_share_count=float(per_row["zero_n"][r].sum() / max(tot_n, 1)),
            rn8_exact_zero_share_gross=float(per_row["zero_g"][r].sum() / max(per_row["g"][r].sum(), 1e-300)),
            negfund_subpop_rows=int(per_row["ftz_n"][r].sum() + per_row["neg_n"][r].sum()),
            negfund_subpop_gross_sum=float(per_row["ftz_g"][r].sum() + per_row["neg_g"][r].sum()),
            negfund_subpop_per_anchor_mean=float((per_row["ftz_n"][r] + per_row["neg_n"][r]).mean()),
            negfund_subpop_distinct_names=len(negnames_by_year[y]),
            rn8_bp_quantiles_p05_p25_p50_p75_p95=[float(x) for x in (np.percentile(np.concatenate(rn8_vals_by_year[y]) * 1e4, [5, 25, 50, 75, 95])
                                                                     if tot_n else [np.nan] * 5)],
            panel_fund_now_nan_rows_in_population=int(per_row["nan_n"][r].sum()))
    out = os.path.join(C.L2, "out", "L2_A_population_s%s.npz" % s)
    np.savez_compressed(out + ".tmp.npz", ts=ts, symbols=np.array(D["SYM"]), P=Pm, smr=SMR, fund_comp=FC, rn8_device=RN8)
    os.replace(out + ".tmp.npz", out)
    rep["per_seed"][s] = dict(arm_config=A["cfg"], checks=chk, by_year=tab, out=out, out_sha256=C.sha256(out), out_size=os.path.getsize(out))
    print("seed %s checks %s" % (s, json.dumps(chk)), flush=True)
    for y in YEARS:
        t = tab[str(y)]
        print("seed %s %d anchors %d rows %d mean/anchor %.1f names %d share_book_short_gross %.3f gross_shares ftz %.3f mildneg %.3f zero %.3f pos %.3f negsub_rows %d" % (
            s, y, t["anchors"], t["population_rows"], t["per_anchor_mean"], t["distinct_names"], t["share_of_book_short_gross_in_population"],
            t["rn8_ftrim_zone_share_gross"], t["rn8_mildneg_share_gross"], t["rn8_exact_zero_share_gross"], t["rn8_positive_share_gross"],
            t["negfund_subpop_rows"]), flush=True)
    del A
# seed agreement on the population (a population fact, not a return)
Z = [np.load(os.path.join(C.L2, "out", "L2_A_population_s%s.npz" % s))["P"] for s in C.SEEDS]
inter = int((Z[0] & Z[1]).sum()); uni = int((Z[0] | Z[1]).sum())
days_by_year = {}
for (n, d) in union_days:
    y = time.gmtime(d * DAY).tm_year
    days_by_year[y] = days_by_year.get(y, 0) + 1
rep["seed_overlap"] = dict(intersection_rows=inter, union_rows=uni, jaccard=float(inter / max(uni, 1)))
rep["metrics_request_scope_union_seeds"] = dict(symbol_days_by_utc_year={str(k): v for k, v in sorted(days_by_year.items())},
                                                symbol_days_total=len(union_days),
                                                distinct_names_by_year={str(y): len(union_names[y]) for y in YEARS},
                                                distinct_names_total=len(set().union(*union_names.values())),
                                                symbols_total=sorted(D["SYM"][n] for n in set().union(*union_names.values())))
rep["arrays_read"] = C.assert_no_returns_read(readers)
st1 = C.sysstate()
assert st1["gpu"].replace(" ", "") == "0%,2MiB", ("GPU not idle after run", st1["gpu"])
rep["sys_after"] = st1; rep["wall_s"] = round(time.time() - T_START, 1)
C.jdump(rep, os.path.join(C.L2, "receipts", "RECEIPT_L2_A_population.json"))
print("SUMMARY l2_a_population OK seeds=%s jaccard=%.4f symbol_days=%d names=%d wall=%.0fs" % (
    ",".join(C.SEEDS), rep["seed_overlap"]["jaccard"], len(union_days), rep["metrics_request_scope_union_seeds"]["distinct_names_total"], rep["wall_s"]), flush=True)
