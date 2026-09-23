#!/usr/bin/env python3
"""Rehearsal of the deploy paths that had never been executed (DEPLOY_new_servable_models_2026-09-23.md §P3): news_backfill.py install and
rollback, news_prod_files.py fetchlist and models, and the §R-A / §R-B restores — on a COPY of the producer (WIDE_SHADOW_HOME=<sandbox>),
with the producer's own loader deciding whether each resulting state is acceptable. Mac, production venv, quiet window. No exchange call
(the fetch step is EMULATED: the added columns come from the x0918r research cache with hole cells NaN, i.e. what an accepted fetch
writes for rows <= 2026-09-19; prev_close of the added names = a placeholder, stated). Never writes ~/wide_shadow.
Steps and checks (each recorded; exit 0 only if all pass):
  S0 sandbox from state/snap/<A0> (09-17T16Z) + original producer 6080073b + bundle + F10 file; generation signed by the producer's own
     build_generation_record; ShadowState loads.
  S1 emulated fetch ⇒ <out>/A2/isolated_state (+ SOURCE.json = sandbox generation sha).
  S2 install (subprocess, the deploy command): rc 0; added columns == isolated copy bitwise; the other 757 columns byte-identical;
     prev_close set for every added name; ShadowState loads the re-signed generation.
  S3 negative control: install a second time ⇒ must REFUSE (production state advanced since the fetch), rc != 0.
  S4 patch + fetchlist (subprocess, the deploy command): patched producer ed11d731; config symbols_fetch = 450 + 72, symbols_live unchanged;
     load_bundle accepts the new MANIFEST.
  S5 one anchor A1 = A0 + 4h with the patched producer (fake fetcher: funding rows from state/snap/<A1>/aux.json; bars from the snapshot +
     the installed added columns): members == the evaluation's training members at A1 (NEWS_ACCEPT_ROWS m_<A1>); no added name holds weight;
     target universe == the 450; the state it saves re-loads.
  S6 models (subprocess, the deploy command) with the candidate package: printed pins == manifest executor_pins; load_bundle accepts;
     slow2026.txt / f10 file bytes == package.
  S7 §R-B restore: models + MANIFEST back from the backup ⇒ shas == in-service (8d79186b / 351ae26b); load_bundle accepts.
  S8 §R-A restore: producer file + config + MANIFEST back from the backup, then news_backfill.py rollback (subprocess): added columns all
     NaN, their prev_close gone, other columns unchanged since S5; the ORIGINAL producer's ShadowState loads the result.
usage: ~/wide_shadow/venv/bin/python test_backfill_install_rehearsal.py <PKG dir> <out dir>"""
import os, sys, json, shutil, hashlib, subprocess, importlib.util
import numpy as np

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; P = f"{HOME}/cc_tmp/news_20260923"
ORIG = f"{P}/producer_copy/shadow_loop_v3.py"; ORIG_SHA = "6080073964bffc621c893915b16f71ecafe093194f0b99a66a4463ee12c74e61"
PATCH = f"{P}/deploy/producer_patch/shadow_loop_v3.py"; PATCH_SHA = "ed11d731ffc13ef1333c3fabe044bc209485ba237fd9b8ae11aeccb014be1ec9"
A0 = 1789660800; A1 = A0 + 14400
sys.path.insert(0, f"{P}/deploy")
from test_fetchlist_split import FakeFetcher


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def module(root, src):
    os.environ["WIDE_SHADOW_HOME"] = root; os.environ["WIDE_SHADOW_BUNDLE"] = f"{root}/shadow_bundle"; os.environ["SHADOW_OFFSET_MIN"] = "12"
    spec = importlib.util.spec_from_file_location(f"sl_{abs(hash((root, src, np.random.rand())))}", src); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    return M


def loads(root, src):
    try:
        M = module(root, src); cfg, booster, man = M.load_bundle(); st = M.ShadowState(cfg)
        return True, int(st.last_anchor), None
    except BaseException as e:            # SystemExit included: the producer refuses by exiting
        return False, None, f"{type(e).__name__}: {e}"


def run(cmd, root, extra=None):
    env = dict(os.environ, WIDE_SHADOW_HOME=root, **(extra or {}))
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)[-1500:]


def main():
    PKG, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    assert sha(ORIG) == ORIG_SHA and sha(PATCH) == PATCH_SHA
    shutil.rmtree(OUT, ignore_errors=True); root = f"{OUT}/ws"; os.makedirs(f"{root}/state"); os.makedirs(f"{root}/fea171")
    rec = {"device_sha256": sha(os.path.abspath(__file__)), "pkg": PKG, "A0": A0, "A1": A1, "steps": {}}; S = rec["steps"]
    added = json.load(open(f"{PKG}/added_names.json"))
    # S0
    shutil.copytree(f"{WS}/shadow_bundle", f"{root}/shadow_bundle"); shutil.copy2(ORIG, f"{root}/shadow_loop_v3.py")
    shutil.copy2(f"{WS}/fea171/f10_live_s42_np.npz", f"{root}/fea171/f10_live_s42_np.npz")
    for f in ("rolling.npz", "aux.json", "leg_returns_live.json"): shutil.copy2(f"{WS}/state/snap/{A0}/{f}", f"{root}/state/{f}")
    M = module(root, ORIG); M.atomic_json(f"{root}/state/generation.json", M.build_generation_record(f"{root}/state", A0))
    ok, la, err = loads(root, ORIG); S["S0_sandbox_loads"] = {"PASS": ok and la == A0, "err": err}
    cfg = json.load(open(f"{root}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; sidx = {s: j for j, s in enumerate(syms)}; J = [sidx[s] for s in added]
    others = np.array([j for j in range(len(syms)) if j not in set(J)])
    # S1 emulated fetch → isolated copy (same file set and SOURCE contract as news_backfill.fetch)
    X = np.load(f"{P}/parity/parity_cache_slice.npz", allow_pickle=True); xts = X["ts"].astype(np.int64); row0 = int(X["row0"]); HZ = np.load(f"{P}/parity/parity_holes_slice.npz")
    z = np.load(f"{root}/state/rolling.npz", allow_pickle=True); rts = z["ts"].astype(np.int64); RD = np.array(z["data"], np.float16); RD0 = RD.copy()
    xi = np.searchsorted(xts, rts); assert np.array_equal(xts[xi], rts); pos = {int(v): q for q, v in enumerate(xi)}
    for s in added:
        j = sidx[s]; col = np.array(X["data"][xi, j, :], np.float16)
        for rr in (HZ["row"][HZ["col"] == j] - row0):
            if int(rr) in pos: col[pos[int(rr)]] = np.nan
        keep_nan = ~np.isfinite(RD[:, j, 3].astype(np.float32)); RD[keep_nan, j, :] = col[keep_nan]      # only NaN rows are written (news_backfill rule)
    iso = f"{OUT}/A2/isolated_state"; os.makedirs(iso)
    aux = json.load(open(f"{root}/state/aux.json"))
    for s in added: aux["prev_close"][s] = 1.0                                                              # placeholder (stated): no exchange call
    np.savez_compressed(f"{iso}/.rolling_tmp.npz", ts=rts, data=RD); os.replace(f"{iso}/.rolling_tmp.npz", f"{iso}/rolling.npz")
    M.atomic_json(f"{iso}/aux.json", aux); shutil.copy2(f"{root}/state/leg_returns_live.json", f"{iso}/leg_returns_live.json")
    M.atomic_json(f"{iso}/generation.json", M.build_generation_record(iso, A0))
    json.dump({"source_generation_sha256": sha(f"{root}/state/generation.json"), "source_last_anchor": A0, "EMULATED": "x0918r stand-in, no exchange"}, open(f"{iso}/SOURCE.json", "w"))
    S["S1_emulated_fetch"] = {"PASS": True, "added_columns_rows_finite_log_qv": int(np.isfinite(RD[:, J, 3].astype(np.float32)).sum())}
    # S2 install (the deploy command)
    rc, log = run([sys.executable, f"{P}/deploy/news_backfill.py", "install", f"{PKG}/added_names.json", f"{OUT}/A2"], root)
    z2 = np.load(f"{root}/state/rolling.npz", allow_pickle=True); R2 = np.array(z2["data"], np.float16); aux2 = json.load(open(f"{root}/state/aux.json"))
    ok, la, err = loads(root, ORIG)
    S["S2_install"] = {"rc": rc, "log": log, "added_equal_isolated": bool(np.array_equal(R2[:, J, :].view(np.uint16), RD[:, J, :].view(np.uint16))),
                       "others_byte_identical": bool(np.array_equal(R2[:, others, :].view(np.uint16), RD0[:, others, :].view(np.uint16))),
                       "prev_close_set": all(s in aux2["prev_close"] for s in added), "producer_loads": ok, "load_err": err}
    S["S2_install"]["PASS"] = rc == 0 and all(S["S2_install"][k] for k in ("added_equal_isolated", "others_byte_identical", "prev_close_set", "producer_loads"))
    # S3 negative control
    rc3, log3 = run([sys.executable, f"{P}/deploy/news_backfill.py", "install", f"{PKG}/added_names.json", f"{OUT}/A2"], root)
    S["S3_second_install_refused"] = {"rc": rc3, "log": log3[-300:], "PASS": rc3 != 0 and "REFUSE" in log3}
    # S4 patch + fetchlist (the deploy commands)
    bk = f"{OUT}/BK_A1"; os.makedirs(bk)
    for f in ("shadow_loop_v3.py",): shutil.copy2(f"{root}/{f}", f"{bk}/{f}")
    for f in ("config.json", "MANIFEST.json", "slow2026.txt"): shutil.copy2(f"{root}/shadow_bundle/{f}", f"{bk}/{f}")
    shutil.copy2(f"{root}/fea171/f10_live_s42_np.npz", f"{bk}/f10_live_s42_np.npz")
    shutil.copy2(PATCH, f"{root}/shadow_loop_v3.py")
    rc4, log4 = run([sys.executable, f"{P}/deploy/news_prod_files.py", "fetchlist", f"{PKG}/added_names.json", f"{OUT}/A4"], root)
    c4 = json.load(open(f"{root}/shadow_bundle/config.json")); ok4, _, err4 = loads(root, PATCH)
    S["S4_patch_fetchlist"] = {"rc": rc4, "log": log4[-600:], "patched_sha_ok": sha(f"{root}/shadow_loop_v3.py") == PATCH_SHA, "n_fetch": len(c4.get("symbols_fetch", [])),
                               "symbols_live_unchanged": c4["symbols_live"] == cfg["symbols_live"], "loads": ok4, "err": err4}
    S["S4_patch_fetchlist"]["PASS"] = rc4 == 0 and S["S4_patch_fetchlist"]["patched_sha_ok"] and S["S4_patch_fetchlist"]["n_fetch"] == 450 + len(added) and S["S4_patch_fetchlist"]["symbols_live_unchanged"] and ok4
    # S5 one anchor with the patched producer on the installed state
    Mp = module(root, PATCH); cfgp, booster, man = Mp.load_bundle(); cfgp["_booster_sha"] = man.get("slow2026.txt", ""); st = Mp.ShadowState(cfgp)
    zA = np.load(f"{WS}/state/snap/{A1}/rolling.npz", allow_pickle=True); tsA = zA["ts"].astype(np.int64); dA = np.array(zA["data"], np.float16)
    xiA = np.searchsorted(xts, tsA); posA = {int(v): q for q, v in enumerate(xiA)}
    for s in added:
        j = sidx[s]; col = np.array(X["data"][xiA, j, :], np.float16)
        for rr in (HZ["row"][HZ["col"] == j] - row0):
            if int(rr) in posA: col[posA[int(rr)]] = np.nan
        dA[:, j, :] = col
    st.cts, st.cd = tsA, dA
    Mp.run_anchor(st, FakeFetcher(json.load(open(f"{WS}/state/snap/{A1}/aux.json"))), cfgp, booster, A1)
    w = np.load(f"{root}/state/weights/{A1}.npz"); tl = json.load(open(f"{root}/state/target_live/{A1}.json"))
    E = np.load(f"{PKG}/NEWS_ACCEPT_ROWS.npz", allow_pickle=True); tm = sorted(E[f"m_{A1}"].astype(int).tolist())
    Jset = set(J); ok5, la5, err5 = loads(root, PATCH)
    S["S5_one_anchor"] = {"members_equal_training": sorted(int(x) for x in w["members"]) == tm, "added_members": sum(1 for j in w["members"] if int(j) in Jset),
                          "added_names_zero_weight": not any(int(j) in Jset and float(v) != 0.0 for j, v in zip(w["idx"], w["val"])),
                          "universe_450": tl["universe"] == cfg["symbols_live"], "state_reloads": ok5 and la5 == A1, "err": err5}
    S["S5_one_anchor"]["PASS"] = all(S["S5_one_anchor"][k] for k in ("members_equal_training", "added_names_zero_weight", "universe_450", "state_reloads"))
    R5 = np.array(np.load(f"{root}/state/rolling.npz", allow_pickle=True)["data"], np.float16)
    # B0 backup (the manual's B0: taken after W1, before the model swap)
    b0 = f"{OUT}/BK_B0"; os.makedirs(b0)
    for f in ("MANIFEST.json", "slow2026.txt"): shutil.copy2(f"{root}/shadow_bundle/{f}", f"{b0}/{f}")
    shutil.copy2(f"{root}/fea171/f10_live_s42_np.npz", f"{b0}/f10_live_s42_np.npz")
    # S6 models (the deploy command) with the package
    rc6, log6 = run([sys.executable, f"{P}/deploy/news_prod_files.py", "models", f"{PKG}/slow2026.txt", f"{PKG}/f10_live_s42_np.npz", f"{OUT}/B2"], root)
    pins = json.load(open(f"{PKG}/P5_DEPLOY_MANIFEST.json"))["deploy"]["executor_pins"]
    try:
        printed = json.loads([l for l in log6.splitlines() if l.startswith("{")][-1])
    except Exception:
        printed = {}
    ok6, _, err6 = loads(root, PATCH)
    S["S6_models"] = {"rc": rc6, "printed": printed, "pins_equal_manifest": printed.get("booster_sha_pin") == pins["booster_sha_pin"] and printed.get("f10_sha_pin") == pins["f10_sha_pin"],
                      "bytes_equal_package": sha(f"{root}/shadow_bundle/slow2026.txt") == sha(f"{PKG}/slow2026.txt") and sha(f"{root}/fea171/f10_live_s42_np.npz") == sha(f"{PKG}/f10_live_s42_np.npz"),
                      "loads": ok6, "err": err6}
    S["S6_models"]["PASS"] = rc6 == 0 and S["S6_models"]["pins_equal_manifest"] and S["S6_models"]["bytes_equal_package"] and ok6
    # S7 R-B restore (the manual's R-B step 2, verbatim semantics: slow2026.txt + MANIFEST.json + f10 file back from the B0 backup)
    for f in ("slow2026.txt", "MANIFEST.json"): shutil.copy2(f"{b0}/{f}", f"{root}/shadow_bundle/{f}")
    shutil.copy2(f"{b0}/f10_live_s42_np.npz", f"{root}/fea171/f10_live_s42_np.npz")
    ok7, _, err7 = loads(root, PATCH)
    S["S7_RB_restore"] = {"king_sha": sha(f"{root}/shadow_bundle/slow2026.txt")[:8], "f10_sha": sha(f"{root}/fea171/f10_live_s42_np.npz")[:8], "loads": ok7, "err": err7}
    S["S7_RB_restore"]["manifest_equal_B0"] = sha(f"{root}/shadow_bundle/MANIFEST.json") == sha(f"{b0}/MANIFEST.json")
    S["S7_RB_restore"]["PASS"] = S["S7_RB_restore"]["king_sha"] == "8d79186b" and S["S7_RB_restore"]["f10_sha"] == "351ae26b" and ok7 and S["S7_RB_restore"]["manifest_equal_B0"]
    # S8 R-A restore: producer + config + MANIFEST from the W1 backup, then rollback (the deploy command)
    shutil.copy2(f"{bk}/shadow_loop_v3.py", f"{root}/shadow_loop_v3.py")
    for f in ("config.json", "MANIFEST.json"): shutil.copy2(f"{bk}/{f}", f"{root}/shadow_bundle/{f}")
    rc8, log8 = run([sys.executable, f"{P}/deploy/news_backfill.py", "rollback", f"{PKG}/added_names.json", f"{OUT}/RA"], root)
    R8 = np.array(np.load(f"{root}/state/rolling.npz", allow_pickle=True)["data"], np.float16); aux8 = json.load(open(f"{root}/state/aux.json"))
    ok8, la8, err8 = loads(root, ORIG)
    S["S8_RA_restore"] = {"rc": rc8, "log": log8[-300:], "added_all_nan": bool(np.isnan(R8[:, J, :].astype(np.float32)).all()),
                          "others_unchanged_since_S5": bool(np.array_equal(R8[:, others, :].view(np.uint16), R5[:, others, :].view(np.uint16))),
                          "prev_close_removed": not any(s in aux8["prev_close"] for s in added), "original_producer_loads": ok8 and la8 == A1, "err": err8,
                          "producer_sha": sha(f"{root}/shadow_loop_v3.py")[:8]}
    S["S8_RA_restore"]["PASS"] = rc8 == 0 and all(S["S8_RA_restore"][k] for k in ("added_all_nan", "others_unchanged_since_S5", "prev_close_removed", "original_producer_loads"))
    ok = all(v["PASS"] for v in S.values()); rec["VERDICT"] = "PASS" if ok else "FAIL"
    json.dump(rec, open(f"{OUT}/TEST_BACKFILL_INSTALL_REHEARSAL.json", "w"), indent=1, default=str)
    print("TEST_BACKFILL_INSTALL_REHEARSAL", rec["VERDICT"], {k: v["PASS"] for k, v in S.items()}, flush=True)
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    main()
