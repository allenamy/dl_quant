#!/usr/bin/env python3
"""GATE F — parity of the object-B path with the archived live targets (PREREG_object_B_recipe_oof_and_object_A_paper_2026-09-19 §3 S5).
Comparison type (3) packaging/prediction parity — NOT a return. Live models only (king 8d79186b, F10 351ae26b); never used for history.

Per anchor A (one process per anchor; the producer module binds its home at import):
  F-1   combo stage from the ARCHIVED producer state of A (combosnap snapshot A + archived weights/<A−4h>.npz + state_H_*_<A−4h>.npz + archived
        king file) with the object-B F10 path: scorer device (production combo_stage L1–176 verbatim) → injection (rank/128 + identity model)
        → combo replay device ⇒ target_live must equal the archived traded file name-by-name, bit-for-bit.
  PC    positive control: the same combo replay device with need=True (real 171 pipeline, live model), no injection ⇒ must equal the archive.
  NC1   negative control: two members' F10 scores swapped (different ranks) ⇒ must NOT equal the archive.
  F-2   end to end: producer state rebuilt from snapshot A−4h (float64 H / ema / ledger / prev_rec / base; LR = bundle + snapshot LR), cache =
        snapshot A rolling, exchangeInfo = snapshot A base_syms, funding rows = snapshot A ledger_tail; FoldBooster('live') ⇒ weights/<A>.npz
        bitwise = archive, prev_rec bitwise = snapshot A; then the F-1 path on THIS state ⇒ target_live bitwise = archive.
  NC2   negative control: FoldBooster with the retrained fold 2025 instead of the live booster ⇒ king weights must differ.
usage: gate_f.py --anchor A     |     gate_f.py --summarize"""
import os, sys, json, time, copy, shutil, resource, argparse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import b_lib as BL
import b_driver as BD

R = BD.R; STAGE = BD.STAGE; OUTD = f"{R}/receipts/gate_f"; TAR_SHA = "33910c01c7ad253d952613cead5ecf627d467126c7bb88598efa36ac4c9e7495"
LIVE_F10_SHA = "351ae26bd6b4a203431a280427fc0bbc968c66e903532168765d654e7e57b3a4"
FP26_PATCH_UTC = "2026-09-17T16:00:00Z"
COL = {s: j for j, s in enumerate(json.load(open(BD.SRC["bundle_config"][0]))["symbols_panel"])}
COLN = {j: s for s, j in COL.items()}


def child_maxrss_mb(): return round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024.0, 1)


def stage_state(ws, A, snap_dir, with_combo_state=True):
    """archived producer state of A: snapshot A aux/rolling/LR, weights/<A−4h>, king file, state_H_*_<A−4h>."""
    for f in ("aux.json", "rolling.npz", "leg_returns_live.json"): shutil.copy2(f"{snap_dir}/{f}", f"{ws}/state/{f}")
    Ap = A - BL.H4
    shutil.copy2(f"{STAGE}/archive/weights/{Ap}.npz", f"{ws}/state/weights/{Ap}.npz")
    shutil.copy2(f"{STAGE}/archive/target_live_king/{A}.json", f"{ws}/state/target_live/{A}.json")
    shutil.copy2(f"{STAGE}/archive/target_live_king/{A}.json.sha256", f"{ws}/state/target_live/{A}.json.sha256")
    if with_combo_state:
        for leg in ("f10", "kc", "fc"): shutil.copy2(f"{STAGE}/archive/fea171/state_H_{leg}_{Ap}.npz", f"{ws}/fea171/state_H_{leg}_{Ap}.npz")


def run_scorer(root, ws, A, model_path):
    BL.clear_mini(f"{ws}/fea171"); shutil.copy2(model_path, f"{ws}/fea171/f10_live_s42_np.npz")
    out = f"{root}/score_{A}.npz"
    env = {"PATH": "/usr/bin:/bin", "HOME": root, "LC_CTYPE": "C.UTF-8", "WIDE_SHADOW_HOME": ws, "F10_SCORE_OUT": out,
           "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "_PY": BD.VENV_PY}
    rc, lines, dt = BL.run_device(f"{HERE}/f10_scorer_3520d363.py", f"{ws}/fea171", env, f"{root}/scorer_{A}.log")
    assert rc == 0, (rc, lines[-6:])
    z = np.load(out); assert int(z["anchor"]) == A and bool(z["need_ran"]), "scorer must run the full pipeline (need=True)"
    return {"pm": z["pm"].astype(np.int64), "f10": z["f10_pm"].astype(np.float64), "okf": int(z["okf"].sum()), "model_sha": str(z["model_sha"]), "s": dt}


def run_combo(root, ws, A, mode, scores=None, model_path=None):
    """mode 'pipeline' (need=True, real model) or 'inject' (identity model + rank injection)."""
    BD.clear_combo_outputs(ws, A); BL.clear_mini(f"{ws}/fea171")
    for f in os.listdir(f"{ws}/fea171"):
        if f.startswith("state_H_") and f.endswith(f"_{A}.npz"): os.remove(f"{ws}/fea171/{f}")
    if mode == "pipeline": shutil.copy2(model_path, f"{ws}/fea171/f10_live_s42_np.npz")
    else:
        BL.write_identity_model(f"{ws}/fea171/f10_live_s42_np.npz"); BL.write_f10_injection(f"{ws}/fea171", A, scores["pm"], scores["f10"])
    env = dict(BD.combo_env(ws, root)); env["_PY"] = BD.VENV_PY
    rc, lines, dt = BL.run_device(f"{HERE}/combo_stage_replay_3520d363.py", f"{ws}/fea171", env, f"{root}/combo_{mode}_{A}.log")
    tl = f"{ws}/state/target_live_combo/{A}.json"
    st = json.load(open(f"{ws}/state/combo_live_status.json")) if os.path.exists(f"{ws}/state/combo_live_status.json") else None
    tc = json.load(open(f"{ws}/state/target_combo/{A}.json")) if os.path.exists(f"{ws}/state/target_combo/{A}.json") else {}
    r = {"rc": rc, "s": dt, "status_ok": bool(st and st.get("ok")), "why": (st or {}).get("why"), "n_f10_scored": tc.get("n_f10_scored"),
         "ftrim_names_fc": sorted((tc.get("ftrim") or {}).get("names_fc", {}).keys())}
    if os.path.exists(tl):
        r["compare"] = BL.compare_targets_a2(f"{STAGE}/archive/target_live/{A}.json", tl, COL, "pipeline" if mode == "pipeline" else "inject",
                                             allow_missing_f10_sha_before=FP26_PATCH_UTC)
        wz = f"{ws}/state/weights_combo/{A}.npz"; arch = json.load(open(f"{STAGE}/archive/target_live/{A}.json"))
        r["weights_npz_sha_equal"] = os.path.exists(wz) and BL.sha(wz) == arch.get("weights_sha")
    else:
        r["compare"] = {"PARITY": False, "why": ["no replayed target_live_combo (combo abort)"], "max_abs_dw": None}
    r["PARITY"] = bool(r["compare"]["PARITY"] and r.get("weights_npz_sha_equal"))
    return r


def sel_mask(snap_dir, A, pm):
    """combo_stage L18–21 + REPLAY_TRUNCATE_CACHE + L38–42: qv4h over the last 2016 rows ending at A, sel = qv4h >= params.qv4h_min."""
    P = json.load(open(BD.SRC["bundle_config"][0]))["params"]
    R_ = np.load(f"{snap_dir}/rolling.npz", allow_pickle=True); rts = R_["ts"].astype(np.int64); RD = R_["data"]
    ai = int(np.searchsorted(rts, A, side="right")) - 1; assert rts[ai] <= A < rts[ai] + 300
    RD = RD[:ai + 1]; CDf = RD.astype(np.float32)
    qseg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 3]; finq = np.isfinite(qseg)
    qvm = np.where(finq, qseg, 0).sum(0) / np.maximum(finq.sum(0), 1)
    return np.expm1(np.clip(qvm[np.asarray(pm, np.int64)], 0, 30)) * 48 >= P["qv4h_min"]


def rebuild_producer_state(dev, cfg, snap_prev, snap_cur):
    """Phase-1 build_state_from_snapshot semantics (parity_replay_2026-09-12/devices/replay_driver.py L201–218), with the cache taken from the
    snapshot of A (rows <= A, already fetched by the producer at A) instead of the current state file."""
    st = dev.ShadowState.__new__(dev.ShadowState)
    st.syms = cfg["symbols_panel"]; st.live = cfg["symbols_live"]; st.NW = len(st.syms)
    st.sym_idx = {s: j for j, s in enumerate(st.syms)}
    st.live_mask = np.zeros(st.NW, bool); st.live_mask[[st.sym_idx[s] for s in st.live if s in st.sym_idx]] = True
    z = np.load(f"{snap_cur}/rolling.npz", allow_pickle=True); st.cts = z["ts"].astype(np.int64); st.cd = z["data"].astype(np.float16)
    aux = json.load(open(f"{snap_prev}/aux.json"))
    st.prev_close = {k: float(v) for k, v in aux["prev_close"].items()}
    st.H = np.zeros(st.NW)
    for k, v in aux["H"].items(): st.H[int(k)] = float(v)
    st.last_anchor = int(aux["last_anchor"]); st.ema = aux["ema"]; st.ledger = {s: [list(r) for r in rows] for s, rows in aux["ledger_tail"].items()}
    st.prev_rec = aux.get("prev_rec"); st.base = list(aux.get("base_syms") or st.live)
    lr = np.load(BD.SRC["bundle_leg_returns"][0]); extra = json.load(open(f"{snap_prev}/leg_returns_live.json"))
    st.LR = {leg: list(lr[leg]) + list(extra[leg]) for leg in ("king", "rev24", "fund")}
    return st


def king_compare(rh, A, snap_cur):
    a = np.load(f"{STAGE}/archive/weights/{A}.npz"); b = np.load(f"{rh}/state/weights/{A}.npz")
    same_idx = np.array_equal(a["idx"], b["idx"]); same_mem = np.array_equal(a["members"], b["members"])
    val_bitwise = same_idx and np.array_equal(a["val"], b["val"])
    mx = float(np.abs(a["val"].astype(np.float64) - b["val"].astype(np.float64)).max()) if same_idx else None
    return {"idx_equal": bool(same_idx), "members_equal": bool(same_mem), "val_bitwise": bool(val_bitwise), "max_abs_dval": mx,
            "PARITY": bool(same_idx and same_mem and val_bitwise)}


def gate_anchor(A):
    t0 = time.time(); root0 = f"/dev/shm/object_b_gate/{A}"; shutil.rmtree(root0, ignore_errors=True); os.makedirs(root0)
    fea_src, reader_src, man = BD.stage_sources()
    live_model = f"{STAGE}/model/f10_live_s42_np.npz"; assert BL.sha(live_model) == LIVE_F10_SHA
    snap = f"{STAGE}/snap/{A}"; snap_prev = f"{STAGE}/snap/{A - BL.H4}"
    res = {"anchor": A, "utc": BL.iso(A), "comparison_type": "(3) packaging/prediction parity — not a return", "tar_sha256": TAR_SHA}
    arch = json.load(open(f"{STAGE}/archive/target_live/{A}.json")); res["archived_written_utc"] = arch.get("written_utc")
    arch_tc = json.load(open(f"{STAGE}/archive/target_combo/{A}.json"))
    # ── F-1 ──
    r1 = f"{root0}/f1"; ws1 = BL.make_sandbox(r1, fea_src, BD.SRC["bundle_config"][0], BD.VENV_PY, reader_src); stage_state(ws1, A, snap)
    sc = run_scorer(r1, ws1, A, live_model); res["scorer"] = {"okf": sc["okf"], "n_pm": int(len(sc["pm"])), "model_sha": sc["model_sha"], "s": sc["s"], "child_maxrss_mb": child_maxrss_mb()}
    res["F1"] = run_combo(r1, ws1, A, "inject", scores=sc)
    res["F1"]["n_f10_scored_equal_archive"] = res["F1"].get("n_f10_scored") == arch_tc.get("n_f10_scored")
    # ── PC ──
    rp = f"{root0}/pc"; wsp = BL.make_sandbox(rp, fea_src, BD.SRC["bundle_config"][0], BD.VENV_PY, reader_src); stage_state(wsp, A, snap)
    res["PC"] = run_combo(rp, wsp, A, "pipeline", model_path=live_model); res["PC"]["child_maxrss_mb"] = child_maxrss_mb()
    # ── NC1: swap the top and bottom finite scores ──
    sw = dict(sc); f = sc["f10"].copy(); ok = np.where(np.isfinite(f))[0]; i_hi = ok[np.argmax(f[ok])]; i_lo = ok[np.argmin(f[ok])]
    f[i_hi], f[i_lo] = f[i_lo], f[i_hi]; sw["f10"] = f
    rn = f"{root0}/nc1"; wsn = BL.make_sandbox(rn, fea_src, BD.SRC["bundle_config"][0], BD.VENV_PY, reader_src); stage_state(wsn, A, snap)
    res["NC1"] = run_combo(rn, wsn, A, "inject", scores=sw); res["NC1"]["must_differ_ok"] = not res["NC1"]["PARITY"]
    res["NC1"]["status"] = "ORIGINAL NC1 — reported only, superseded in the verdict by AMENDMENT 3 (NC1′ + NC1r)"
    # ── AMENDMENT 3: NC1′ and NC1r among eligible members (inside sel, not FTRIM-zeroed in the baseline fc run, finite score) ──
    names = [COLN[int(j)] for j in sc["pm"]]; sel = sel_mask(snap, A, sc["pm"]); ftr = set(res["F1"]["ftrim_names_fc"])
    elig = np.array([i for i in range(len(names)) if sel[i] and names[i] not in ftr and np.isfinite(sc["f10"][i])], np.int64)
    res["NC_eligible"] = {"n_members": int(len(names)), "n_sel": int(sel.sum()), "n_ftrim_fc": len(ftr), "n_eligible": int(len(elig))}
    def swap_run(i, j, tag):
        f2 = sc["f10"].copy(); f2[i], f2[j] = f2[j], f2[i]
        r_ = run_combo(rn, wsn, A, "inject", scores={"pm": sc["pm"], "f10": f2})
        r_["swapped"] = [{"name": names[i], "f10": float(sc["f10"][i])}, {"name": names[j], "f10": float(sc["f10"][j])}]
        r_["must_differ_ok"] = not r_["PARITY"]; r_["tag"] = tag; return r_
    fe = sc["f10"][elig]; res["NC1p"] = swap_run(int(elig[np.argmax(fe)]), int(elig[np.argmin(fe)]), "NC1prime")
    rng = np.random.default_rng([20260919, A]); res["NC1r"] = []
    for k in range(3):
        i, j = (int(x) for x in rng.choice(elig, 2, replace=False)); res["NC1r"].append(swap_run(i, j, f"NC1r_{k}"))
    # ── F-2 + NC2 ──
    if os.path.isdir(snap_prev):
        rh = f"{root0}/king"; os.makedirs(f"{rh}/state/weights", exist_ok=True); os.makedirs(f"{rh}/state/target_live", exist_ok=True)
        dev = BD.import_producer(rh)
        cfg = copy.deepcopy(json.load(open(BD.SRC["bundle_config"][0]))); cfg["_booster_sha"] = BD.KING_LIVE_SHA
        aux_cur = json.load(open(f"{snap}/aux.json"))
        def one(booster):
            st = rebuild_producer_state(dev, cfg, snap_prev, snap)
            assert st.last_anchor == A - BL.H4, (st.last_anchor, A)
            fx = dev.ReplayFetcher(list(aux_cur["base_syms"]), {s: [[r[0], r[1]] for r in rows] for s, rows in aux_cur["ledger_tail"].items()})
            wrote, sig, skip = BD.producer_step(dev, st, fx, cfg, booster, A, rh)
            return st, wrote, sig
        st, wrote, sig = one(BL.FoldBooster("live", {"live": BD.KING_LIVE_FILE}))
        kc = king_compare(rh, A, snap)
        pr_a = aux_cur["prev_rec"]; pr_b = st.prev_rec
        pr_eq = {k: (pr_a.get(k) == pr_b.get(k)) for k in ("members", "legz", "sm", "sm_idx", "sel_idx", "base_n", "fund_base_n", "carry_bps", "cost_bps")}
        lr_eq = {leg: list(map(float, st.LR[leg][-950:])) == json.load(open(f"{snap}/leg_returns_live.json"))[leg] for leg in ("king", "rev24", "fund")}
        res["F2_king"] = {"wrote": wrote, "weights": kc, "prev_rec_equal": pr_eq, "LR_tail_equal": lr_eq, "w3": (sig or {}).get("w3"),
                          "PARITY": bool(kc["PARITY"] and all(pr_eq.values()) and all(lr_eq.values()))}
        # end to end: F-1 path on the rebuilt state
        r2 = f"{root0}/f2"; ws2 = BL.make_sandbox(r2, fea_src, BD.SRC["bundle_config"][0], BD.VENV_PY, reader_src)
        json.dump(BD.aux_doc(st), open(f"{ws2}/state/aux.json", "w"))
        json.dump({leg: list(map(float, st.LR[leg][-950:])) for leg in st.LR}, open(f"{ws2}/state/leg_returns_live.json", "w"))
        shutil.copy2(f"{snap}/rolling.npz", f"{ws2}/state/rolling.npz")
        Ap = A - BL.H4; shutil.copy2(f"{STAGE}/archive/weights/{Ap}.npz", f"{ws2}/state/weights/{Ap}.npz")
        shutil.copy2(f"{rh}/state/target_live/{A}.json", f"{ws2}/state/target_live/{A}.json"); shutil.copy2(f"{rh}/state/target_live/{A}.json.sha256", f"{ws2}/state/target_live/{A}.json.sha256")
        for leg in ("f10", "kc", "fc"): shutil.copy2(f"{STAGE}/archive/fea171/state_H_{leg}_{Ap}.npz", f"{ws2}/fea171/state_H_{leg}_{Ap}.npz")
        sc2 = run_scorer(r2, ws2, A, live_model)
        res["F2_scores_equal_F1"] = bool(np.array_equal(sc2["pm"], sc["pm"]) and np.array_equal(sc2["f10"], sc["f10"], equal_nan=True))
        res["F2"] = run_combo(r2, ws2, A, "inject", scores=sc2)
        # king file written by the rebuilt producer vs the archived king backup (weights/universe/booster; written_utc/offset excluded)
        res["F2_king_file"] = BL.compare_targets_a2(f"{STAGE}/archive/target_live_king/{A}.json", f"{rh}/state/target_live/{A}.json", COL, "kingfile")
        st2, wrote2, _ = one(BL.FoldBooster("live", {"live": f"{R}/models/king_v3_fold2025.txt"}))
        res["NC2"] = {"weights": king_compare(rh, A, snap)}; res["NC2"]["must_differ_ok"] = not res["NC2"]["weights"]["PARITY"]
    else:
        res["F2_king"] = res["F2"] = None; res["NC2"] = None; res["F2_skipped"] = "no snapshot for A−4h"
    res["t_s"] = round(time.time() - t0, 1); res["child_maxrss_mb"] = child_maxrss_mb()
    ok_f1 = bool(res["F1"]["PARITY"] and res["F1"]["n_f10_scored_equal_archive"])
    ok_f2 = True if res.get("F2_king") is None else bool(res["F2_king"]["PARITY"] and res["F2"]["PARITY"] and res["F2_king_file"]["PARITY"])
    res["F1_scorer_model_is_live"] = res["scorer"]["model_sha"] == LIVE_F10_SHA
    ok_f1 = bool(ok_f1 and res["F1_scorer_model_is_live"])
    ok_ctrl = bool(res["PC"]["PARITY"] and res["NC1p"]["must_differ_ok"] and all(r_["must_differ_ok"] for r_ in res["NC1r"])
                   and (res["NC2"] is None or res["NC2"]["must_differ_ok"]))   # AMENDMENT 3 A3.2; original NC1 reported only
    res["ANCHOR_PASS"] = bool(ok_f1 and ok_f2 and ok_ctrl); res["ok_f1"] = ok_f1; res["ok_f2"] = ok_f2; res["ok_controls"] = ok_ctrl
    os.makedirs(OUTD, exist_ok=True); json.dump(res, open(f"{OUTD}/GATE_F_{A}.json", "w"), indent=1, default=str)
    print(json.dumps({"anchor": BL.iso(A), "PASS": res["ANCHOR_PASS"], "NC1p": res["NC1p"]["must_differ_ok"], "NC1r": [x["must_differ_ok"] for x in res["NC1r"]],
                      "F1": res["F1"]["compare"].get("max_abs_dw"), "PC": res["PC"]["compare"].get("max_abs_dw"),
                      "F2_king": (res.get("F2_king") or {}).get("PARITY"), "F2": ((res.get("F2") or {}).get("compare") or {}).get("max_abs_dw"),
                      "NC1_ok": res["NC1"]["must_differ_ok"], "NC2_ok": (res["NC2"] or {}).get("must_differ_ok"), "t_s": res["t_s"]}), flush=True)
    shutil.rmtree(root0, ignore_errors=True)
    return res


def summarize():
    rows = []
    for f in sorted(os.listdir(OUTD)):
        if f.startswith("GATE_F_1") and f.endswith(".json"): rows.append(json.load(open(f"{OUTD}/{f}")))
    per = [{"anchor": r["anchor"], "utc": r["utc"], "in_tar_33910c01": r["anchor"] <= 1789768800, "PASS": r["ANCHOR_PASS"],
            "F1_max_abs_dw": r["F1"]["compare"].get("max_abs_dw"), "F1_n_names": r["F1"]["compare"].get("n_archived"),
            "F2_max_abs_dw": ((r.get("F2") or {}).get("compare") or {}).get("max_abs_dw"), "F2_king_weights_bitwise": ((r.get("F2_king") or {}).get("weights") or {}).get("val_bitwise"),
            "PC_max_abs_dw": r["PC"]["compare"].get("max_abs_dw"), "NC1_orig_differs_reported_only": r["NC1"]["must_differ_ok"],
            "NC1prime_differs": r["NC1p"]["must_differ_ok"], "NC1r_differs": [x["must_differ_ok"] for x in r["NC1r"]], "NC_eligible": r["NC_eligible"],
            "NC2_differs": (r.get("NC2") or {}).get("must_differ_ok"),
            "F1_literal_all_keys_equal": r["F1"]["compare"].get("literal_all_keys_equal"), "F1_literal_differing_keys": r["F1"]["compare"].get("literal_differing_keys"),
            "F1_gross_norm_rule": r["F1"]["compare"]["gross_norm"]["rule"], "PC_literal_all_keys_equal": r["PC"]["compare"].get("literal_all_keys_equal"),
            "F2_king_file_gross_norm_rule": ((r.get("F2_king_file") or {}).get("gross_norm") or {}).get("rule"),
            "scorer_model_is_live": r.get("F1_scorer_model_is_live"), "scorer_s": r["scorer"]["s"], "child_maxrss_mb": r.get("child_maxrss_mb")} for r in rows]
    verdict = "PASS" if rows and all(p["PASS"] for p in per) else "FAIL"
    n1p = sum(1 for p in per if p["NC1prime_differs"]); n1r = sum(sum(p["NC1r_differs"]) for p in per); n1r_all = sum(len(p["NC1r_differs"]) for p in per)
    h1 = f"{R}/receipts/gate_f/run1_NC1orig/GATE_F.json"
    history = [{"run": 1, "criteria": "PREREG §3 S5 + AMENDMENT 2 (original NC1)", "VERDICT": json.load(open(h1))["VERDICT"] if os.path.exists(h1) else None,
                "note": "original NC1 FAIL, 5/12 unchanged (09-17 20Z, 09-18 08Z, 09-18 12Z, 09-19 00Z, 09-19 04Z); explanation (swapped names' F10 scores discarded by sel / FTRIM) holds on 12/12; receipts kept verbatim in receipts/gate_f/run1_NC1orig/",
                "receipts_sha256": BL.sha(h1) if os.path.exists(h1) else None},
               {"run": 2, "criteria": "PREREG §3 S5 + AMENDMENT 2 + AMENDMENT 3 (NC1′ 12/12, NC1r 36/36; parity criterion unchanged)", "VERDICT": verdict,
                "NC1prime_changed": f"{n1p}/{len(per)}", "NC1r_changed": f"{n1r}/{n1r_all}",
                "NC1_orig_changed_reported_only": f"{sum(1 for p in per if p['NC1_orig_differs_reported_only'])}/{len(per)}"}]
    doc = {"gate": "GATE F (PREREG §3 S5, criteria per AMENDMENT 2 A2.1 and AMENDMENT 3 A3.2)", "comparison_type": "(3) packaging/prediction parity — not a return", "tar_sha256": TAR_SHA,
           "n_anchors_tested": len(per), "n_object_A_anchors": 144, "n_object_A_untestable_no_archived_inputs": 144 - sum(1 for p in per if p["in_tar_33910c01"]),
           "per_anchor": per, "VERDICT": verdict, "gate_history": history,
           "amendment_3_disclosure": "written after seeing which anchors failed run 1's NC1; makes the negative control stricter; does not touch the parity criterion (max|dw| = 0, weights_sha equal)", "utc": BL.iso(time.time()), "device_sha256": BL.sha(os.path.abspath(__file__)),
           "lib_sha256": BL.sha(f"{HERE}/b_lib.py"), "driver_sha256": BL.sha(f"{HERE}/b_driver.py")}
    json.dump(doc, open(f"{R}/receipts/GATE_F.json", "w"), indent=1)
    print(f"GATE_F VERDICT {verdict} anchors {len(per)}", flush=True)
    for p in per: print(json.dumps(p), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--anchor", type=int); ap.add_argument("--summarize", action="store_true"); a = ap.parse_args()
    if a.summarize: summarize()
    else: gate_anchor(a.anchor)
