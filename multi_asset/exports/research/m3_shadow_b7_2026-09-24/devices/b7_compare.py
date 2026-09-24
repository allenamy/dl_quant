#!/usr/bin/env python3
"""b7_compare.py — M3 shadow acceptance B7 (AMENDMENT_2 §3 step 4, item 2: "β_exec 与研究侧同锚重算的差在 1% 内"), research side.
Mac, /usr/bin/python3 + numpy. Everything below was fixed and committed BEFORE any B7 number was read.

Anchors: A08 = 2026-09-24T08:00Z (1790236800), A12 = 2026-09-24T12:00Z (1790251200) — the first two NC anchors (NC s42 deployed 05:26Z,
executor tree 5d3029c, beta_overlay shadow, budget 2.5). Positive control: ACTRL = 2026-09-18T20:00Z (1789761600).

RESEARCH β (the prereg formula, m2_lib.py sha 93f8e760, UNCHANGED): the venue's 4h klines (b7_fetch_klines.py) → a 5-minute log-price grid
whose 4h-boundary rows hold log(close of the kline that closes at that boundary) (the other rows repeat the last boundary value; bars_4h
reads only boundary rows) → m2_lib.bars_4h → m2_lib.betas_at at [ACTRL, A08, A12] (180 completed 4h bars ending at A, OLS with intercept
on BTCUSDT, ≥ 120 valid pairs else 1.0, clip [−1, 4], BTC = 1). first_fin / last_fin = the first / last boundary with a kline; a missing
kline in between marks that boundary row as UNAVAILABLE (m2_lib excludes both adjacent bars); a symbol with no kline at all (fetch FAILED
or empty) is MISSING — never given the formula's 1.0.

POSITIVE CONTROL (instrument): research β at ACTRL vs the certified β (M3's matrix 6dcf9782, row ACTRL, from the certified raw table) on
names estimated on both sides and with no UNAVAILABLE bar in the certified window (b7_ctrl_extract.py). PASS iff max |Δβ| ≤ 1e-6 on at
least 100 such names. A FAILED control makes the B7 verdict UNDECIDED (the instrument is not validated), numbers still reported.

LAYER (i) — per name (REPORT; the lead's request), for each anchor, population = the names of the PRODUCTION field
target_live/<A>.json `beta_overlay.betas` (a copy, sha recorded; the executor ties to it through `betas_sha256`, checked in layer ii):
  classes: BTC (1 on both sides, excluded) · MISSING (no research data) · both_fallback · prod_fallback_only (n_obs_prod < 120, research
  estimated) · res_fallback_only · both_estimated. On both_estimated: abs = |β_prod − β_res|, rel = abs / |β_res| (β_res == 0 ⇒ rel = inf,
  named). Reported: class counts, quantiles p50 / p90 / p99 / max of rel and abs, the number of names with rel > 1 % and their list with
  β_prod, β_res, n_obs_prod, n_obs_res.

LAYER (ii) — book β_exec (the ACCEPTANCE quantity):
  * the executor's record = the anchors row (pilot_log/20260924/anchors.jsonl, a copy) whose floor(anchor_ts / 4h) · 4h == A, key
    `m3_beta_overlay`; required: exactly one such row, mode "shadow", field_ok true, beta_exec_usdt / book_gross_usdt / n_targeted_names
    present; betas_sha256 == sha of the production field's betas (canonical JSON, beta_overlay.betas_sha256's rule) — else UNDECIDED.
  * the executed per-name targets: the anchors row carries none (the integration agent's reading, confirmed here: `weights` is the
    mixture). The plan rows in orders.jsonl (a copy) carry target_w = target_notional / Σ|target_notional| for EVERY plan row, skipped ones
    included (binance_executor.py plan(): "set on EVERY row, including the skipped ones"). Reconstruction:
      target_i = target_w_i × book_gross_usdt over the distinct symbols of the orders rows with anchor_ts == the anchors row's anchor_ts
      (every row of a symbol must carry the same target_w, else refused).
    CLOSURE (all three must hold, else "不可由记录重算" and UNDECIDED): (c1) |Σ|target_w| − 1| ≤ 1e-9; (c2) the number of non-zero
    target_w == n_targeted_names; (c3) Σ target_i · β_prod_i (sorted symbols, production betas) reproduces the record's beta_exec_usdt
    within 1e-9 relative. Files checked are listed in the receipt either way.
  * research β_exec = Σ target_i · β_res_i over the same non-zero targets; a targeted name without research data ⇒ UNDECIDED (named).
  * rel_exec = |β_exec_res − β_exec_record| / |β_exec_record|; the anchor PASSES iff rel_exec ≤ 0.01.
VERDICT: PASS iff the control PASSES and both anchors PASS; FAIL iff the control PASSES, both anchors are computable and at least one has
rel_exec > 0.01; UNDECIDED otherwise (named reason). Layer (i) never changes the verdict.
Blind state (live execution data ⇒ pooled quantities only): from orders.jsonl only (anchor_ts, symbol, target_w) are read; nothing about
fills, arms or order outcomes is read or written; the receipt holds sums and counts, never per-name targets.
usage: /usr/bin/python3 -B b7_compare.py <inputs_dir> <fetch_dir> <ctrl_npz> <out_dir>
"""
import csv, gzip, hashlib, json, math, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m2_lib as M

A08, A12, ACTRL = 1790236800, 1790251200, 1789761600
H4, ROW, BTC = 14400, 300, "BTCUSDT"
M2_SHA = "93f8e76088ca523158df4d3ddb12f4f3239d0b75e3e0f7362ecc9ced914c8c9d"


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def betas_sha256(betas):                                    # live/beta_overlay.py betas_sha256, verbatim rule
    return hashlib.sha256(json.dumps({k: float(v) for k, v in sorted(betas.items())}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def utc(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def q(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) == 0: return {"n": 0}
    return {"n": int(len(x)), "p50": float(np.percentile(x, 50)), "p90": float(np.percentile(x, 90)), "p99": float(np.percentile(x, 99)), "max": float(x.max())}


def main():
    inp, fdir, ctrl_p, out = [os.path.abspath(a) for a in sys.argv[1:5]]; os.makedirs(out, exist_ok=True)
    rec = {"device": "b7_compare.py", "self_sha256": sha_file(os.path.abspath(__file__)), "m2_lib_sha256": sha_file(os.path.join(HERE, "m2_lib.py")),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "anchors": {"A08": utc(A08), "A12": utc(A12), "ACTRL": utc(ACTRL)}, "inputs": {}}
    if rec["m2_lib_sha256"] != M2_SHA: raise SystemExit("m2_lib is not 93f8e760 — refused")
    und = []
    # ---- fetched klines → grid ----
    man = json.load(open(os.path.join(fdir, "FETCH_MANIFEST.json"))); rec["inputs"]["fetch_manifest"] = {"sha256": sha_file(os.path.join(fdir, "FETCH_MANIFEST.json")), "verdict": man["verdict"]}
    if sha_file(os.path.join(fdir, "KLINES_RAW.jsonl.gz")) != man["outputs"]["KLINES_RAW.jsonl.gz"]: raise SystemExit("klines file sha != manifest")
    if not man["verdict"].startswith(("COMPLETE", "PARTIAL_FAILED_SYMBOLS")): und.append(f"fetch verdict {man['verdict']}")
    kl = {}
    with gzip.open(os.path.join(fdir, "KLINES_RAW.jsonl.gz"), "rt") as f:
        for ln in f:
            d = json.loads(ln); kl[d["symbol"]] = json.loads(d["body"])
    syms = sorted(kl); bj = syms.index(BTC) if BTC in syms else None
    if bj is None: raise SystemExit("no BTCUSDT klines — refused")
    G0 = ACTRL - 180 * H4; GEND = A12
    grid = np.arange(G0, GEND + 1, ROW, dtype=np.int64); nS = len(syms)
    LP = np.full((len(grid), nS), np.nan); ff = np.full(nS, -1, np.int64); lf = np.full(nS, -1, np.int64)
    bnd = np.arange(G0, GEND + 1, H4, dtype=np.int64); brow = ((bnd - G0) // ROW).astype(np.int64)
    ua_r, ua_c = [], []; bad_kline = {}
    for j, s in enumerate(syms):
        px = {}
        for k in kl[s]:
            ot, ct, c = int(k[0]) // 1000, int(k[6]), float(k[4])
            if ct != (ot + H4) * 1000 - 1 or not (c > 0): bad_kline.setdefault(s, []).append(ot); continue
            px[ot + H4] = c                                            # the close at the boundary the kline ends on
        have = [t for t in bnd.tolist() if t in px]
        if not have: continue
        ff[j], lf[j] = min(have), max(have)
        last = np.nan
        for t, r0 in zip(bnd.tolist(), brow.tolist()):
            if t in px: last = math.log(px[t]); LP[r0, j] = last
            elif ff[j] <= t <= lf[j]: ua_r.append(r0); ua_c.append(j)       # a missing kline inside the life: UNAVAILABLE boundary
            nxt = r0 + H4 // ROW
            if nxt <= len(grid) - 1 and np.isfinite(last): LP[r0 + 1:nxt, j] = last
    rec["grid"] = {"G0": utc(G0), "GEND": utc(GEND), "n_rows": int(len(grid)), "n_symbols": nS, "n_ua_boundaries": len(ua_r),
                   "symbols_with_bad_klines": {k: len(v) for k, v in bad_kline.items()}}
    T, R, V = M.bars_4h(LP, grid, ff, lf, np.array(ua_r, np.int64), np.array(ua_c, np.int64))
    B, NOBS, EST, RAW = M.betas_at(T, R, V, np.array([ACTRL, A08, A12], np.int64), bj)
    res = {a: {s: (float(B[i, j]), int(NOBS[i, j]), bool(EST[i, j]), bool(ff[j] >= 0)) for j, s in enumerate(syms)} for i, a in enumerate((ACTRL, A08, A12))}
    # ---- positive control ----
    C = np.load(ctrl_p); rec["inputs"]["ctrl_npz"] = sha_file(ctrl_p)
    csy = [str(s) for s in C["symbols"]]; cmap = {s: i for i, s in enumerate(csy)}
    dif = []; rows_c = []
    for s in syms:
        if s == BTC or s not in cmap: continue
        i = cmap[s]; br, nr, er, have = res[ACTRL][s]
        if not have or not bool(C["est"][i]) or not er: continue
        d = abs(br - float(C["beta"][i])); rows_c.append([s, float(C["beta"][i]), br, d, bool(C["ua_in_window"][i])])
        if not bool(C["ua_in_window"][i]): dif.append(d)
    ctrl = {"n_compared_clean": len(dif), "max_abs_dbeta_clean": float(max(dif)) if dif else None,
            "n_ua_names_reported_not_gated": int(sum(1 for r in rows_c if r[4])), "max_abs_dbeta_ua_names": float(max([r[3] for r in rows_c if r[4]], default=0.0)),
            "gate": "max |Δβ| ≤ 1e-6 on ≥ 100 clean names"}
    ctrl["pass"] = bool(len(dif) >= 100 and max(dif) <= 1e-6)
    rec["positive_control"] = ctrl
    if not ctrl["pass"]: und.append("positive control failed")
    with open(os.path.join(out, "B7_CONTROL_per_name.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["symbol", "beta_certified", "beta_klines", "abs_diff", "ua_in_certified_window"]); w.writerows(rows_c)
    # ---- production copies ----
    A_rows = [json.loads(l) for l in open(os.path.join(inp, "anchors_20260924.jsonl"))]
    O_min = []
    for l in open(os.path.join(inp, "orders_20260924.jsonl")):
        o = json.loads(l); O_min.append((o.get("anchor_ts"), o.get("symbol"), o.get("target_w")))      # only these three keys are read
    rec["inputs"]["anchors_copy"] = sha_file(os.path.join(inp, "anchors_20260924.jsonl")); rec["inputs"]["orders_copy"] = sha_file(os.path.join(inp, "orders_20260924.jsonl"))
    rec["files_checked_for_executed_targets"] = ["pilot_log/20260924/anchors.jsonl (keys: m3_beta_overlay record, weights = mixture, reshape report; no per-name target)",
                                                 "pilot_log/20260924/orders.jsonl (target_w per plan row, skipped rows included)"]
    per_anchor = {}; name_rows = []
    for A, lab in ((A08, "A08"), (A12, "A12")):
        pa = {"anchor": utc(A)}; per_anchor[lab] = pa
        tp = os.path.join(inp, "target_live", f"{A}.json"); d = json.load(open(tp)); fld = d.get("beta_overlay") or {}
        pa["target_live_copy_sha256"] = sha_file(tp)
        bp, nop = fld.get("betas") or {}, fld.get("n_obs") or {}
        # layer (i)
        cls = {}; rel, ab, over = [], [], []
        for s in sorted(bp):
            p_b, p_n = float(bp[s]), int(nop[s]); p_est = (p_n >= 120 and s != BTC)
            if s == BTC: c = "BTC"; rb = rn = re_ = None
            elif s not in res[A] or not res[A][s][3]: c = "MISSING"; rb = rn = re_ = None
            else:
                rb, rn, re_, _ = res[A][s]
                c = ("both_estimated" if (p_est and re_) else "both_fallback" if (not p_est and not re_) else "prod_fallback_only" if not p_est else "res_fallback_only")
            cls[c] = cls.get(c, 0) + 1
            a_ = r_ = None
            if c == "both_estimated":
                a_ = abs(p_b - rb); r_ = (a_ / abs(rb)) if rb != 0 else float("inf"); rel.append(r_); ab.append(a_)
                if r_ > 0.01: over.append({"symbol": s, "beta_prod": p_b, "beta_res": rb, "n_obs_prod": p_n, "n_obs_res": rn, "rel": r_})
            name_rows.append([lab, s, c, p_b, p_n, rb, rn, re_, a_, r_])
        pa["layer_i"] = {"n_names": len(bp), "classes": cls, "rel": q(rel), "abs": q(ab), "n_rel_over_1pct": len(over),
                         "rel_over_1pct": sorted(over, key=lambda x: -x["rel"])}
        # layer (ii)
        rows = [r for r in A_rows if int(float(r["anchor_ts"]) // H4 * H4) == A]
        li = {"anchors_rows_found": len(rows)}; pa["layer_ii"] = li
        if len(rows) != 1: li["undecided"] = f"{len(rows)} anchors rows for {utc(A)}"; und.append(f"{lab}: {li['undecided']}"); continue
        m3 = rows[0].get("m3_beta_overlay"); ats = rows[0]["anchor_ts"]
        if not isinstance(m3, dict): li["undecided"] = "no m3_beta_overlay record"; und.append(f"{lab}: no m3 record"); continue
        li["record"] = {k: m3.get(k) for k in ("mode", "field_ok", "field_reason", "beta_exec_usdt", "beta_exec_gross_units", "book_gross_usdt",
                                                "sizing_gross_usdt", "n_targeted_names", "n_beta_missing", "betas_sha256", "n_betas", "n_fallback", "data_cutoff_ts")}
        need = (m3.get("mode") == "shadow" and m3.get("field_ok") is True and isinstance(m3.get("beta_exec_usdt"), (int, float))
                and isinstance(m3.get("book_gross_usdt"), (int, float)) and isinstance(m3.get("n_targeted_names"), int))
        li["betas_sha256_matches_target_live_field"] = (m3.get("betas_sha256") == betas_sha256(bp)) if bp else False
        if not need or not li["betas_sha256_matches_target_live_field"]:
            li["undecided"] = "record incomplete / not shadow / field not ok / betas sha differs"; und.append(f"{lab}: {li['undecided']}"); continue
        tw = {}
        amb = []
        for (a_ts, s, w) in O_min:
            if a_ts != ats: continue
            if w is None: amb.append(s); continue
            if s in tw and tw[s] != float(w): amb.append(s)
            tw[s] = float(w)
        G = float(m3["book_gross_usdt"])
        sw = sum(abs(v) for v in tw.values()); nz = {s: v for s, v in tw.items() if v != 0.0}
        missing_prod = sorted(s for s in nz if s not in bp)
        recon_prod = sum(nz[s] * G * float(bp[s]) for s in sorted(nz) if s in bp) if not missing_prod else None
        be = float(m3["beta_exec_usdt"])
        c1 = abs(sw - 1.0) <= 1e-9; c2 = len(nz) == int(m3["n_targeted_names"]); c3 = (recon_prod is not None and abs(recon_prod - be) <= 1e-9 * max(1.0, abs(be)))
        li["closure"] = {"n_order_symbols": len(tw), "n_nonzero_target": len(nz), "sum_abs_target_w": sw, "c1_sum_abs_w_is_1": c1,
                         "c2_nonzero_count_equals_n_targeted_names": c2, "c3_recon_with_prod_betas_equals_record": c3,
                         "recon_beta_exec_usdt_prod_betas": recon_prod, "ambiguous_symbols": len(amb), "targeted_without_prod_beta": len(missing_prod)}
        if not (c1 and c2 and c3 and not amb):
            li["undecided"] = "不可由记录重算 (closure failed)"; und.append(f"{lab}: not recomputable from the records"); continue
        miss_res = sorted(s for s in nz if s != BTC and (s not in res[A] or not res[A][s][3]))
        if miss_res:
            li["undecided"] = f"{len(miss_res)} targeted names without research data"; li["missing_research"] = miss_res; und.append(f"{lab}: research data missing"); continue
        be_res = sum(nz[s] * G * (1.0 if s == BTC else res[A][s][0]) for s in sorted(nz))
        li["beta_exec_usdt_research"] = be_res; li["beta_exec_usdt_record"] = be
        li["beta_exec_gross_units_research"] = be_res / float(m3["sizing_gross_usdt"]) if m3.get("sizing_gross_usdt") else None
        li["rel_exec"] = abs(be_res - be) / abs(be) if be != 0 else float("inf")
        li["pass"] = bool(li["rel_exec"] <= 0.01)
    with open(os.path.join(out, "B7_PER_NAME.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["anchor", "symbol", "class", "beta_prod", "n_obs_prod", "beta_res", "n_obs_res", "est_res", "abs_diff", "rel_diff"]); w.writerows(name_rows)
    rec["per_anchor"] = per_anchor
    comp = [per_anchor[l]["layer_ii"].get("pass") for l in ("A08", "A12")]
    if und or any(v is None for v in comp): verdict = "UNDECIDED"
    elif all(comp): verdict = "PASS"
    else: verdict = "FAIL"
    if verdict == "UNDECIDED" and ctrl["pass"] and all(v is not None for v in comp) and not all(comp): verdict = "FAIL"
    rec["undecided_because"] = und; rec["VERDICT"] = verdict
    json.dump(rec, open(os.path.join(out, "B7_PARITY.json"), "w"), indent=1, default=float)
    ex = {l: per_anchor[l]["layer_ii"].get("rel_exec") for l in ("A08", "A12")}
    print(f"B7_PARITY VERDICT={verdict} rel_exec_A08={ex['A08']} rel_exec_A12={ex['A12']} control_max_dbeta={ctrl['max_abs_dbeta_clean']} "
          f"n_rel_over_1pct_A08={per_anchor['A08']['layer_i']['n_rel_over_1pct']} n_rel_over_1pct_A12={per_anchor['A12']['layer_i']['n_rel_over_1pct']} "
          f"undecided={und} out_sha256={sha_file(os.path.join(out, 'B7_PARITY.json'))}", flush=True)
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
