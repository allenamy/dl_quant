"""tf_gates.py — pre-gates P0/P0b/P0c/P2 and arm T0 for the TradFi exposure diagnostic.
PREREG docs/PREREG_tradfi_universe_gap_2026-09-24.md (58a29c04a) + AMENDMENT 1 (3b20d1c41).

P0   reproduce lead's six quoted pre-2026 path-mean Sharpes from the three STATS receipts (assert, +-0.005)
P0b  NEW and NC base cells must share device/calibration/price pins (assert)
P0c  compute NEW - NC pre-2026 paired daily difference in bps/day and COMPARE (not assert) to lead's ~2.8 / 0.9
P2   engine pins recorded for later comparison against my own runs
T0   TradFi gross share of NEW's book, per year and pre-2026, both seeds (pure read, no engine)

T0 also decides, by the rule frozen in the prereg BEFORE the number was seen: if the TradFi gross share is
exactly 0 at every anchor then T1a is a bitwise no-op and must be asserted as such rather than run.

usage: env -i PATH=/usr/bin:/bin HOME=/root python -B tf_gates.py PATH,HOME,LC_CTYPE <out.json>
"""
import os, sys, json, time, glob, hashlib, calendar
import numpy as np

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
OUT = sys.argv[2]
OVN = "/dev/shm/ovn_2026-09-23"; NC = "/dev/shm/news2_2026-09-23"; NEWS = "/dev/shm/news_2026-09-23"
ENG = "/dev/shm/fresh_2026-09-23/engine"          # bt_tables / bt_driver_lib, pinned by the FRESH round
NEW_COMBO = "/workspace/old_vs_new_2026-09-23/new_targets"
CRYPTO_NPZ = f"{NEWS}/receipts/P1_members_2025H2on.npz"
# prereg §2 P0: lead's quoted pre-2026 path-mean Sharpes
QUOTED_SHARPE = {"NEW": {"s42": 1.44, "s2027": 1.28}, "NEW_S": {"s42": 1.11, "s2027": 0.96}, "NC": {"s42": 1.02, "s2027": 1.14}}
QUOTED_BPS_GAP = {"s42": 2.8, "s2027": 0.9}       # AMENDMENT 1 P0c: lead's spoken "about"; COMPARE, do not assert
PRE2026 = ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z")
NPATH = 32; H4 = 14400; DAY = 86400
CELLS = {
    "NEW":   {"s42": f"{OVN}/runs/OVN_NEW_s42_scaled_rule_raw_UAFE",  "s2027": f"{OVN}/runs/OVN_NEW_s2027_scaled_rule_raw_UAFE"},
    "NC":    {"s42": f"{NC}/runs/NEWS2_s42_scaled_rule_raw_UAFE",     "s2027": f"{NC}/runs/NEWS2_s2027_scaled_rule_raw_UAFE"},
}
STATS = {"NEW": f"{OVN}/receipts/OVN_STATS.json", "NEW_S": f"{NEWS}/receipts/engine/NEWS_STATS.json",
         "NC": f"{NC}/receipts/engine/NEWS2_STATS.json"}
ARMKEY = {"NEW": {"s42": "NEW_s42", "s2027": "NEW_s2027"}, "NEW_S": {"s42": "NEWS_s42", "s2027": "NEWS_s2027"},
          "NC": {"s42": "NEWS2_s42", "s2027": "NEWS2_s2027"}}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def sharpe_pre2026(receipt, arm_key):
    """tables[arm][base][pre2026].paths.sharpe.path_mean, by EXPLICIT path. Raises if any key is absent.
    No tree-walk and no default: a missing key must fail loudly, not silently resolve to some other arm's number."""
    R = json.load(open(receipt))
    node = R["tables"][arm_key]["base"]["pre2026"]["paths"]["sharpe"]["path_mean"]
    return float(node)


def load_paths(d, tag):
    import bt_tables as BT, bt_driver_lib as DL
    stems = [os.path.join(d, f"PATH_{tag}_seed_{k:02d}") for k in range(NPATH)]
    out = []
    for k, s in enumerate(stems):
        J = json.load(open(s + ".json"))
        assert J["npz_sha256"] == sha(s + ".npz"), f"{s}: npz sha != json"
        assert DL.audits_clean(J["audits"]), f"{s}: audits not clean"
        assert int(J["seed"]) == k
        out.append(BT.series_from_path(np.load(s + ".npz")))
    return out


def seg_mask(A, a, b):
    lo, hi = ts(a), ts(b)
    return (A >= lo) & (A <= hi)


def full_days(A, m):
    d = A[m] // DAY
    u, c = np.unique(d, return_counts=True)
    return u[c == DAY // H4]


def daily(p, m, days):
    A = p["A"]; r = p["r"]
    out = np.zeros(len(days))
    for i, d in enumerate(days):
        sel = m & (A // DAY == d)
        out[i] = np.prod(1.0 + r[sel]) - 1.0
    return out


def pins_of(d, tag):
    J = json.load(open(os.path.join(d, f"PATH_{tag}_seed_00.json")))
    return {k: J.get(k) for k in ("device_sha256", "calibration_sha256", "price_pin")}


def main():
    sys.path.insert(0, ENG)
    rec = {"device": "tf_gates.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "prereg": {"path": "docs/PREREG_tradfi_universe_gap_2026-09-24.md", "commit": "58a29c04a"},
           "amendment_1": {"path": "docs/AMENDMENT_1_tradfi_universe_gap_2026-09-24.md", "commit": "3b20d1c41"},
           "gates": {}, "T0": {}}

    # ---- P0: reproduce the six quoted Sharpes from the receipts ----
    p0 = {"quoted": QUOTED_SHARPE, "measured": {}, "max_abs_dev": 0.0, "tol": 0.005,
          "readout": "tables[arm][base][pre2026].paths.sharpe.path_mean, explicit path, raises on missing key"}
    for arm, path in STATS.items():
        p0["measured"][arm] = {"receipt": path, "receipt_sha256": sha(path), "seeds": {}}
        for seed in ("s42", "s2027"):
            v = sharpe_pre2026(path, ARMKEY[arm][seed])
            p0["measured"][arm]["seeds"][seed] = v
            p0["max_abs_dev"] = max(p0["max_abs_dev"], abs(v - QUOTED_SHARPE[arm][seed]))
    p0["missing"] = []
    p0["PASS"] = bool(p0["max_abs_dev"] <= p0["tol"])
    rec["gates"]["P0_reproduce_quoted_sharpe"] = p0

    # ---- P0b / P2: engine pins ----
    pv = {}
    for arm in ("NEW", "NC"):
        for seed in ("s42", "s2027"):
            d = CELLS[arm][seed]; tag = os.path.basename(d)
            pv[f"{arm}_{seed}"] = pins_of(d, tag)
    agree = {k: len({json.dumps(v[k], sort_keys=True) for v in pv.values()}) == 1 for k in ("device_sha256", "calibration_sha256", "price_pin")}
    rec["gates"]["P0b_denominator_same_engine"] = {"pins": pv, "identical": agree, "PASS": bool(all(agree.values()))}

    # ---- P0c: NEW - NC paired daily difference, bps/day, pre-2026 (COMPARE, not assert) ----
    p0c = {"quoted_about": QUOTED_BPS_GAP, "measured_bps_per_day": {}, "note": "computed here because no receipt holds a NEW-vs-NC paired difference"}
    dailies = {}
    for arm in ("NEW", "NC"):
        for seed in ("s42", "s2027"):
            d = CELLS[arm][seed]; tag = os.path.basename(d)
            ps = load_paths(d, tag)
            A = ps[0]["A"]
            for p in ps: assert np.array_equal(p["A"], A), f"{tag}: axis differs across paths"
            m = seg_mask(A, *PRE2026); days = full_days(A, m)
            dailies[(arm, seed)] = (np.array([daily(p, m, days) for p in ps]), days, A)
    for seed in ("s42", "s2027"):
        Dn, days_n, An = dailies[("NEW", seed)]
        Dc, days_c, Ac = dailies[("NC", seed)]
        assert np.array_equal(days_n, days_c), f"{seed}: day axes differ between NEW and NC"
        d = (Dn - Dc).mean(axis=0)          # per-day mean over the 32 paired paths
        p0c["measured_bps_per_day"][seed] = {"estimate": float(1e4 * d.mean()), "n_days": int(len(d)), "n_paths": int(Dn.shape[0])}
    for seed, v in p0c["measured_bps_per_day"].items():
        q = QUOTED_BPS_GAP[seed]
        v["vs_quoted_rel_dev"] = float(abs(v["estimate"] - q) / abs(q)) if q else None
        v["flag_over_20pct"] = bool(v["vs_quoted_rel_dev"] is not None and v["vs_quoted_rel_dev"] > 0.20)
    p0c["ASSERTED"] = False
    rec["gates"]["P0c_denominator_vs_quoted"] = p0c

    # ---- T0: TradFi gross share of NEW's book ----
    M = np.load(CRYPTO_NPZ, allow_pickle=True)
    t0 = {"crypto_npz": {"path": CRYPTO_NPZ, "sha256": sha(CRYPTO_NPZ)}, "n_crypto": int(M["crypto"].sum()),
          "n_tradfi": int((~M["crypto"]).sum()), "seeds": {}}
    for seed in ("s42", "s2027"):
        cpath = f"{NEW_COMBO}/combo_{seed[1:] if seed.startswith('s') else seed}/scaled_diagnostic.npz"
        cpath = f"{NEW_COMBO}/combo_s{seed[1:]}/scaled_diagnostic.npz"
        C = np.load(cpath, allow_pickle=True)
        assert np.array_equal(C["symbols"], M["symbols"]), "symbol axis differs between combo and crypto flag"
        W = C["weights"]; E = C["E_ts"].astype(np.int64); tf = ~M["crypto"]
        absW = np.abs(W); gross = absW.sum(axis=1); gtf = absW[:, tf].sum(axis=1)
        pub = np.asarray(C["trade_mask"]).astype(bool)
        yr = np.array([time.gmtime(int(e)).tm_year for e in E])
        prem = (E >= ts(PRE2026[0])) & (E <= ts(PRE2026[1]))
        def blk(sel):
            s = sel & pub
            if not s.any(): return {"n_published_anchors": 0, "share": None, "why": "no published anchor in this block"}
            return {"n_published_anchors": int(s.sum()), "gross_sum": float(gross[s].sum()), "tradfi_gross_sum": float(gtf[s].sum()),
                    "share": float(gtf[s].sum() / gross[s].sum()) if gross[s].sum() else None,
                    "share_per_anchor_mean": float(np.nanmean(np.where(gross[s] > 0, gtf[s] / np.maximum(gross[s], 1e-300), np.nan))),
                    "anchors_with_any_tradfi": int((gtf[s] > 0).sum())}
        t0["seeds"][seed] = {"combo": {"path": cpath, "sha256": sha(cpath)},
                             "pre2026": blk(prem), "by_year": {str(y): blk(yr == y) for y in sorted(set(yr.tolist()))},
                             "all_anchors": {"n": int(len(E)), "n_published": int(pub.sum()),
                                             "anchors_with_any_tradfi_weight": int((gtf > 0).sum()),
                                             "max_tradfi_share": float(np.nanmax(np.where(gross > 0, gtf / np.maximum(gross, 1e-300), np.nan)))}}
    # P4': the exposure channel is EMPTY. Verified on the object the engine actually reads (TARGETS csr),
    # not only on the combo's dense weights, with counts balanced so "saw no TradFi entries" cannot stand alone.
    tf_cols = np.flatnonzero(~M["crypto"]).astype(np.int64)
    eng = {}
    for seed in ("s42", "s2027"):
        T = np.load(f"{OVN}/targets/TARGETS_NEW_{seed}.npz", allow_pickle=True)
        per = {}
        for pref in ("scaled", "lit"):
            idx = T[f"{pref}_idx"].astype(np.int64); val = T[f"{pref}_val"]
            in_tf = np.isin(idx, tf_cols)
            n_tf = int(in_tf.sum()); n_tot = int(len(idx))
            per[pref] = {"nnz_total": n_tot, "nnz_on_tradfi": n_tf, "nnz_on_crypto": n_tot - n_tf,
                         "counts_balance": bool(n_tf + (n_tot - n_tf) == n_tot),
                         "abs_mass_total": float(np.abs(val).sum()),
                         "abs_mass_on_tradfi": float(np.abs(val[in_tf]).sum()) if n_tf else 0.0,
                         "distinct_columns_used": int(len(np.unique(idx))),
                         "max_column_index": int(idx.max()), "axis_width": int(len(M["symbols"]))}
        eng[seed] = {"targets_npz": f"{OVN}/targets/TARGETS_NEW_{seed}.npz",
                     "targets_sha256": sha(f"{OVN}/targets/TARGETS_NEW_{seed}.npz"), "readings": per}
    t0["engine_input_check"] = eng
    t0["exposure_channel_empty_on_engine_input"] = bool(
        all(eng[s]["readings"][p]["nnz_on_tradfi"] == 0 for s in ("s42", "s2027") for p in ("scaled", "lit")))
    t0["all_counts_balance"] = bool(all(eng[s]["readings"][p]["counts_balance"] for s in ("s42", "s2027") for p in ("scaled", "lit")))

    # frozen rule: T1a is a bitwise no-op iff the TradFi share is exactly 0 at EVERY anchor, both seeds
    zero_w = all(t0["seeds"][s]["all_anchors"]["anchors_with_any_tradfi_weight"] == 0 for s in ("s42", "s2027"))
    zero_e = t0["exposure_channel_empty_on_engine_input"]
    t0["two_instruments_agree"] = bool(zero_w == zero_e)
    t0["T1a_is_bitwise_noop"] = bool(zero_w and zero_e)
    assert t0["two_instruments_agree"], f"combo weights say {zero_w} but the engine input says {zero_e}"
    t0["decision_rule_verbatim"] = ("prereg §1 arm 0: if the TradFi gross share is exactly 0 at every anchor then T1a is a bitwise "
                                    "no-op, assert it and stop; otherwise T1a runs regardless of how small the share is")
    rec["T0"] = t0

    if t0["T1a_is_bitwise_noop"]:
        rec["gap_share"] = {"unit_primary": "bps/day", "numerator_definition": "NEW - T1a, pre-2026 paired daily difference",
                            "seeds": {s: {"numerator_bps_per_day": 0.0,
                                          "denominator_bps_per_day": p0c["measured_bps_per_day"][s]["estimate"],
                                          "share": 0.0,
                                          "why_numerator_is_exactly_zero": "T1a is a bitwise no-op: NEW's book holds no TradFi weight at any anchor, "
                                                                           "so removing those columns changes nothing the engine reads"}
                                      for s in ("s42", "s2027")},
                            "sharpe_side_report": {s: {"numerator_sharpe_points": 0.0,
                                                       "denominator_sharpe_points": p0["measured"]["NEW"]["seeds"][s] - p0["measured"]["NC"]["seeds"][s],
                                                       "share": 0.0} for s in ("s42", "s2027")}}
    gates_pass = {k: v.get("PASS") for k, v in rec["gates"].items() if "PASS" in v}
    rec["GATES_PASS"] = bool(all(v for v in gates_pass.values()))
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
    print(f"TF_GATES P0={'PASS' if p0['PASS'] else 'FAIL'}(max_abs_dev={p0['max_abs_dev']:.4f}, missing={p0['missing']}) "
          f"P0b={'PASS' if rec['gates']['P0b_denominator_same_engine']['PASS'] else 'FAIL'} "
          f"P0c_measured={{s42:{p0c['measured_bps_per_day']['s42']['estimate']:+.3f}, s2027:{p0c['measured_bps_per_day']['s2027']['estimate']:+.3f}}}bps/d "
          f"quoted={{s42:{QUOTED_BPS_GAP['s42']}, s2027:{QUOTED_BPS_GAP['s2027']}}} "
          f"flag20={{s42:{p0c['measured_bps_per_day']['s42']['flag_over_20pct']}, s2027:{p0c['measured_bps_per_day']['s2027']['flag_over_20pct']}}} "
          f"T0_tradfi_share_pre2026={{s42:{t0['seeds']['s42']['pre2026']['share']}, s2027:{t0['seeds']['s2027']['pre2026']['share']}}} "
          f"T1a_noop={t0['T1a_is_bitwise_noop']} receipt={sha(OUT)}", flush=True)
    sys.exit(0 if rec["GATES_PASS"] else 3)


if __name__ == "__main__":
    main()
