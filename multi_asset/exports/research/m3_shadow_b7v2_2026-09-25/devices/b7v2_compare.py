#!/usr/bin/env python3
"""b7v2_compare.py — B7 v2 for ONE m3_beta_v2 shadow anchor A, research side (method (a)). Mac, /usr/bin/python3 + numpy.
Rule (frozen before any v2 shadow anchor): docs/DECISION_RULE_B7_v2_m3_shadow_2026-09-25.md (lead, b80f52b39). This device implements it
and adds only INSTRUMENT self-checks (a failed one ⇒ UNDECIDED, never PASS/FAIL). Written and committed before any v2 shadow anchor existed.

RESEARCH β_res (the prereg formula, m2_lib.py 93f8e760 unchanged): venue 4h klines (b7v2_fetch.py) → a 5-minute log-price grid on
[A − 180·4h, A] whose 4h-boundary rows hold log(close of the kline closing there) → m2_lib.bars_4h → m2_lib.betas_at(A) (180 completed 4h
bars ending at A, OLS with intercept on BTCUSDT, ≥ 120 valid pairs else 1.0, clip [−1, 4], BTC = 1). first_fin / last_fin = first / last
boundary with a kline; a missing kline between them = UNAVAILABLE boundary (both adjacent bars excluded); a name with no kline = MISSING.
This path is b7_compare.py's; its identity with the certified path was measured (b7v2_ctrl_diag.py, READING=H_SUPPORTED, receipts
6789185bb: path part 0 on 449/449 names bitwise). β_prod and β_res are expected to differ by float16 rounding of the production input
(control anchor: max 7.6e-4, p50 4.5e-5) — inside the rule's bands; the 1e-6 control of v1 is NOT used.

GATE (0) — version and self-check (rule §1 row (0)); every item must hold:
  0a the production field target_live/<A>.json `beta_overlay.version` == "m3_beta_v2";
  0b the executor's anchors record `m3_beta_overlay`: version_expected == "m3_beta_v2", mode == "shadow", field_ok is true;
  0c the record's betas_sha256 == live/beta_overlay.betas_sha256 rule applied to the field's betas (canonical JSON, recomputed here);
  0d method (b): the nc_m3_selfcheck.py output for A (run with the default --expect-version m3_beta_v2) ends with the line
     "M3_SELFCHECK <A> OK n=0" and holds "OK  published field version == expected: measured=m3_beta_v2".
LAYER (i) — per name (REPORTED, NOT A GATE): every non-BTC name of the production field. over-band ⇔ |β_prod − β_res| >
  max(0.01·|β_res|, 0.002); a name without research data is over-band with β_res None. Each over-band name gets a named reason, first match:
    venue_status_<S>   the venue status at fetch time (EXINFO_SUBSET.json; fetched in the quiet window after A — labelled as such) is not
                       TRADING, or the name is absent from exchangeInfo (S = ABSENT);
    no_research_data   no kline (fetch FAILED / empty);
    n_obs_differs      n_obs_prod != n_obs_res (the two sides saw different valid bars);
    unexplained        none of the above.
  Any unexplained name ⇒ the anchor is PENDING (「待查」): not counted as clean, not red (rule §1).
LAYER (ii) — book level (A GATE): β_exec_prod = the record's beta_exec_usdt; executed targets rebuilt from the plan rows of orders.jsonl
  (target_w × book_gross_usdt over the symbols with the row's anchor_ts — b7_compare.py's reconstruction); β_exec_res = Σ target_i·β_res_i
  (BTC 1). PASS ⇔ |β_exec_prod − β_exec_res| ≤ max(0.01·|β_exec_prod|, 0.001·nav_usdt) (nav_usdt from the same record).
INSTRUMENT self-checks (each ⇒ UNDECIDED, named): fetch manifest verdict COMPLETE for A and KLINES_RAW sha == manifest; the target_live copy
  sha == its .sha256 sidecar; exactly one anchors row with external_book.nominal_ts == A; closures c1 |Σ|target_w| − 1| ≤ 1e-9, c2 #non-zero
  == n_targeted_names, c3 Σ target_i·β_prod_i reproduces the record's beta_exec_usdt (rel 1e-9); no ambiguous target_w; every targeted
  non-BTC name has research data; nav_usdt a positive number.
STATUS of the anchor: UNDECIDED (any instrument check) · FAIL ((0) or (ii) fails) · PENDING ((0),(ii) pass, ≥ 1 unexplained (i) name) ·
  CLEAN ((0),(ii) pass, no unexplained name). Two consecutive CLEAN anchors are what the rule needs; this device judges one anchor.
Blind state: from orders.jsonl only (anchor_ts, symbol, target_w) are read; outputs hold sums/counts and per-name β (research + producer
fields), never per-name targets, fills or arms.
usage: /usr/bin/python3 -B b7v2_compare.py <inputs_dir> <fetch_dir> <selfcheck_txt> <A> <out_dir>
"""
import csv, gzip, hashlib, json, math, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m2_lib as M

H4, ROW, BTC, V2 = 14400, 300, "BTCUSDT", "m3_beta_v2"
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


def research_betas(kl, A):
    """b7_compare.py L91–117 construction (grid [A − 180·4h, A]) → {symbol: (beta, nobs, est, have)}"""
    syms = sorted(kl)
    if BTC not in syms: raise SystemExit("no BTCUSDT klines — refused")
    G0 = A - 180 * H4
    grid = np.arange(G0, A + 1, ROW, dtype=np.int64); nS = len(syms)
    LP = np.full((len(grid), nS), np.nan); ff = np.full(nS, -1, np.int64); lf = np.full(nS, -1, np.int64)
    bnd = np.arange(G0, A + 1, H4, dtype=np.int64); brow = ((bnd - G0) // ROW).astype(np.int64)
    ua_r, ua_c, bad = [], [], {}
    for j, s in enumerate(syms):
        px = {}
        for k in kl[s]:
            ot, ct, c = int(k[0]) // 1000, int(k[6]), float(k[4])
            if ct != (ot + H4) * 1000 - 1 or not (c > 0): bad.setdefault(s, []).append(ot); continue
            if G0 <= ot + H4 <= A: px[ot + H4] = c
        have = [t for t in bnd.tolist() if t in px]
        if not have: continue
        ff[j], lf[j] = min(have), max(have)
        last = np.nan
        for t, r0 in zip(bnd.tolist(), brow.tolist()):
            if t in px: last = math.log(px[t]); LP[r0, j] = last
            elif ff[j] <= t <= lf[j]: ua_r.append(r0); ua_c.append(j)
            nxt = r0 + H4 // ROW
            if nxt <= len(grid) - 1 and np.isfinite(last): LP[r0 + 1:nxt, j] = last
    T, R, V = M.bars_4h(LP, grid, ff, lf, np.array(ua_r, np.int64), np.array(ua_c, np.int64))
    B, NOBS, EST, _ = M.betas_at(T, R, V, np.array([A], np.int64), syms.index(BTC))
    res = {s: (float(B[0, j]), int(NOBS[0, j]), bool(EST[0, j]), bool(ff[j] >= 0)) for j, s in enumerate(syms)}
    return res, {"n_symbols": nS, "n_ua_boundaries": len(ua_r), "symbols_with_bad_klines": {k: len(v) for k, v in bad.items()}}


def main(argv):
    inp, fdir, scp, A, out = os.path.abspath(argv[1]), os.path.abspath(argv[2]), os.path.abspath(argv[3]), int(argv[4]), os.path.abspath(argv[5])
    os.makedirs(out, exist_ok=True)
    rec = {"device": "b7v2_compare.py", "self_sha256": sha_file(os.path.abspath(__file__)), "m2_lib_sha256": sha_file(os.path.join(HERE, "m2_lib.py")),
           "rule": "docs/DECISION_RULE_B7_v2_m3_shadow_2026-09-25.md (b80f52b39)", "anchor": A, "anchor_utc": utc(A),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "inputs": {}, "numpy": np.__version__, "python": sys.version.split()[0]}
    if rec["m2_lib_sha256"] != M2_SHA: raise SystemExit("m2_lib is not 93f8e760 — refused")
    if A % H4: raise SystemExit("A off the 4h grid — refused")
    und = []
    # ---- fetch ----
    man = json.load(open(os.path.join(fdir, "FETCH_MANIFEST.json")))
    rec["inputs"]["fetch_manifest"] = {"sha256": sha_file(os.path.join(fdir, "FETCH_MANIFEST.json")), "verdict": man.get("verdict"), "anchor": man.get("anchor"),
                                       "n_requests": man.get("n_requests"), "max_used_weight_1m": man.get("max_used_weight_1m")}
    if man.get("anchor") != A: und.append(f"fetch manifest is for anchor {man.get('anchor')}, not {A}")
    if man.get("verdict") != "COMPLETE": und.append(f"fetch verdict {man.get('verdict')}")
    if sha_file(os.path.join(fdir, "KLINES_RAW.jsonl.gz")) != (man.get("outputs") or {}).get("KLINES_RAW.jsonl.gz"): und.append("klines file sha != manifest")
    exp = os.path.join(fdir, "EXINFO_SUBSET.json"); EX = json.load(open(exp)) if os.path.isfile(exp) else None
    if EX is None or sha_file(exp) != (man.get("outputs") or {}).get("EXINFO_SUBSET.json"): und.append("EXINFO_SUBSET missing or sha != manifest")
    kl = {}
    with gzip.open(os.path.join(fdir, "KLINES_RAW.jsonl.gz"), "rt") as f:
        for ln in f:
            d = json.loads(ln); kl[d["symbol"]] = json.loads(d["body"])
    res, rec["research_grid"] = research_betas(kl, A)
    # ---- production copies ----
    tp = os.path.join(inp, "target_live", f"{A}.json"); want = open(tp + ".sha256").read()[:64]
    rec["inputs"]["target_live_copy_sha256"] = sha_file(tp)
    if rec["inputs"]["target_live_copy_sha256"] != want: und.append("target_live copy sha != its sidecar")
    F = json.load(open(tp)).get("beta_overlay") or {}; bp, nop = F.get("betas") or {}, F.get("n_obs") or {}
    day = time.strftime("%Y%m%d", time.gmtime(A))
    ap_, op_ = os.path.join(inp, f"anchors_{day}.jsonl"), os.path.join(inp, f"orders_{day}.jsonl")
    rec["inputs"]["anchors_copy_sha256"] = sha_file(ap_); rec["inputs"]["orders_copy_sha256"] = sha_file(op_)
    rows = [r for r in (json.loads(l) for l in open(ap_)) if (r.get("external_book") or {}).get("nominal_ts") == A]
    m3 = rows[0].get("m3_beta_overlay") if len(rows) == 1 else None
    if len(rows) != 1: und.append(f"{len(rows)} anchors rows with nominal_ts == A")
    if len(rows) == 1 and not isinstance(m3, dict): und.append("anchors row has no m3_beta_overlay record")
    m3 = m3 if isinstance(m3, dict) else {}
    # ---- gate (0) ----
    sc_lines = open(scp).read().splitlines(); rec["inputs"]["selfcheck_txt_sha256"] = sha_file(scp)
    g0 = {"0a_field_version_v2": F.get("version") == V2,
          "0b_record_v2_shadow_field_ok": (m3.get("version_expected") == V2 and m3.get("mode") == "shadow" and m3.get("field_ok") is True),
          "0c_record_betas_sha256_matches_field": bool(bp) and m3.get("betas_sha256") == betas_sha256(bp),
          "0d_selfcheck_ok_v2": bool(sc_lines) and sc_lines[-1].strip() == f"M3_SELFCHECK {A} OK n=0"
                                and any(l.startswith(f"  OK  published field version == expected: measured={V2}") for l in sc_lines)}
    rec["gate0"] = {"items": g0, "measured": {"field_version": F.get("version"), "record_version_expected": m3.get("version_expected"), "record_mode": m3.get("mode"),
                    "record_field_ok": m3.get("field_ok"), "record_betas_sha256": m3.get("betas_sha256"), "field_betas_sha256": betas_sha256(bp) if bp else None,
                    "selfcheck_last_line": sc_lines[-1] if sc_lines else None}, "pass": all(g0.values())}
    # ---- layer (i) ----
    exs = (EX or {}).get("symbols") or {}; absent = set((EX or {}).get("absent") or [])
    name_rows, over, cls = [], [], {}
    for s in sorted(bp):
        if s == BTC: continue
        p_b, p_n = float(bp[s]), int(nop[s])
        rb, rn, re_, have = res.get(s, (None, None, None, False))
        if not have: rb = rn = re_ = None
        vst = "ABSENT" if (s in absent or s not in exs) else exs[s].get("status")
        d_ = abs(p_b - rb) if rb is not None else None
        band = max(0.01 * abs(rb), 0.002) if rb is not None else None
        ob = (rb is None) or (d_ > band)
        reason = None
        if ob:
            if vst != "TRADING": reason = f"venue_status_{vst}"
            elif rb is None: reason = "no_research_data"
            elif p_n != rn: reason = "n_obs_differs"
            else: reason = "unexplained"
            over.append({"symbol": s, "beta_prod": p_b, "beta_res": rb, "abs_diff": d_, "band": band, "n_obs_prod": p_n, "n_obs_res": rn,
                         "est_res": re_, "venue_status_at_fetch": vst, "reason": reason})
            cls[reason] = cls.get(reason, 0) + 1
        name_rows.append([s, p_b, p_n, rb, rn, re_, d_, band, ob, vst, reason])
    diffs = [r[6] for r in name_rows if r[6] is not None]
    n_unexpl = cls.get("unexplained", 0)
    rec["layer_i"] = {"role": "REPORTED, NOT A GATE (rule §1)", "n_names_non_btc": len(name_rows), "abs_diff": q(diffs), "n_over_band": len(over),
                      "over_band_by_reason": cls, "n_unexplained": n_unexpl, "over_band": over,
                      "venue_status_note": f"status read from exchangeInfo at {(EX or {}).get('fetched_utc')} (quiet window after A), not at A"}
    # ---- layer (ii) ----
    li = {}; rec["layer_ii"] = li
    tw, amb = {}, []
    for l in open(op_):
        o = json.loads(l); a_ts, s, w = o.get("anchor_ts"), o.get("symbol"), o.get("target_w")      # only these three keys are read
        if len(rows) != 1 or a_ts != rows[0].get("anchor_ts"): continue
        if w is None: amb.append(s); continue
        if s in tw and tw[s] != float(w): amb.append(s)
        tw[s] = float(w)
    G, be, nav = m3.get("book_gross_usdt"), m3.get("beta_exec_usdt"), m3.get("nav_usdt")
    sw = sum(abs(v) for v in tw.values()); nz = {s: v for s, v in tw.items() if v != 0.0}
    miss_prod = sorted(s for s in nz if s not in bp)
    num = all(isinstance(x, (int, float)) for x in (G, be, nav))
    recon = sum(nz[s] * float(G) * float(bp[s]) for s in sorted(nz)) if (not miss_prod and num and nz) else None
    c1 = abs(sw - 1.0) <= 1e-9; c2 = len(nz) == m3.get("n_targeted_names"); c3 = recon is not None and abs(recon - float(be)) <= 1e-9 * max(1.0, abs(float(be)))
    li["closure"] = {"n_order_symbols": len(tw), "n_nonzero_target": len(nz), "sum_abs_target_w": sw, "c1": c1, "c2": c2, "c3": c3,
                     "recon_beta_exec_usdt_prod_betas": recon, "ambiguous_symbols": len(amb), "targeted_without_prod_beta": len(miss_prod)}
    if not (c1 and c2 and c3 and not amb): und.append("layer (ii) not recomputable from the records (closure)")
    if not (isinstance(nav, (int, float)) and nav > 0): und.append("nav_usdt not a positive number")
    miss_res = sorted(s for s in nz if s != BTC and (s not in res or not res[s][3]))
    if miss_res: und.append(f"{len(miss_res)} targeted names without research data"); li["targeted_without_research_data"] = miss_res
    if not und:
        be_res = sum(nz[s] * float(G) * (1.0 if s == BTC else res[s][0]) for s in sorted(nz))
        tol = max(0.01 * abs(float(be)), 0.001 * float(nav))
        li.update({"beta_exec_prod_usdt": float(be), "beta_exec_res_usdt": be_res, "abs_diff_usdt": abs(float(be) - be_res), "nav_usdt": float(nav),
                   "tolerance_usdt": tol, "tolerance_rule": "max(0.01·|β_exec_prod|, 0.001·NAV)", "rel_to_beta_exec": abs(float(be) - be_res) / abs(float(be)) if be else None,
                   "pass": abs(float(be) - be_res) <= tol})
    # ---- status ----
    if und: status = "UNDECIDED"
    elif not rec["gate0"]["pass"] or not li.get("pass"): status = "FAIL"
    elif n_unexpl: status = "PENDING"
    else: status = "CLEAN"
    rec["instrument_undecided_because"] = und; rec["STATUS"] = status
    with open(os.path.join(out, f"B7V2_PER_NAME_{A}.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["symbol", "beta_prod", "n_obs_prod", "beta_res", "n_obs_res", "est_res", "abs_diff", "band", "over_band", "venue_status_at_fetch", "reason"])
        w.writerows(name_rows)
    op = os.path.join(out, f"B7V2_{A}.json"); json.dump(rec, open(op, "w"), indent=1, default=float)
    print(f"B7V2 A={A} ({utc(A)}) STATUS={status} gate0={rec['gate0']['pass']} ii_abs_usdt={li.get('abs_diff_usdt')} ii_tol_usdt={li.get('tolerance_usdt')} "
          f"ii_pass={li.get('pass')} n_over_band={len(over)} n_unexplained={n_unexpl} undecided={und} out_sha256={sha_file(op)}", flush=True)
    return {"CLEAN": 0, "PENDING": 4, "FAIL": 1, "UNDECIDED": 2}[status]


if __name__ == "__main__":
    sys.exit(main(sys.argv))
