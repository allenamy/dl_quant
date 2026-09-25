#!/usr/bin/env python3
"""F-2 for the files-only release (v2 + C on the NC book): can the CURRENT producer (the old tree, treeNC5 = production today) take over a
state that the NEW tree (treeNC7) has already advanced — i.e. is a rollback after one or more new anchors safe? Mac, production venv, heavy:
quiet window only (>= 15 min left). Never calls the exchange, never writes ~/wide_shadow or ~/dl_quant_live (sandboxes under <out>).
Input: the NC-format snapshot state/snap/<A0> (A1 = A0 + 4h and A2 = A0 + 8h must have COMPLETE snapshots: the fake fetcher replays them).
  (a)  NEW producer (treeNC7) runs A1 on a copy of snap/<A0>; (a2) NEW combo at A1: rc 0, status ok.
  (o)  OLD producer (treeNC5) runs A1 on an identical copy; (o2) OLD combo at A1: rc 0, status ok.
  (d)  the durable writes change HOW files are written, not WHAT: the state files and outputs the two trees wrote for A1 are compared
       byte for byte (rolling.npz, aux.json, leg_returns_live.json, boundary_raw.npz, members_hist.npz, generation.json, weights/<A1>.npz,
       target_live/<A1>.json minus written_utc, target_combo/<A1>.json, state_H_{kc,fc,f10}_<A1>.npz); any difference is listed by file
       (a difference is a RED only if it is not a wall-clock field — each is named).
  (b)  ROLLBACK: the OLD producer loads the state the NEW producer wrote at A1 (its own generation verification) and runs A2; (b2) the OLD
       combo at A2: rc 0, status ok. This is the rollback path after a new anchor.
  (f)  FORWARD after rollback: the NEW producer loads the state the OLD producer wrote at A2 — the two trees can alternate either way.
VERDICT: PASS iff (a) (a2) (o) (o2) (b) (b2) (f) are green and (d) has no non-wall-clock difference.
usage: ~/wide_shadow/venv/bin/python test_c_rollback_rehearsal.py <old tree> <new tree> <A0> <out dir>
output: <out>/TEST_C_ROLLBACK_REHEARSAL.json"""
import json, os, shutil, sys, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nc_sandbox_lib as L

STATE_FILES = ["rolling.npz", "aux.json", "leg_returns_live.json", "boundary_raw.npz", "members_hist.npz", "generation.json"]


def exc_str(e): return f"{type(e).__name__}: {str(e)[:300]}"


def producer(ws, A, aux, tag, cols):
    try:
        r = L.run_producer(ws, A, L.NCFake(aux), True, tag, cols); d = r["diag"] or {}
        M = L.load_producer(ws, f"{tag}_reload"); st2 = M.ShadowState(M.load_bundle()[0])
        return {"ok": d.get("outcome") == "returned" and r["target_live_written"] and st2.last_anchor == A, "outcome": d.get("outcome"),
                "target_live_written": r["target_live_written"], "reloaded_last_anchor": st2.last_anchor, "wall_s": r["wall_s"], "phase_s": d.get("phase_s")}
    except Exception as e:
        return {"ok": False, "error": exc_str(e), "tb": traceback.format_exc()[-1200:], "diag": L.last_diag(ws, A)}


def combo(root, ws, exe, tag):
    c = L.run_combo(root, ws, exe, tag)
    return {"ok": c["rc"] == 0 and c["ok"], **c}


def main():
    old_t, new_t, A0, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), int(sys.argv[3]), os.path.abspath(sys.argv[4])
    q = L.quiet_window_guard(15)
    assert not os.path.exists(out), "refusing to overwrite"; os.makedirs(out)
    A1, A2 = A0 + 14400, A0 + 28800
    for A in (A0, A1, A2):
        assert os.path.exists(f"{L.WS}/state/snap/{A}/COMPLETE"), f"snap/{A} missing or incomplete"
    rec = {"device": os.path.abspath(__file__), "device_sha256": L.sha(os.path.abspath(__file__)), "lib_sha256": L.sha(L.__file__),
           "old_tree": old_t, "new_tree": new_t, "old_shadow_loop": L.sha(f"{old_t}/shadow_loop_v3.py"), "new_shadow_loop": L.sha(f"{new_t}/shadow_loop_v3.py"),
           "anchors": {"A0": A0, "A1": A1, "A2": A2}, "quiet_window_at_start": q, "started_utc": time.strftime("%FT%TZ", time.gmtime()), "checks": {}}
    C = rec["checks"]
    def dump():
        with open(f"{out}/TEST_C_ROLLBACK_REHEARSAL.json", "w") as fh:
            json.dump(rec, fh, indent=1, default=str)
    cfg = json.load(open(f"{L.WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; sidx = {s: j for j, s in enumerate(syms)}
    crypto = L.crypto_axis_json(syms)["crypto"]
    aux1 = json.load(open(f"{L.WS}/state/snap/{A1}/aux.json")); aux2 = json.load(open(f"{L.WS}/state/snap/{A2}/aux.json"))
    cols1 = [sidx[s] for s in aux1["base_syms"] if s in sidx and crypto[sidx[s]]]
    cols2 = [sidx[s] for s in aux2["base_syms"] if s in sidx and crypto[sidx[s]]]
    snap0 = f"{L.WS}/state/snap/{A0}"
    sides = {}
    for tag, tree in (("new", new_t), ("old", old_t)):
        root = f"{out}/sb_{tag}"; ws, exe = L.build_sandbox(root, "new", tree)
        L.copy_state(snap0, f"{ws}/state")
        for junk in ("COMPLETE", "SHA256SUMS", "PARITY.json", "PARITY.run.log", "PARITY_v2.json", "PARITY_v2.run.log", "combo_live_status.json"):
            if os.path.exists(f"{ws}/state/{junk}"): os.remove(f"{ws}/state/{junk}")
        rec[f"carry_prior_{tag}"] = L.carry_prior(ws, A0)
        C[f"{tag}_producer_A1"] = producer(ws, A1, aux1, f"{tag}_a1", cols1)
        C[f"{tag}_combo_A1"] = combo(root, ws, exe, f"{tag}_a1") if C[f"{tag}_producer_A1"]["ok"] else {"ok": False, "skipped": "producer failed"}
        sides[tag] = (root, ws, exe); dump()
    # (d) byte comparison of what the two trees wrote for A1
    wsn, wso = sides["new"][1], sides["old"][1]
    pairs = [(f"state/{f}", f"state/{f}") for f in STATE_FILES] + [(f"state/weights/{A1}.npz",) * 2, (f"state/target_combo/{A1}.json",) * 2] + \
            [(f"fea171/state_H_{t}_{A1}.npz",) * 2 for t in ("kc", "fc", "f10")]
    diffs = {}
    for a, b in pairs:
        pa, pb = f"{wsn}/{a}", f"{wso}/{b}"
        if not (os.path.exists(pa) and os.path.exists(pb)):
            diffs[a] = f"missing new={os.path.exists(pa)} old={os.path.exists(pb)}"; continue
        if L.sha(pa) != L.sha(pb):
            if a.endswith(".json"):
                ja, jb = json.load(open(pa)), json.load(open(pb))
                keys = sorted(k for k in set(ja) | set(jb) if ja.get(k) != jb.get(k)) if isinstance(ja, dict) and isinstance(jb, dict) else ["<non-dict>"]
                diffs[a] = {"differing_keys": keys}
            else:
                diffs[a] = "bytes differ"
    tl_n, tl_o = json.load(open(f"{wsn}/state/target_live/{A1}.json")), json.load(open(f"{wso}/state/target_live/{A1}.json"))
    tl_keys = sorted(k for k in set(tl_n) | set(tl_o) if k != "written_utc" and tl_n.get(k) != tl_o.get(k))
    WALL = {"written_utc", "created_utc", "utc", "t_wall", "wall_s", "generated_utc", "signed_utc"}
    nonwall = {k: v for k, v in diffs.items() if not (isinstance(v, dict) and set(v["differing_keys"]) <= WALL)}
    C["d_same_bytes"] = {"ok": not nonwall and not tl_keys, "diffs": diffs, "non_wallclock_diffs": nonwall, "target_live_keys_differing_ex_written_utc": tl_keys}
    dump()
    # (b) rollback: OLD code takes over the state the NEW code wrote at A1
    root_b = f"{out}/sb_rollback"; shutil.copytree(sides["new"][0], root_b, symlinks=True)
    ws_b, exe_b = f"{root_b}/wide_shadow", f"{root_b}/dl_quant_live"
    for f in ["shadow_loop_v3.py"]:
        shutil.copy2(f"{old_t}/{f}", f"{ws_b}/{f}")
    for f in os.listdir(f"{old_t}/fea171"):
        if os.path.isfile(f"{old_t}/fea171/{f}"): shutil.copy2(f"{old_t}/fea171/{f}", f"{ws_b}/fea171/{f}")
    if os.path.exists(f"{ws_b}/fea171/durable_io.py") and not os.path.exists(f"{old_t}/fea171/durable_io.py"):
        os.remove(f"{ws_b}/fea171/durable_io.py")                   # the rollback removes the new-only file, as nc_install_files does
    C["b_old_producer_A2_on_new_state"] = producer(ws_b, A2, aux2, "b_a2", cols2)
    C["b_old_combo_A2"] = combo(root_b, ws_b, exe_b, "b_a2") if C["b_old_producer_A2_on_new_state"]["ok"] else {"ok": False, "skipped": "producer failed"}
    dump()
    # (f) forward again: NEW code loads the state the OLD code wrote at A2
    try:
        root_f = f"{out}/sb_forward"; shutil.copytree(root_b, root_f, symlinks=True); ws_f = f"{root_f}/wide_shadow"
        shutil.copy2(f"{new_t}/shadow_loop_v3.py", f"{ws_f}/shadow_loop_v3.py")
        for f in os.listdir(f"{new_t}/fea171"):
            if os.path.isfile(f"{new_t}/fea171/{f}"): shutil.copy2(f"{new_t}/fea171/{f}", f"{ws_f}/fea171/{f}")
        M = L.load_producer(ws_f, "f_reload"); st = M.ShadowState(M.load_bundle()[0])
        C["f_new_loads_old_state_A2"] = {"ok": st.last_anchor == A2, "last_anchor": st.last_anchor}
    except Exception as e:
        C["f_new_loads_old_state_A2"] = {"ok": False, "error": exc_str(e)}
    rec["VERDICT"] = "PASS" if all(v.get("ok") for v in C.values()) else "FAIL"
    rec["ended_utc"] = time.strftime("%FT%TZ", time.gmtime()); dump()
    print("C_ROLLBACK", rec["VERDICT"], json.dumps({k: v.get("ok") for k, v in C.items()}), flush=True)
    if rec["VERDICT"] == "PASS":
        for d in ("sb_new", "sb_old", "sb_rollback", "sb_forward"): shutil.rmtree(f"{out}/{d}", ignore_errors=True)
    return 0 if rec["VERDICT"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
