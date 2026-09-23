#!/usr/bin/env python3
"""Deploy checks A6 (pre-swap: one live anchor after the fetch-list change, OLD models) and B6 (first live anchor after the swap, NEW
models) — DEPLOY_new_servable_models_2026-09-23.md. Mac, production venv (~/wide_shadow/venv/bin/python), quiet window, READ-ONLY.
Reads only production's archived snapshot of anchor A (state/snap/<A>/: rolling.npz, aux.json, leg_returns_live.json,
combo_live_status.json — written by combosnap after the anchor) plus state/target_live/<A>.json, state/target_combo/<A>.json,
state/weights_combo/<A>.npz, fea171/state_H_{kc,fc}_<A-4h>.npz and the bundle config. Never writes ~/wide_shadow or ~/dl_quant_live;
scratch goes to --out.
Checks (bitwise unless stated):
 C0 identity   target_live/<A>.json booster_sha / f10_sha == sha256 of --king / --f10 (the models that must be in service at A).
 C1 reproduce  the producer King block (shadow_loop_v3.py L486-L553 verbatim; fetch list = config symbols_fetch, or symbols_live when absent;
               base = aux base_syms) on the snapshot ⇒ members == prev_rec members; legz king == xz(booster(X78)); rev24; fund == prev_rec.
 C2a fetch     the names the training rule could select must all be FETCHED: expected = the anchor's venue TRADING perpetual list
    coverage   (aux base_syms, read by the producer from exchangeInfo at A) ∩ the 829 axis ∩ crypto class; PASS iff expected ⊆ fetch list.
               WHY (P4 control 2026-09-23T16Z): C2 alone is VACUOUS for a missing fetch list — legality is computed from the rolling
               cache, and a name that is not fetched has no bars there, so it is never legal and never a training candidate either;
               C2 then passes with 0 differences although the fetch list lacks ~70 legal names. C2a reads legality's precondition
               (being fetched) from an independent source (the venue list).
 C2 training   candidates = SPEC legal (TRADABLE W24H ∧ LIVE on the snapshot's last 288 rows, the function validated against the x0918r
    rule       mask in P5_DATA_PARITY) ∧ crypto class ⇒ the same King block with the non-candidates removed ⇒ members_train.
               PASS if equal; otherwise every differing name is listed with its fetch / legal / crypto flags; a difference is NAMED R1 only if
               the name is in the fetch list, is selected by the producer and is NOT legal (the producer's screen has no legal mask).
 C3 combo      combo_target.step on the recomputed serving inputs (F10 numpy scores from X171 recomputed with the production mini pipeline
               and --f10; seats = the seat rule of combo_stage L56-64 on the snapshot leg-return file; kc/fc = production state_H at A-4h;
               rn8 from the snapshot ledger; qv4h from the snapshot cache; LIVE_MASK = target_live universe) == production weights_combo/<A>
               (float32 as stored); publish flag == combo_live_status ok; w3_masked == target_combo w3_masked.
Verdict line `NEWS_LIVE_CHECK VERDICT=PASS|FAIL anchor=<utc> ...`; exit 0 only on PASS (C0 ∧ C1 ∧ C2a ∧ C3 ∧ (C2 or all C2 differences R1)).
Control (run before the fetch-list change, on any current anchor): C2a must FAIL naming the unfetched TRADING crypto axis names — proves the
device can see a missing fetch list (the first control run showed that C2 alone cannot).
usage: ~/wide_shadow/venv/bin/python news_live_check.py --anchor A --king F --f10 F --crypto P1_members_2025H2on.npz --out DIR
"""
import os, sys, json, time, shutil, hashlib, argparse
import numpy as np

HOME = os.path.expanduser("~"); WS = os.environ.get("WIDE_SHADOW_HOME", f"{HOME}/wide_shadow"); P = f"{HOME}/cc_tmp/news_20260923"
sys.path.insert(0, f"{P}/devices"); sys.path.insert(0, f"{P}/deploy")
import mac_candidate_acceptance as CA          # sets news_hist_features to the sha-verified producer copies (P5-0 / P5-a)
import news_hist_features as H
import news_legs as NL
CH = ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def legal_spec(block):
    """verbatim mac_p5_datacheck.legal_spec: block (288, N, 7) f16 rows (A−24h, A] ⇒ TRADABLE W24H ∧ LIVE"""
    lc = block[:, :, 4].astype(np.float32); lq = block[:, :, 3].astype(np.float32)
    return (np.isfinite(lc) & (lc > 0)).any(0) & np.isfinite(lq).any(0)


def fetch_coverage(base_syms, panel, crypto, fetch):
    """C2a: expected = venue TRADING perpetuals at A (aux base_syms) ∩ 829 axis ∩ crypto; returns (missing sorted, extra sorted)"""
    ax = {s: j for j, s in enumerate(panel)}
    expected = {s for s in base_syms if s in ax and bool(crypto[ax[s]])}
    f = set(fetch)
    return sorted(expected - f), sorted(f - expected), len(expected)


def main():
    ap = argparse.ArgumentParser(allow_abbrev=False)
    for k in ("king", "f10", "crypto", "out"): ap.add_argument("--" + k, required=True)
    ap.add_argument("--anchor", type=int, required=True)
    a = ap.parse_args(); A = a.anchor; os.makedirs(f"{a.out}/work", exist_ok=True)
    utc = time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(A)); snap = f"{WS}/state/snap/{A}"
    for f in ("rolling.npz", "aux.json", "leg_returns_live.json", "combo_live_status.json"): assert os.path.exists(f"{snap}/{f}"), f"snapshot missing {f}"
    cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; NW = len(syms); sidx = {s: j for j, s in enumerate(syms)}
    fetch = list(cfg.get("symbols_fetch") or cfg["symbols_live"])
    z = np.load(f"{snap}/rolling.npz", allow_pickle=True); ts = z["ts"].astype(np.int64); d = np.array(z["data"], np.float16)
    aux = json.load(open(f"{snap}/aux.json")); pr = aux["prev_rec"]
    assert int(ts[-1]) == A and int(aux["last_anchor"]) == A and int(pr["anchor_ts"]) == A, "snapshot is not anchor A"
    tl = json.load(open(f"{WS}/state/target_live/{A}.json")); tc = json.load(open(f"{WS}/state/target_combo/{A}.json"))
    status = json.load(open(f"{snap}/combo_live_status.json"))
    r = {"anchor": A, "utc": utc, "device_sha256": sha(os.path.abspath(__file__)), "fetch_n": len(fetch), "has_symbols_fetch": "symbols_fetch" in cfg,
         "inputs": {"king": {"path": a.king, "sha256": sha(a.king)}, "f10": {"path": a.f10, "sha256": sha(a.f10)}, "crypto": {"path": a.crypto, "sha256": sha(a.crypto)}}}
    # C0
    r["C0"] = {"target_live_booster_sha": tl.get("booster_sha"), "target_live_f10_sha": tl.get("f10_sha"),
               "PASS": tl.get("booster_sha") == r["inputs"]["king"]["sha256"] and tl.get("f10_sha") == r["inputs"]["f10"]["sha256"]}
    # C1 reproduction
    import lightgbm as lgb
    kb = H._king_block(); xz_in_base, xz = NL.prod_funcs(); booster = lgb.Booster(model_file=a.king)
    st = H._St(); st.cd = d; st.live = fetch; st.sym_idx = sidx; st.ledger = aux["ledger_tail"]; st.ema = aux["ema"]; st.NW = NW
    row_of = {int(t): i for i, t in enumerate(ts)}
    out = kb(st, A, cfg["params"], cfg, row_of, list(aux["base_syms"]), H._Diag(), lambda x: None)
    m = out["m"]; pred = booster.predict(out["X"])
    lz = {"king": xz(pred), "rev24": xz(-out["wstat"](0, 288, "sum")[m]), "fund": xz_in_base(out["fe_v"][m], [syms[int(j)] for j in m], out["base_vals"])}
    c1 = {"members_equal": [int(x) for x in m] == pr["members"]}
    for k in ("king", "rev24", "fund"):
        c1[f"legz_{k}_bitwise"] = CA.bits_eq(np.nan_to_num(lz[k]), np.array(pr["legz"][k], np.float64), np.float64) if len(lz[k]) == len(pr["legz"][k]) else False
    c1["PASS"] = all(c1.values()); r["C1"] = c1
    # C2a fetch coverage (independent of the rolling cache)
    crypto = np.load(a.crypto)["crypto"].astype(bool); assert crypto.shape == (NW,)
    miss, extra, n_exp = fetch_coverage(aux["base_syms"], syms, crypto, fetch)
    r["C2a"] = {"expected_n": n_exp, "fetch_n": len(fetch), "missing_n": len(miss), "missing": miss, "fetched_not_expected": extra, "PASS": not miss}
    # C2 training rule
    legal = legal_spec(d[-288:]); cand = legal & crypto
    st2 = H._St(); d2 = d.copy(); d2[:, ~cand, :] = np.nan; st2.cd = d2; st2.live = [syms[j] for j in np.flatnonzero(cand)]; st2.sym_idx = sidx
    st2.ledger = aux["ledger_tail"]; st2.ema = aux["ema"]; st2.NW = NW
    out2 = kb(st2, A, cfg["params"], cfg, row_of, list(st2.live), H._Diag(), lambda x: None)
    mt = set(int(x) for x in out2["m"]); ms = set(int(x) for x in pr["members"]); fset = set(fetch)
    diff = [{"name": syms[j], "side": "producer_only" if j in ms else "training_only", "in_fetch": syms[j] in fset, "legal": bool(legal[j]), "crypto": bool(crypto[j])}
            for j in sorted(ms ^ mt)]
    for x in diff: x["R1"] = x["side"] == "producer_only" and x["in_fetch"] and not x["legal"]
    r["C2"] = {"members_equal": not diff, "n_diff": len(diff), "diff": diff, "n_candidates": int(cand.sum()),
               "PASS": not diff, "PASS_or_named_R1": (not diff) or all(x["R1"] for x in diff)}
    # C3 combo (serving inputs recomputed from the snapshot)
    S = H.replay_anchor(A, d, ts, syms, CH, np.array([s in fset for s in syms]), aux["ema"], aux["ledger_tail"], cfg["params"], cfg, f"{a.out}/work", holes=None, cols="members")
    assert [int(x) for x in S["m"]] == [int(x) for x in m], "replay members != King block members"
    M10 = np.load(a.f10); from scipy.special import erf
    X171 = np.concatenate([S["X82"].astype(np.float32), S["X89"]], 1)
    xz_in = np.nan_to_num(np.clip((X171 - M10["mu"]) / M10["sd_"], -5, 5)); g = lambda x: 0.5 * x * (1 + erf(x / np.sqrt(2)))
    h = g(xz_in @ M10["w0"].T + M10["b0"]); h = g(h @ M10["w1"].T + M10["b1"]); f10 = (h @ M10["w2"].T + M10["b2"]).squeeze(-1)
    lrj = json.load(open(f"{snap}/leg_returns_live.json")); LRs = np.stack([np.array(lrj[k], np.float64) for k in ("king", "rev24", "fund")], 1)
    w3 = CA.msharpe(LRs, cfg["params"]["msharpe_look"])
    led = aux["ledger_tail"]
    rn8 = np.array([(float(led[syms[j]][-1][1]) * (8.0 / (float(led[syms[j]][-1][2]) or 8.0))) if led.get(syms[j]) else np.nan for j in m])
    ai = int(np.searchsorted(ts, A, side="right")) - 1; CDf = d.astype(np.float32); qseg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 3]
    finq = np.isfinite(qseg); qvm = np.where(finq, qseg, 0).sum(0) / np.maximum(finq.sum(0), 1); qv = np.expm1(np.clip(qvm[m], 0, 30)) * 48
    keep = set(tl.get("universe") or []); legal_mask = np.array([s in keep for s in syms]) if keep else np.ones(NW, bool)
    prev = {}
    for tag in ("kc", "fc"):
        p_ = f"{WS}/fea171/state_H_{tag}_{A - 14400}.npz"; v = np.zeros(NW)
        if os.path.exists(p_):
            zz = np.load(p_); assert int(zz["anchor"]) == A - 14400; v[zz["idx"].astype(int)] = zz["val"].astype(np.float64)
        prev[tag] = v
    import combo_target as CT
    CT.ROOT = __import__("pathlib").Path(f"{a.out}/ctroot"); os.makedirs(f"{a.out}/ctroot/vendor_live/fea171", exist_ok=True)
    shutil.copy2(f"{WS}/fea171/combo_stage.py", f"{a.out}/ctroot/vendor_live/fea171/combo_stage.py")
    o = CT.step(np.array(pr["legz"]["king"]), f10, np.array(pr["legz"]["fund"]), w3, rn8, m, qv, legal_mask, cfg["params"], prev["kc"], prev["fc"], "scaled_diagnostic")
    raw = np.zeros(NW); wc = f"{WS}/state/weights_combo/{A}.npz"
    if os.path.exists(wc) and status.get("ok"):
        wz = np.load(wc); raw[wz["idx"].astype(int)] = wz["val"].astype(np.float64)
    ser = np.where(np.abs(o["raw"]) > 1e-9, o["raw"], 0.0).astype(np.float32).astype(np.float64) if o["raw"] is not None else None
    c3 = {"publish_production": bool(status.get("ok")), "publish_recomputed": bool(o["accepted"]),
          "w3_masked_equal": [round(float(x), 6) for x in CA.masked(w3)] == tc["w3_masked"],
          "kc_prev_found": bool(np.abs(prev["kc"]).sum() > 0), "fc_prev_found": bool(np.abs(prev["fc"]).sum() > 0)}
    c3["publish_equal"] = c3["publish_production"] == c3["publish_recomputed"]
    c3["combo_raw_f32_bitwise"] = (not c3["publish_production"]) or (ser is not None and CA.bits_eq(ser, raw, np.float64))
    if ser is not None and c3["publish_production"]: c3["combo_raw_maxabs"] = float(np.abs(ser - raw).max())
    c3["n_f10_scored"] = int(np.isfinite(f10).sum()); c3["target_combo_n_f10_scored"] = tc.get("n_f10_scored")
    c3["PASS"] = c3["publish_equal"] and c3["combo_raw_f32_bitwise"] and c3["w3_masked_equal"] and c3["kc_prev_found"] and c3["fc_prev_found"]
    r["C3"] = c3
    ok = r["C0"]["PASS"] and r["C1"]["PASS"] and r["C2a"]["PASS"] and r["C3"]["PASS"] and r["C2"]["PASS_or_named_R1"]
    r["VERDICT"] = "PASS" if ok else "FAIL"
    p = f"{a.out}/NEWS_LIVE_CHECK_{A}.json"; json.dump(r, open(p, "w"), indent=1)
    print(f"NEWS_LIVE_CHECK VERDICT={r['VERDICT']} anchor={utc} C0={r['C0']['PASS']} C1={r['C1']['PASS']} C2a={r['C2a']['PASS']}(missing {r['C2a']['missing_n']} of {r['C2a']['expected_n']}) C2={r['C2']['PASS']}(n_diff {r['C2']['n_diff']}, "
          f"all_R1 {r['C2']['PASS_or_named_R1']}) C3={r['C3']['PASS']} fetch_n={len(fetch)} receipt={p} sha256={sha(p)}", flush=True)
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    main()
