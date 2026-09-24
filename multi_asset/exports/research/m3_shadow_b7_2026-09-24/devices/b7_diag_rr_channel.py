#!/usr/bin/env python3
"""b7_diag_rr_channel.py — DIAGNOSTIC (not a re-judgement of B7). Pre-registration: docs/PREREG_b7_diag_L403_channel_2026-09-24.md
(frozen in the same commit, before any number). Question: are B7's per-name β differences caused by combo_stage.py L403 feeding
`_BOP.compute` the ch0 channel (±0.30 clipped, float16) instead of NC's RR = rr_from_ch0(ch0, boundary_raw) (raw values at the
boundary cells)?
Read-only: production snapshot files are np.load-ed; the production modules are imported from COPIES in devices/prod_copy/ whose sha256
must equal the live files' (no import from ~/wide_shadow ⇒ no __pycache__ written there). No venue call. Mac, /usr/bin/python3.
Blind state: orders copy read for (anchor_ts, symbol, target_w) only; execution-derived outputs are pooled sums.
usage: /usr/bin/python3 -B b7_diag_rr_channel.py <b7_inputs_dir (orders copy)> <out_dir>
"""
import csv, gzip, hashlib, json, math, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
B7 = os.path.dirname(HERE)
RUN = os.path.join(B7, "receipts/run_2026-09-24T13Z")
sys.path.insert(0, os.path.join(HERE, "prod_copy"))
sys.path.insert(0, "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/common")
import venue_quiet_window as VQW

WS = os.path.expanduser("~/wide_shadow")
LIVE_CODE = {"beta_overlay_producer.py": "b77c180d69170988780566e19d0ee4a0f85af25a9b9e9be08b6e4a386095fb58",
             "nc_contract.py": "316a0b9bcf1461401740ebd79a3292a9bfcdc49d56f111219ff6e126110650cb"}
SYMS = os.path.join(WS, "fea171/xfer_syms.npz")
A08, A12 = 1790236800, 1790251200
H4, ROW, BTC = 14400, 300, "BTCUSDT"
NROW = 180 * 48 + 1
CLIP_F16 = 0.2997


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def betas_sha256(betas):                                    # live/beta_overlay.py rule (same as b7_compare.py)
    return hashlib.sha256(json.dumps({k: float(v) for k, v in sorted(betas.items())}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def utc(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def q(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) == 0: raise ValueError("empty sequence")
    return {"n": int(len(x)), "p50": float(np.percentile(x, 50)), "p90": float(np.percentile(x, 90)), "p99": float(np.percentile(x, 99)), "max": float(x.max())}


def ols(x, y):
    dx = x - x.mean(); dy = y - y.mean(); sxx = float((dx * dx).sum())
    if not sxx > 0: raise ValueError("zero variance")
    return float(min(max(float((dx * dy).sum()) / sxx, -1.0), 4.0))


def prod_bars(rts, ret5, col, A):
    """Replicates compute()'s R4 / V for one column (checked against compute's own betas below)."""
    ai = int(np.nonzero(rts == A)[0][0]); lo = ai - (NROW - 1); assert lo >= 0
    R = np.asarray(ret5[lo:ai + 1, col], dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"): L = np.log1p(R)
    fin = np.isfinite(L)
    body = L[1:].reshape(180, 48); bok = fin[1:].reshape(180, 48).all(1); sok = fin[0:180 * 48:48]
    V = bok & sok
    return np.where(V, np.where(fin[1:].reshape(180, 48), body, 0.0).sum(1), np.nan), V, lo, ai


def main():
    inp, out = [os.path.abspath(a) for a in sys.argv[1:3]]; os.makedirs(out, exist_ok=True)
    st = VQW.quiet_window_status()
    if not st["open"]: raise SystemExit(f"quiet window not open — refused ({st})")
    rec = {"device": "b7_diag_rr_channel.py", "self_sha256": sha_file(os.path.abspath(__file__)), "status": "DIAGNOSTIC, NOT A RE-JUDGEMENT OF B7",
           "prereg": "docs/PREREG_b7_diag_L403_channel_2026-09-24.md", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "quiet_window_at_start": st, "inputs": {}}
    for f, want in LIVE_CODE.items():
        c, l = sha_file(os.path.join(HERE, "prod_copy", f)), sha_file(os.path.join(WS, "fea171", f))
        if not (c == l == want): raise SystemExit(f"{f}: copy {c[:8]} live {l[:8]} pinned {want[:8]} — refused")
        rec["inputs"][f] = want
    import beta_overlay_producer as BOP
    import nc_contract as NC
    Z = np.load(SYMS, allow_pickle=True); symbols = [str(s) for s in Z["symbols"]]; rec["inputs"]["xfer_syms.npz"] = sha_file(SYMS)
    P = json.load(open(os.path.join(RUN, "out/B7_PARITY.json"))); rec["inputs"]["B7_PARITY.json"] = sha_file(os.path.join(RUN, "out/B7_PARITY.json"))
    PN = {(r["anchor"], r["symbol"]): r for r in csv.DictReader(open(os.path.join(RUN, "out/B7_PER_NAME.csv")))}
    rec["inputs"]["B7_PER_NAME.csv"] = sha_file(os.path.join(RUN, "out/B7_PER_NAME.csv"))
    # research 4h closes (klines)
    kl = {}
    with gzip.open(os.path.join(RUN, "fetch/KLINES_RAW.jsonl.gz"), "rt") as f:
        for ln in f:
            d = json.loads(ln); kl[d["symbol"]] = {int(k[0]) // 1000 + H4: float(k[4]) for k in json.loads(d["body"])}
    rec["inputs"]["KLINES_RAW.jsonl.gz"] = sha_file(os.path.join(RUN, "fetch/KLINES_RAW.jsonl.gz"))
    O = []
    for l in open(os.path.join(inp, "orders_20260924.jsonl")):
        o = json.loads(l); O.append((o.get("anchor_ts"), o.get("symbol"), o.get("target_w")))
    A_rows = [json.loads(l) for l in open(os.path.join(inp, "anchors_20260924.jsonl"))]
    rec["inputs"]["orders_copy"] = sha_file(os.path.join(inp, "orders_20260924.jsonl")); rec["inputs"]["anchors_copy"] = sha_file(os.path.join(inp, "anchors_20260924.jsonl"))
    ch0_lists = {lab: [o["symbol"] for o in P["per_anchor"][lab]["layer_i"]["rel_over_1pct"]] for lab in ("A08", "A12")}
    focus = sorted(set(ch0_lists["A08"]) | set(ch0_lists["A12"]))
    per, name_rows, cell_rows = {}, [], []
    for A, lab in ((A08, "A08"), (A12, "A12")):
        pa = {"anchor": utc(A)}; per[lab] = pa
        sd = os.path.join(WS, "state/snap", str(A))
        sums = {ln.split()[1]: ln.split()[0] for ln in open(os.path.join(sd, "SHA256SUMS")) if ln.strip()}
        for f in ("rolling.npz", "boundary_raw.npz"):
            h = sha_file(os.path.join(sd, f))
            if sums.get(f) != h: raise SystemExit(f"{sd}/{f} sha {h[:8]} != SHA256SUMS {str(sums.get(f))[:8]} — refused")
            pa[f + "_sha256"] = h
        with np.load(os.path.join(sd, "rolling.npz"), allow_pickle=True) as r: rts, data = r["ts"].astype(np.int64), r["data"]
        with np.load(os.path.join(sd, "boundary_raw.npz")) as b: bts, bcol, braw = b["ts"].astype(np.int64), b["col"].astype(np.int64), b["raw"].astype(np.float32)
        if data.shape[1] != len(symbols): raise SystemExit("symbol axis differs from rolling data")
        ch0 = data[:, :, 0]
        tl = json.load(open(os.path.join(RUN, "inputs/target_live", f"{A}.json"))); fld = tl["beta_overlay"]; uni = list(tl["universe"])
        # ---- P0 ----
        f0 = BOP.compute(rts, ch0, symbols, uni, A)
        rec_sha = P["per_anchor"][lab]["layer_ii"]["record"]["betas_sha256"]
        p0_eq = (list(f0["betas"]) == list(fld["betas"])) and all(float(f0["betas"][k]) == float(fld["betas"][k]) for k in fld["betas"]) \
            and all(int(f0["n_obs"][k]) == int(fld["n_obs"][k]) for k in fld["n_obs"])
        p0 = {"bitwise_equal_to_production_field": bool(p0_eq), "sha_ch0_path": betas_sha256(f0["betas"]), "sha_record": rec_sha}
        p0["pass"] = bool(p0_eq and p0["sha_ch0_path"] == rec_sha); pa["P0"] = p0
        if not p0["pass"]: pa["UNAVAILABLE"] = "P0 failed"; continue
        # ---- RR ----
        RR = NC.rr_from_ch0(rts, ch0, bts, bcol, braw)
        ai = int(np.nonzero(rts == A)[0][0]); lo = ai - (NROW - 1)
        c32 = np.asarray(ch0[lo:ai + 1]).astype(np.float32); r32 = RR[lo:ai + 1]
        diff = ~((c32 == r32) | (np.isnan(c32) & np.isnan(r32)))
        pa["rr_vs_ch0_in_window"] = {"n_cells_differ": int(diff.sum()), "n_names_with_differing_cells": int(diff.any(0).sum()),
                                     "names_with_differing_cells": sorted(symbols[j] for j in np.nonzero(diff.any(0))[0]),
                                     "boundary_table_cells_total": int(len(bts)),
                                     "boundary_table_cells_in_window": int(((bts >= rts[lo]) & (bts <= A)).sum())}
        if diff.sum() == 0: pa["rr_is_noop"] = "RR ≡ ch0 in the β window at this anchor: switching the channel cannot change β here"
        for j in np.nonzero(diff.any(0))[0]:
            s = symbols[j]
            for i in np.nonzero(diff[:, j])[0]:
                cell_rows.append([lab, s, s in focus, utc(rts[lo + i]), float(c32[i, j]), float(r32[i, j]), float(r32[i, j]) - float(c32[i, j])])
        fr = BOP.compute(rts, RR, symbols, uni, A)
        # ---- layer (i) under RR ----
        rel, over = [], []
        for s in fr["betas"]:
            if s == BTC: continue
            row = PN.get((lab, s))
            if row is None or row["class"] != "both_estimated": continue
            if int(fr["n_obs"][s]) < 120: continue
            rb = float(row["beta_res"]); br = float(fr["betas"][s]); r_ = abs(br - rb) / abs(rb) if rb != 0 else float("inf"); rel.append(r_)
            name_rows.append([lab, s, float(row["beta_prod"]), br, rb, int(row["n_obs_prod"]), int(fr["n_obs"][s]), int(row["n_obs_res"]), float(row["rel_diff"]), r_])
            if r_ > 0.01: over.append(s)
        L0 = ch0_lists[lab]
        pa["layer_i_rr"] = {"rel": q(rel), "n_over_1pct_ch0": len(L0), "n_over_1pct_rr": len(over), "over_1pct_rr": sorted(over),
                            "removed": sorted(set(L0) - set(over)), "added": sorted(set(over) - set(L0)), "kept": sorted(set(L0) & set(over))}
        # ---- layer (ii) under RR (pooled) ----
        li = P["per_anchor"][lab]["layer_ii"]; recd = li["record"]; G = float(recd["book_gross_usdt"])
        row = [r for r in A_rows if int(float(r["anchor_ts"]) // H4 * H4) == A]; assert len(row) == 1; ats = row[0]["anchor_ts"]
        tw = {}
        for a_ts, s, w in O:
            if a_ts == ats and w is not None: tw[s] = float(w)
        nz = {s: w * G for s, w in tw.items() if w != 0.0}
        c1 = abs(sum(abs(v) for v in tw.values()) - 1.0) <= 1e-9; c2 = len(nz) == int(recd["n_targeted_names"])
        c3 = abs(sum(nz[s] * float(fld["betas"][s]) for s in sorted(nz)) - float(recd["beta_exec_usdt"])) <= 1e-9 * max(1.0, abs(float(recd["beta_exec_usdt"])))
        if not (c1 and c2 and c3): pa["layer_ii_rr"] = {"undecided": "不可由记录重算 (closure failed)"}; continue
        be_rr = sum(nz[s] * float(fr["betas"][s]) for s in sorted(nz)); be_res = float(li["beta_exec_usdt_research"])
        gap = {s: nz[s] * ((1.0 if s == BTC else float(PN[(lab, s)]["beta_res"])) - float(fr["betas"][s])) for s in nz}
        gap_tot = sum(gap.values())
        pa["layer_ii_rr"] = {"closure_c1_c2_c3": [c1, c2, c3], "beta_exec_rr_usdt": be_rr, "beta_exec_research_usdt": be_res,
                             "beta_exec_record_usdt": float(recd["beta_exec_usdt"]), "rel_exec_rr": abs(be_res - be_rr) / abs(be_rr),
                             "rel_exec_ch0_B7": li["rel_exec"], "rr_minus_record_usdt": be_rr - float(recd["beta_exec_usdt"]),
                             "gap_rr_usdt": gap_tot, "share_of_gap_rr_from_names_still_over_1pct": (sum(v for s, v in gap.items() if s in over) / gap_tot) if gap_tot else None,
                             "n_targeted_still_over_1pct": len(set(over) & set(nz))}
        # ---- §3-6 attribution for names still > 1% (descriptive) ----
        att = {}
        bnd = [A - (179 - k) * H4 for k in range(180)]                      # bar end times T
        jb = symbols.index(BTC)
        xr_rr, vb_rr, _, _ = prod_bars(rts, RR, jb, A)
        xres = np.array([math.log(kl[BTC][T] / kl[BTC][T - H4]) if (T in kl[BTC] and T - H4 in kl[BTC]) else np.nan for T in bnd])
        tabset = set(zip(bts.tolist(), bcol.tolist()))
        for s in sorted(over):
            j = symbols.index(s)
            yr, vr, lo_, ai_ = prod_bars(rts, RR, j, A)
            m_p = vr & vb_rr
            chk = ols(xr_rr[m_p], yr[m_p]) if m_p.sum() >= 120 else 1.0
            yres = np.array([math.log(kl[s][T] / kl[s][T - H4]) if (s in kl and T in kl[s] and T - H4 in kl[s]) else np.nan for T in bnd])
            m_r = np.isfinite(yres) & np.isfinite(xres)
            b_res_all = ols(xres[m_r], yres[m_r]); b_res_csv = float(PN[(lab, s)]["beta_res"])
            m_rv = m_r & m_p
            b_res_V = ols(xres[m_rv], yres[m_rv])
            dr = yr - yres
            flag = np.isfinite(dr) & (np.abs(dr) > 1e-3)
            n_clip = n_tab = n_none = 0
            for k in np.nonzero(flag)[0]:
                rows = range(lo_ + 1 + k * 48, lo_ + 1 + (k + 1) * 48)
                has_clip = any(abs(float(ch0[i, j])) >= CLIP_F16 and float(RR[i, j]) == float(np.float32(ch0[i, j])) for i in rows)
                has_tab = any((int(rts[i]), j) in tabset for i in rows)
                n_clip += has_clip; n_tab += has_tab; n_none += (not has_clip and not has_tab)
            att[s] = {"beta_rr": float(fr["betas"][s]), "beta_res": b_res_csv, "own_ols_reproduces_beta_rr": abs(chk - float(fr["betas"][s])) <= 1e-12,
                      "own_ols_reproduces_beta_res": abs(b_res_all - b_res_csv) <= 1e-9, "n_obs_rr": int(m_p.sum()), "n_obs_res": int(m_r.sum()),
                      "beta_res_on_prod_valid_bars": b_res_V, "validity_set_part": b_res_V - b_res_csv, "return_value_part": float(fr["betas"][s]) - b_res_V,
                      "n_bars_absdiff_r4h_gt_1e-3": int(flag.sum()), "of_which_with_unoverridden_clip_cell": int(n_clip),
                      "of_which_with_boundary_table_cell": int(n_tab), "of_which_neither": int(n_none),
                      "max_abs_diff_r4h": float(np.nanmax(np.abs(dr))) if np.isfinite(dr).any() else None}
        pa["attribution_names_still_over_1pct"] = att
    rec["per_anchor"] = per
    # ---- frozen reading (prereg §4) ----
    ok = [lab for lab in ("A08", "A12") if per[lab].get("P0", {}).get("pass")]
    if not ok: reading = "UNAVAILABLE"
    else:
        cA = {lab: per[lab]["layer_i_rr"]["n_over_1pct_rr"] <= per[lab]["layer_i_rr"]["n_over_1pct_ch0"] // 2 for lab in ok}
        cB = {lab: (per[lab].get("layer_ii_rr", {}).get("rel_exec_rr") is not None and per[lab]["layer_ii_rr"]["rel_exec_rr"] < 0.01) for lab in ok}
        rec["conditions"] = {"A_names_at_least_halved": cA, "B_rel_exec_rr_below_1pct": cB, "anchors_with_P0": ok}
        reading = "SUPPORTS_L403_WRONG_CHANNEL" if (len(ok) == 2 and all(cA.values()) and all(cB.values())) else "NOT_SUPPORTED_AS_SOLE_CAUSE"
    rec["READING"] = reading
    json.dump(rec, open(os.path.join(out, "B7_DIAG_RR.json"), "w"), indent=1, default=float)
    with open(os.path.join(out, "B7_DIAG_RR_per_name.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["anchor", "symbol", "beta_prod_ch0", "beta_rr", "beta_res", "n_obs_prod_ch0", "n_obs_rr", "n_obs_res", "rel_ch0", "rel_rr"]); w.writerows(name_rows)
    with open(os.path.join(out, "B7_DIAG_RR_cells.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["anchor", "symbol", "in_ch0_over_1pct_union", "row_close_utc", "ch0_as_f32", "rr", "rr_minus_ch0"]); w.writerows(cell_rows)
    s = {lab: (per[lab].get("layer_i_rr", {}).get("n_over_1pct_ch0"), per[lab].get("layer_i_rr", {}).get("n_over_1pct_rr"),
               per[lab].get("layer_ii_rr", {}).get("rel_exec_rr")) for lab in ("A08", "A12")}
    print(f"B7_DIAG_RR READING={reading} A08(n_ch0,n_rr,rel_exec_rr)={s['A08']} A12(n_ch0,n_rr,rel_exec_rr)={s['A12']} "
          f"P0={[per[l].get('P0', {}).get('pass') for l in ('A08', 'A12')]} out_sha256={sha_file(os.path.join(out, 'B7_DIAG_RR.json'))}", flush=True)
    sys.exit(0 if reading != "UNAVAILABLE" else 1)


if __name__ == "__main__":
    main()
