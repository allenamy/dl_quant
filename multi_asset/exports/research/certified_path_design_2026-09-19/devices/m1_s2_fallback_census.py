#!/usr/bin/env python3
"""M1 — COMBO_LIVE fallback census over the S2 run records (READ-ONLY; design doc DESIGN_certified_production_path_2026-09-19 §3).

Reads (never writes) the S2 per-arm run records and their sparse state vectors:
    /workspace/uplift_r2_2026-09-13/P2/receipts/RUN_S2_<arm>.json      (driver p2_driver.py dc4e6c85, one record per anchor)
    /workspace/uplift_r2_2026-09-13/P2/receipts/RUN_S2_<arm>.vec.npz   (kc / fc float64 state vectors, |v| > 1e-9 truncated)
Writes only:  /workspace/certified_path_design_2026-09-19/receipts/M1_S2_FALLBACK_CENSUS.json

What it measures, per arm x UTC year (and W_ALPHA = anchors >= 2022-06-30 00Z, <= 2026-08-30 20Z):
  outcome   COMBO_OK (traded_file == combo) / KNOWN_CRASH (combo chain() returned None -> no kc/fc state, p2_driver L338-346)
            / PREFLIGHT_OR_VALIDATION (combo_stage rc 3 with combo_live_status.why) / PRODUCER_SKIP / OTHER
  why class for rc-3 anchors, keyed to the production combo_stage assertion that fired
            (combo_stage_2026-09-17_fp2-6b_f10sha.py: L333 F10 floor, L334 gross, L335 names, L336 king doc, L374 verify_file,
             L379 parse_target, L380 outside-universe, L381 reader n/gross, L324 deadline, L327 king file missing)
  F10-floor split  STRUCT  members < 380 (L333 unreachable even with complete OOF coverage)
                   NOSERVE members >= 380 and n_scored == 0
                   GAP     members >= 380 and 0 < n_scored < 380 (OOF coverage gap, PREREG D10)
  counterfactual reads (measurement only, nothing is re-run): of the F10-floor failures, how many have
            n_scored >= ceil(0.95 * members) (a ratio floor), and whether the later numeric preflight checks
            (gross of 0.55*kc + 0.45*fc in [0.4, 1.2], names >= 150) hold on the recorded states.
  preflight predicate reads on every anchor with recorded states (pf:*): gross side (<0.4 / >1.2) and pass counts under
            LIT floors (production constants 380 / 150) and SCALED floors (0.95*|pm| / 0.375*|pm|; 150/400 = 0.375), with the
            current OOF coverage and with coverage set to complete (n_scored := |pm|, only where F10 is served). Recorded states
            are used as-is, so these are predicate counts, not book results.
  January withhold windows (Y-01-01 00Z .. Y-01-31 00Z, Y = 2024/2025/2026): king served / seats w3 / crash / traded file,
            and whether the previous yearly fold would be admissible under the same 30-day rule (label_end(Y-1) < E - 30 d).
  fund-seat-zero runs: contiguous anchor runs where the recorded seat w3[2] (fund) == 0.
"""
import os, sys, json, time, math, hashlib, collections, calendar
import numpy as np

P2R = "/workspace/uplift_r2_2026-09-13/P2/receipts"
OUT = "/workspace/certified_path_design_2026-09-19/receipts/M1_S2_FALLBACK_CENSUS.json"
ARMS = ["S2_v4_s42", "S2_v4_s2027", "S2_A0pred_s42", "S2_A0pred_s2027", "S2_v4_s42_serveall", "S2_v4_s42_pins"]
PIN = {  # record sha pins as used by stream R RUN_CONFIG d6ad8d2e (json) and the S2 SHA256SUMS (vec)
    "S2_A0pred_s42": "d01063c0ee68a48799229aef60736e7a1a8e46dbbdc9d5d72f3f227f95affbbe",
    "S2_v4_s42": "4c5612f613ddad105d7c8997dcdc5a37bda8ccb8892b80cf18b370d325232bc6",
    "S2_A0pred_s2027": "c63b59a72438a1a0f789e548ac10e5ed48e54a9e23bcfbdcd532c497b3850133",
    "S2_v4_s2027": "5aba956d75faec46e63147baf84f37b5ed2af58a91061438ce94329aa3a71741",
}
FLOOR = 380; DAY = 86400; H4 = 14400
W_ALPHA_LO = calendar.timegm((2022, 6, 30, 0, 0, 0)); W_ALPHA_HI = calendar.timegm((2026, 8, 30, 20, 0, 0))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def year(t): return time.gmtime(int(t)).tm_year


def why_class(why):
    if not why: return "NO_WHY"
    if "F10 打分覆盖" in why: return "L333_F10_FLOOR"
    if "combo gross" in why: return "L334_GROSS"
    if "combo 名数" in why: return "L335_NAMES"
    if "king 文件锚/schema" in why: return "L336_KINGDOC"
    if "verify_file" in why: return "L374_VERIFY_FILE"
    if "parse_target" in why: return "L379_PARSE_TARGET"
    if "宇宙外权重" in why: return "L380_OUTSIDE_UNIVERSE"
    if "过硬截止" in why: return "L324_DEADLINE"
    if "生产者 king 文件" in why: return "L327_KINGFILE_MISSING"
    if why.strip() == "AssertionError:": return "L381_READER_N_OR_GROSS"
    return "OTHER:" + why[:80]


def combo_numeric(V, k):
    """0.55*kc + 0.45*fc from the recorded state vectors at vec row k -> (gross, n_names). States are |v|>1e-9 truncated (A6.2)."""
    w = np.zeros(829)
    a, b = V["kc_off"][k], V["kc_off"][k + 1]; w[V["kc_idx"][a:b]] += 0.55 * V["kc_val"][a:b]
    a, b = V["fc_off"][k], V["fc_off"][k + 1]; w[V["fc_idx"][a:b]] += 0.45 * V["fc_val"][a:b]
    nz = np.abs(w) > 1e-9
    return float(np.abs(w[nz]).sum()), int(nz.sum()), None


def census(arm):
    jp = f"{P2R}/RUN_{arm}.json"; vp = f"{P2R}/RUN_{arm}.vec.npz"
    js = sha(jp); vs = sha(vp)
    if arm in PIN: assert js == PIN[arm], (arm, js)
    D = json.load(open(jp)); R = D["records"]
    _Z = np.load(vp); V = {k_: np.array(_Z[k_]) for k_ in _Z.files}   # materialise once: NpzFile re-decompresses on every index (first run killed for this)
    assert len(R) == D["n_records"] == len(V["anchor"]), arm
    assert all(int(r["anchor"]) == int(a) for r, a in zip(R, V["anchor"])), "record/vec anchor axis differ"
    kt = {int(k): int(v) for k, v in D["king_fold_table"]["label_end"].items()}
    per = collections.defaultdict(lambda: collections.Counter()); mem = collections.defaultdict(list)
    f10cf = collections.defaultdict(lambda: collections.Counter())
    other_why = collections.Counter(); jan = {}; fund0 = []
    for k, r in enumerate(R):
        A = int(r["anchor"]); Y = year(A); keys = [str(Y)] + (["W_ALPHA"] if W_ALPHA_LO <= A <= W_ALPHA_HI else []) + ["ALL"]
        ko = r.get("king_oof") or {}; fo = r.get("f10_oof") or {}; sg = r.get("signal") or {}
        m = int(ko.get("n_members") or sg.get("members") or 0); ns = int(fo.get("n_scored") or 0)
        tf = r.get("traded_file"); st = r.get("combo_live_status") or {}
        if tf == "combo": oc = "COMBO_OK"
        elif tf == "none(producer_skip)": oc = "PRODUCER_SKIP"
        elif r.get("combo_known_crash"): oc = "KNOWN_CRASH"
        elif r.get("combo_rc") == 3: oc = "PREFLIGHT_OR_VALIDATION"
        else: oc = "OTHER"
        wc = why_class(st.get("why")) if oc == "PREFLIGHT_OR_VALIDATION" else None
        if wc and wc.startswith("OTHER"): other_why[wc] += 1
        sub = None; cf = {}
        if wc == "L333_F10_FLOOR":
            sub = "STRUCT_members_lt_380" if m < FLOOR else ("NOSERVE_n_scored_0" if ns == 0 else "GAP_0_lt_scored_lt_380")
            g, n, _ = combo_numeric(V, k)
            cf = {"ratio_floor_095_pass": ns >= math.ceil(0.95 * m) if m else False,
                  "later_gross_ok": 0.4 <= g <= 1.2, "later_names_ok": n >= 150}
        # preflight predicate on the RECORDED states (approximate: states would change if coverage changed); every anchor with kc/fc states
        pf = {}
        if r.get("combo_meta") is not None:
            g_, n_, _ = combo_numeric(V, k)
            gross_ok = 0.4 <= g_ <= 1.2
            pf["states"] = True; pf["gross_lt_0.4"] = g_ < 0.4; pf["gross_gt_1.2"] = g_ > 1.2
            pf["LIT_floors_current_oof"] = (ns >= FLOOR) and gross_ok and n_ >= 150
            pf["LIT_floors_full_coverage"] = (m >= FLOOR) and gross_ok and n_ >= 150
            pf["SCALED_floors_current_oof"] = (ns >= math.ceil(0.95 * m)) and gross_ok and n_ >= math.ceil(0.375 * m) and ns > 0
            pf["SCALED_floors_full_coverage_if_f10_served"] = bool(fo.get("served")) and gross_ok and n_ >= math.ceil(0.375 * m)
        for key in keys:
            c = per[key]; c["n"] += 1; c["oc:" + oc] += 1
            for pk, pv in pf.items():
                if pv: c["pf:" + pk] += 1
            if wc: c["why:" + wc] += 1
            if sub: c["f10:" + sub] += 1
            if m >= FLOOR: c["members_ge_380"] += 1
            for cfk, cfv in cf.items():
                if cfv: f10cf[key][cfk] += 1
            if sub == "GAP_0_lt_scored_lt_380": f10cf[key]["gap_members_minus_scored_sum"] += (m - ns)
            mem[key].append(m)
        w3 = sg.get("w3")
        if w3 is not None and float(w3[2]) == 0.0: fund0.append(A)
        # January withhold windows
        g = time.gmtime(A)
        if g.tm_mon == 1 and (g.tm_mday < 31 or (g.tm_mday == 31 and g.tm_hour == 0)) and Y in (2024, 2025, 2026):
            J = jan.setdefault(str(Y), collections.Counter()); J["n"] += 1
            J["king_served"] += int(bool(ko.get("served"))); J["king_admissible"] += int(bool(ko.get("admissible")))
            J["oc:" + oc] += 1; J["traded:" + str(tf)] += 1
            if w3 is not None:
                J["fund_seat_eq_0"] += int(float(w3[2]) == 0.0); J["king_seat_gt_0"] += int(float(w3[0]) > 0.0)
                J.setdefault("w3_min", [9, 9, 9]); J.setdefault("w3_max", [-9, -9, -9])
                J["w3_min"] = [min(a_, float(b_)) for a_, b_ in zip(J["w3_min"], w3)]; J["w3_max"] = [max(a_, float(b_)) for a_, b_ in zip(J["w3_max"], w3)]
            prevY = Y - 1
            if prevY in kt:
                J["prev_fold_%d_exists_and_admissible" % prevY] += int(kt[prevY] < A - 30 * DAY)
            else:
                J["prev_fold_%d_absent_in_oof" % prevY] += 1
            J["this_fold_label_end"] = iso(kt[Y]) if Y in kt else None
    # fund-seat-zero contiguous runs
    runs = []
    if fund0:
        s = p = fund0[0]
        for a in fund0[1:]:
            if a - p != H4: runs.append((s, p)); s = a
            p = a
        runs.append((s, p))
    runs_out = [{"first": iso(a), "last": iso(b), "n_anchors": (b - a) // H4 + 1} for a, b in runs if (b - a) // H4 + 1 >= 6]
    out = {}
    for key, c in per.items():
        ms = np.array(mem[key]); d = dict(c)
        d["members_min_median_max"] = [int(ms.min()), float(np.median(ms)), int(ms.max())]
        d["share_combo_ok"] = round(c["oc:COMBO_OK"] / c["n"], 4)
        d["share_fallback_to_king"] = round(c["oc:PREFLIGHT_OR_VALIDATION"] / c["n"], 4)
        d["share_known_crash_hold"] = round(c["oc:KNOWN_CRASH"] / c["n"], 4)
        d["f10_floor_counterfactual_reads"] = dict(f10cf[key])
        out[key] = d
    return {"arm": arm, "record_sha256": js, "vec_sha256": vs, "n_records": len(R), "driver_sha256": D.get("driver_sha256"),
            "king_fold_label_end": {k: iso(v) for k, v in kt.items()}, "by_period": out, "january_withhold_windows": {k: dict(v) for k, v in jan.items()},
            "fund_seat_zero_runs_ge6": runs_out, "fund_seat_zero_anchor_count": len(fund0), "other_why_strings": dict(other_why)}


def main():
    assert set(os.environ) <= {"PATH", "HOME", "LC_CTYPE", "PWD", "SHLVL", "_", "OLDPWD"}, sorted(os.environ)
    t0 = time.time(); res = {}
    for arm in ARMS:
        res[arm] = census(arm); print(arm, "done", round(time.time() - t0, 1), "s", flush=True)
    doc = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "python": sys.version.split()[0], "numpy": np.__version__,
           "env": dict(os.environ), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "floor": FLOOR, "results": res, "runtime_s": round(time.time() - t0, 1)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"; json.dump(doc, open(tmp, "w"), indent=1, ensure_ascii=False); os.replace(tmp, OUT)
    print("WROTE", OUT, sha(OUT))


if __name__ == "__main__":
    main()
