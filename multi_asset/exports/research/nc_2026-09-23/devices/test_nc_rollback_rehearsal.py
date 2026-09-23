#!/usr/bin/env python3
"""F-2 rollback rehearsal on a copy (DESIGN §F-2 option (ii); FREEZE b30e4afa5 + amendment 1). Mac, production venv, heavy: runs only
inside the Mac window [N+1:00, N+3:40]. Never calls the exchange, never writes ~/wide_shadow or ~/dl_quant_live (sandboxes under <out>).
Chain (A0 = the NC state's last anchor, A1 = A0+4h, A2 = A0+8h; archived snapshots state/snap/<A1>, <A2> required):
  (a)  NEW producer (the NC tree) runs A1 on a copy of the NC state — fake fetcher: exchangeInfo = snap/<A1> base_syms, funding (per name
       and bulk) = snap/<A1> ledger rows, bars pre-filled from snap/<A1>/rolling.npz (dynamic fetch columns only, no-cross-gap ch0);
       green = anchor_diagnostics outcome "returned" + target_live/<A1>.json + the NEW loader re-verifies the written generation at A1.
  (a2) NEW combo_stage at A1 under sandbox-exec: rc 0 and combo_live_status ok (a healthy NC anchor to roll back from).
  (a3) NO SIDECAR (com.hsy.sidecar is booted out at deploy): on a COPY of the post-(a2) sandbox, the NEW producer runs A2 and the NEW
       combo_stage runs A2; green = state_H_f10_<A1>.npz sha right after (a2) == sha right before the A2 run == sha after it (no other
       writer), its anchor field == A1, combo's own fields h_source (target_blend) / kc_state_source / fc_state_source (target_combo)
       all "own" and the log line ④ kc_src / fc_src agree, rc 0, status ok, state_H_f10_<A2>.npz written.
  (b)  nc_downgrade_state.py (subprocess, as the operator runs it) on the NC state after A1: rc 0; output has no None EMA field, no None
       interval, no NC aux key, exactly the OLD STATE_FILES + generation.json.
  (c)  OLD producer (6080073b) loads the downgraded state (its own generation verification) and runs A2 (fake as in (a), bars for every
       archived column, old ingestion): green = outcome returned + target_live/<A2>.json written.
  (d)  OLD combo_stage (fb5a9407) at A2 under sandbox-exec: rc 0 and status ok.
  (e)  negative controls, counted ONLY when the baseline (a)-(d) is green:
       e1 OLD ShadowState on the UNCONVERTED NC state must refuse (ValueError "invalid generation schema");
       e2 downgraded state with one EMA entry forced to acc None (generation re-signed, so only the None can be what fails) must fail
          somewhere in (old producer raises | no target_live | old combo rc != 0 | status not ok) — the catching layer is recorded;
       e3 downgraded state with one base name's last ledger interval put back to None (re-signed) must fail likewise.
Modes: --nc-state DIR (a seeded NC state, e.g. nc_seed_state.py output/state) | --synthetic-seed A0 (MACHINERY DRY RUN: an NC-layout state
from snap/<A0> without the seed pack; the verdict is prefixed MACHINERY_DRY_RUN_ and is never a deployment receipt).
--harness-phase-fix: run on a copy of the tree with the missing _AnchorTiming key added (verdict suffixed _WITH_HARNESS_PATCH).
usage: ~/wide_shadow/venv/bin/python test_nc_rollback_rehearsal.py <NC tree> <out dir> (--nc-state DIR | --synthetic-seed A0) [--harness-phase-fix] [--keep]
output: <out>/TEST_NC_ROLLBACK_REHEARSAL.json"""
import os, sys, re, json, time, shutil, argparse, subprocess, traceback
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nc_sandbox_lib as L


def exc_str(e):
    return f"{type(e).__name__}: {str(e)[:300]}"


def old_resign(ws):
    M = L.load_producer(ws, "resign")
    aux = json.load(open(f"{ws}/state/aux.json"))
    M.atomic_json(f"{ws}/state/generation.json", M.build_generation_record(f"{ws}/state", int(aux["last_anchor"])))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("tree"); ap.add_argument("out")
    g = ap.add_mutually_exclusive_group(required=True); g.add_argument("--nc-state"); g.add_argument("--synthetic-seed", type=int)
    ap.add_argument("--harness-phase-fix", action="store_true")
    ap.add_argument("--keep", action="store_true", help="keep every sandbox (paths in the receipt); default: removed after a PASS, kept otherwise")
    a = ap.parse_args()
    q = L.quiet_window_guard(15)          # measured: the whole rehearsal takes ~3 min on the Mac
    out = os.path.abspath(a.out); assert not os.path.exists(out), "refusing to overwrite"; os.makedirs(out)
    rec = {"device": os.path.abspath(__file__), "device_sha256": L.sha(os.path.abspath(__file__)), "lib_sha256": L.sha(L.__file__),
           "converter_sha256": L.sha(f"{HERE}/nc_downgrade_state.py"), "tree": os.path.abspath(a.tree),
           "tree_shadow_loop_sha256": L.sha(f"{a.tree}/shadow_loop_v3.py"), "old_producer_sha256": L.sha(L.OLD_PRODUCER),
           "quiet_window_at_start": q, "started_utc": time.strftime("%FT%TZ", time.gmtime()), "checks": {}, "negative_controls": {}}
    C = rec["checks"]; NEG = rec["negative_controls"]

    def dump():
        json.dump(rec, open(f"{out}/TEST_NC_ROLLBACK_REHEARSAL.json", "w"), indent=1, default=str)

    tree = os.path.abspath(a.tree)
    rec["tree_phase_key_check"] = L.phase_key_check(tree)
    if rec["tree_phase_key_check"]["missing"]:
        if not a.harness_phase_fix:
            rec["VERDICT"] = "FAIL_TREE_DEFECT"; rec["why"] = f"diag.phase names not in _AnchorTiming.phase_s: {rec['tree_phase_key_check']['missing']} => KeyError on every anchor"
            dump(); print("NC_ROLLBACK", rec["VERDICT"], rec["why"], flush=True); sys.exit(1)
        rec["harness_phase_fix"] = L.harness_phase_fix(tree, f"{out}/tree_harness"); tree = f"{out}/tree_harness"
    # ---- the NC input state
    if a.synthetic_seed:
        rec["input"] = L.synthetic_nc_state(tree, a.synthetic_seed, f"{out}/nc_input/state"); nc_in = f"{out}/nc_input/state"
    else:
        nc_in = os.path.abspath(a.nc_state); rec["input"] = {"synthetic": False, "nc_state": nc_in, "files": {f: L.sha(f"{nc_in}/{f}") for f in sorted(os.listdir(nc_in)) if os.path.isfile(f"{nc_in}/{f}")}}
    A0 = int(json.load(open(f"{nc_in}/aux.json"))["last_anchor"]); A1, A2 = A0 + 14400, A0 + 28800
    for A in (A1, A2):
        assert os.path.exists(f"{L.WS}/state/snap/{A}/COMPLETE"), f"snap/{A} missing or incomplete"
    rec["anchors"] = {"A0": A0, "A1": A1, "A2": A2}
    cfg = json.load(open(f"{L.WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; sidx = {s: j for j, s in enumerate(syms)}
    crypto = L.crypto_axis_json(syms)["crypto"]
    aux1 = json.load(open(f"{L.WS}/state/snap/{A1}/aux.json")); aux2 = json.load(open(f"{L.WS}/state/snap/{A2}/aux.json"))
    cols1 = [sidx[s] for s in aux1["base_syms"] if s in sidx and crypto[sidx[s]]]
    # ---- (a) new producer at A1
    ws_n, exe_n = L.build_sandbox(f"{out}/sb_new", "new", tree)
    L.copy_state(nc_in, f"{ws_n}/state"); rec["carry_prior_A0"] = L.carry_prior(ws_n, A0)
    try:
        r = L.run_producer(ws_n, A1, L.NCFake(aux1), True, "a", cols1)
        d = r["diag"] or {}
        M = L.load_producer(ws_n, "a_reload"); st2 = M.ShadowState(M.load_bundle()[0])
        C["a_new_producer_A1"] = {"ok": d.get("outcome") == "returned" and r["target_live_written"] and st2.last_anchor == A1,
                                  "outcome": d.get("outcome"), "error_type": d.get("error_type"), "target_live_written": r["target_live_written"],
                                  "reloaded_last_anchor": st2.last_anchor, "wall_s": r["wall_s"], "prefill_rows": r["prefill_rows"], "phase_s": d.get("phase_s"),
                                  "fake_calls": d.get("fetcher", {}).get("calls")}
    except Exception as e:
        C["a_new_producer_A1"] = {"ok": False, "error": exc_str(e), "tb": traceback.format_exc()[-1500:], "diag": L.last_diag(ws_n, A1)}
    if C["a_new_producer_A1"]["ok"]:
        c = L.run_combo(f"{out}/sb_new", ws_n, exe_n, "a2")
        C["a2_new_combo_A1"] = {"ok": c["rc"] == 0 and c["ok"], **c}
    dump()
    if not all(C[k]["ok"] for k in C):
        rec["VERDICT"] = "FAIL_BASELINE_NEW_SIDE"; dump(); print("NC_ROLLBACK", rec["VERDICT"], flush=True); sys.exit(1)
    rec["sandboxes"] = {"a_a2_new_side_post_a2": f"{out}/sb_new"}
    # ---- (a3) no sidecar: the F10 chain advances one anchor on combo's OWN state_H_f10 (lead 2026-09-23; own copy, (b) unaffected)
    f10_a1 = f"{ws_n}/fea171/state_H_f10_{A1}.npz"
    A3 = {"sha_after_a2": L.sha(f10_a1) if os.path.exists(f10_a1) else None}
    root3 = f"{out}/sb_a3"; shutil.copytree(f"{out}/sb_new", root3, symlinks=True); rec["sandboxes"]["a3_post_A2"] = root3
    ws3, exe3 = f"{root3}/wide_shadow", f"{root3}/dl_quant_live"; f3 = f"{ws3}/fea171/state_H_f10_{A1}.npz"
    A3["sha_before_a2run"] = L.sha(f3) if os.path.exists(f3) else None
    A3["A1_file_anchor_field"] = int(np.load(f3)["anchor"]) if os.path.exists(f3) else None
    cols2 = [sidx[s] for s in aux2["base_syms"] if s in sidx and crypto[sidx[s]]]
    try:
        r = L.run_producer(ws3, A2, L.NCFake(aux2), True, "a3", cols2); d = r["diag"] or {}
        A3.update(producer_outcome=d.get("outcome"), producer_error_type=d.get("error_type"), target_live_written=r["target_live_written"])
    except Exception as e:
        A3.update(producer_outcome="raised", producer_error=exc_str(e), tb=traceback.format_exc()[-1200:], target_live_written=False)
    if A3["producer_outcome"] == "returned" and A3["target_live_written"]:
        c = L.run_combo(root3, ws3, exe3, "a3")
        A3.update(rc=c["rc"], status={"ok": c["ok"], "step": c["status_step"], "why": c["status_why"]}, combo_wall_s=c["wall_s"], combo_log=c["log"])
        tb_ = f"{ws3}/state/target_blend/{A2}.json"; tc_ = f"{ws3}/state/target_combo/{A2}.json"
        A3["h_f10_source"] = json.load(open(tb_)).get("h_source") if os.path.exists(tb_) else None
        tcj = json.load(open(tc_)) if os.path.exists(tc_) else {}
        A3["kc_src"] = tcj.get("kc_state_source"); A3["fc_src"] = tcj.get("fc_state_source")
        l4 = [l for l in open(c["log"]) if "④" in l]
        m4 = re.search(r"kc_src=(\S+) fc_src=(\S+)", l4[-1]) if l4 else None
        A3["log4_line"] = l4[-1].strip() if l4 else None
        A3["log4_kc_src"], A3["log4_fc_src"] = (m4.group(1), m4.group(2)) if m4 else (None, None)
        A3["f10_A2_written"] = os.path.exists(f"{ws3}/fea171/state_H_f10_{A2}.npz")
        A3["sha_A1_after_a2run"] = L.sha(f3)
    A3["criterion_source"] = ("combo_stage's own fields: target_blend/<A2>.json h_source (H_f10_prev: 'own' only when "
                              "fea171/state_H_f10_<A2-4h>.npz exists AND its anchor field == A2-4h = A1) and target_combo/<A2>.json "
                              "kc_state_source / fc_state_source; the log line ④ kc_src / fc_src must agree")
    A3["ok"] = bool(A3["sha_after_a2"] and A3["sha_after_a2"] == A3["sha_before_a2run"] == A3.get("sha_A1_after_a2run")
                    and A3["A1_file_anchor_field"] == A1 and A3.get("h_f10_source") == "own"
                    and A3.get("kc_src") == "own" and A3.get("fc_src") == "own"
                    and (A3.get("log4_kc_src"), A3.get("log4_fc_src")) == ("own", "own")
                    and A3.get("rc") == 0 and (A3.get("status") or {}).get("ok") and A3.get("f10_A2_written"))
    rec["a3_f10_chain_without_sidecar"] = A3; dump()
    # ---- (b) downgrade (subprocess, as the operator runs it)
    dg = f"{out}/downgraded"
    p = subprocess.run([f"{L.WS}/venv/bin/python", f"{HERE}/nc_downgrade_state.py", f"{ws_n}/state", dg], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "HOME": L.HOME, "PYTHONDONTWRITEBYTECODE": "1"})
    line = [l for l in p.stdout.splitlines() if l.startswith("NC_DOWNGRADE_OK")]
    bchk = {"rc": p.returncode, "line": line[0] if line else None, "stderr_tail": p.stderr[-600:]}
    if p.returncode == 0:
        auxd = json.load(open(f"{dg}/state/aux.json"))
        bchk["ema_none"] = sum(1 for e in auxd["ema"].values() if e.get("acc") is None or e.get("last_ts") is None)
        bchk["iv_none"] = sum(1 for rows in auxd["ledger_tail"].values() for x in rows if len(x) < 3 or x[2] is None)
        bchk["nc_keys_left"] = [k for k in ("fetch_syms", "prev_close_ts", "nc_backfill_residual") if k in auxd]
        bchk["files"] = sorted(os.listdir(f"{dg}/state"))
        bchk["receipt_counts"] = json.load(open(f"{dg}/DOWNGRADE_RECEIPT.json"))["counts"]
        bchk["ok"] = (bchk["ema_none"] == 0 and bchk["iv_none"] == 0 and not bchk["nc_keys_left"]
                      and bchk["files"] == ["aux.json", "generation.json", "leg_returns_live.json", "rolling.npz"] and bool(line))
    else:
        bchk["ok"] = False
    C["b_downgrade"] = bchk; dump()
    if not bchk["ok"]:
        rec["VERDICT"] = "FAIL_DOWNGRADE"; dump(); print("NC_ROLLBACK", rec["VERDICT"], flush=True); sys.exit(1)

    def old_run(tag, mutate=None):
        """old sandbox from the downgraded state (+ the NC chain's A1 weights / combo H files), optional mutation (re-signed), A2."""
        root = f"{out}/sb_old_{tag}"; ws, exe = L.build_sandbox(root, "old")
        for f in os.listdir(f"{dg}/state"): shutil.copy2(f"{dg}/state/{f}", f"{ws}/state/{f}")
        carried = L.carry_prior(ws, A1, src_ws=ws_n)
        mut = None
        if mutate:
            aux = json.load(open(f"{ws}/state/aux.json")); mut = mutate(aux); json.dump(aux, open(f"{ws}/state/aux.json", "w")); old_resign(ws)
        res = {"carried_from_nc_chain": carried, "mutation": mut}
        try:
            r = L.run_producer(ws, A2, L.NCFake(aux2), False, f"old_{tag}")
            d = r["diag"] or {}
            res.update(producer_outcome=d.get("outcome"), producer_error_type=d.get("error_type"), target_live_written=r["target_live_written"],
                       wall_s=r["wall_s"], phase_s=d.get("phase_s"))
        except Exception as e:
            res.update(producer_outcome="raised_before_or_in_run_anchor", producer_error=exc_str(e), tb=traceback.format_exc()[-1200:],
                       target_live_written=os.path.exists(f"{ws}/state/target_live/{A2}.json"), diag=L.last_diag(ws, A2))
        if res.get("producer_outcome") == "returned" and res["target_live_written"]:
            res["combo"] = L.run_combo(root, ws, exe, tag)
        return res

    # ---- (c) + (d)
    r = old_run("base")
    C["c_old_producer_A2"] = {"ok": r.get("producer_outcome") == "returned" and r["target_live_written"],
                              **{k: v for k, v in r.items() if k != "combo"}}
    if "combo" in r:
        C["d_old_combo_A2"] = {"ok": r["combo"]["rc"] == 0 and r["combo"]["ok"], **r["combo"]}
    else:
        C["d_old_combo_A2"] = {"ok": False, "why": "not run: (c) red"}
    dump()
    baseline = all(C[k]["ok"] for k in C)
    rec["baseline_green"] = baseline
    if not baseline:
        rec["VERDICT"] = "FAIL_BASELINE_OLD_SIDE"; NEG["counted"] = False; dump(); print("NC_ROLLBACK", rec["VERDICT"], flush=True); sys.exit(1)
    NEG["counted"] = True
    # ---- e1: old loader on the unconverted NC state
    ws1, _ = L.build_sandbox(f"{out}/sb_neg_e1", "old")
    L.copy_state(f"{ws_n}/state", f"{ws1}/state")
    try:
        M = L.load_producer(ws1, "e1"); M.ShadowState(M.load_bundle()[0])
        NEG["e1_old_loader_on_nc_state"] = {"refused": False, "detected": False}
    except Exception as e:
        NEG["e1_old_loader_on_nc_state"] = {"refused": True, "error": exc_str(e), "detected": isinstance(e, ValueError) and "invalid generation schema" in str(e)}
    dump()
    # ---- e2: one EMA acc None
    live = set(cfg["symbols_live"]); b2 = set(aux2["base_syms"])

    def pick(aux):
        c = [s for s in sorted(aux["ema"]) if s in live and s in b2 and aux["ledger_tail"].get(s)]
        return c[len(c) // 2]

    def m_e2(aux):
        s = pick(aux); aux["ema"][s] = {"acc": None, "last_ts": aux["ema"][s]["last_ts"]}; return {"ema_acc_none": s}

    def m_e3(aux):
        s = pick(aux); aux["ledger_tail"][s][-1] = [aux["ledger_tail"][s][-1][0], aux["ledger_tail"][s][-1][1], None]; return {"ledger_last_iv_none": s}

    for tag, fn in (("e2_ema_acc_none", m_e2), ("e3_ledger_iv_none", m_e3)):
        r = old_run(tag, fn)
        layer = None
        if r.get("producer_outcome") != "returned": layer = f"old producer raised ({r.get('producer_error_type') or r.get('producer_error')})"
        elif not r["target_live_written"]: layer = "old producer wrote no target_live"
        elif r["combo"]["rc"] != 0: layer = f"old combo rc {r['combo']['rc']}"
        elif not r["combo"]["ok"]: layer = f"old combo status not ok ({r['combo'].get('status_step')})"
        NEG[tag] = {"detected": layer is not None, "caught_by": layer, **{k: v for k, v in r.items() if k not in ("tb",)}}
        dump()
    ok_neg = all(NEG[k]["detected"] for k in ("e1_old_loader_on_nc_state", "e2_ema_acc_none", "e3_ledger_iv_none"))
    v = ("PASS" if ok_neg else "FAIL_NEGATIVE_CONTROL_NOT_DETECTED") if A3["ok"] else ("FAIL_A3_F10_CHAIN" + ("" if ok_neg else "_AND_NEGATIVE_CONTROL"))
    if a.synthetic_seed: v = "MACHINERY_DRY_RUN_" + v
    if a.harness_phase_fix: v += "_WITH_HARNESS_PATCH"
    rec["VERDICT"] = v; rec["finished_utc"] = time.strftime("%FT%TZ", time.gmtime())
    rec["sandboxes"].update({"old_side_" + k[len("sb_old_"):]: f"{out}/{k}" for k in sorted(os.listdir(out)) if k.startswith("sb_old_")})
    rec["sandboxes_kept"] = bool(a.keep or not v.replace("MACHINERY_DRY_RUN_", "").startswith("PASS"))
    if not rec["sandboxes_kept"]:
        for k in sorted(os.listdir(out)):
            if k.startswith("sb_") or k in ("nc_input", "downgraded"): shutil.rmtree(f"{out}/{k}", ignore_errors=True)
    dump()
    print("NC_ROLLBACK", v, json.dumps({k: C[k]["ok"] for k in C}), "a3", A3["ok"], json.dumps({k: NEG[k]["detected"] for k in NEG if k != "counted"}), flush=True)
    sys.exit(0 if v.replace("MACHINERY_DRY_RUN_", "").startswith("PASS") else 1)


if __name__ == "__main__":
    main()
