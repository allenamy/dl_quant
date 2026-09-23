#!/usr/bin/env python3
"""Install / rollback rehearsal of nc_package.py + nc_install.py on a COPY of the machine layout (fake HOME built from production files and
one archived snapshot; the real ~/wide_shadow, ~/regime_dash, ~/dl_quant_live are only read). MACHINERY: the models are stand-ins (the
NEW_S package's King / F10, real files of the right format, never the deployment models) and the seed pack is the fork's synthetic
machine pack; the verdict is prefixed MACHINERY_ and is not a deployment receipt.
  P1 package built against the fake home; preflight (package + seeded state rows) PASS
  N1 a destination changed after packaging            ⇒ preflight REFUSED (restored afterwards)
  A1 apply                                            ⇒ stage installed_not_started; the NC producer (5 STATE_FILES) loads the state
  R1 rollback, state never advanced                   ⇒ state from the backup; every destination back to its baseline bytes, new files
                                                         moved aside, NC-only state files gone; the OLD producer (3 STATE_FILES) loads it;
                                                         the state files equal the pre-install bytes
  A2 apply again (same seeded dir: production is byte-identical again) ⇒ installed
  N2 state advanced (aux changed + generation re-signed by the NC module), rollback WITHOUT --downgraded ⇒ REFUSED (named)
  R2 nc_downgrade_state.py on the current state, rollback --downgraded ⇒ OLD producer loads; destinations at baseline
usage: ~/wide_shadow/venv/bin/python test_nc_install_rehearsal.py <NC tree> <extras dir> <synth seed pack> <snapshot anchor> <work dir>"""
import hashlib, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); HOME = os.path.expanduser("~"); PY = f"{HOME}/wide_shadow/venv/bin/python"
KING = f"{HOME}/cc_tmp/news_20260923/package_NEW_S/slow2026.txt"; F10 = f"{HOME}/cc_tmp/news_20260923/package_NEW_S/f10_live_s42_np.npz"
CRYPTO = f"{HOME}/cc_tmp/news_20260923/package_NEW_S/crypto_P1_members_2025H2on.npz"
FAILS, N = [], [0]


def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:400]) if detail is not None else ""), flush=True)


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def run(args):
    r = subprocess.run([PY] + args, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]


def fake_home(fh, A):
    W = f"{HOME}/wide_shadow"; w = f"{fh}/wide_shadow"
    os.makedirs(f"{w}/fea171/combosnap"); os.makedirs(f"{w}/state"); os.makedirs(f"{fh}/regime_dash"); os.makedirs(f"{fh}/dl_quant_live/state")
    open(f"{fh}/dl_quant_live/state/anchor.lock", "w").close()
    os.symlink(f"{W}/venv", f"{w}/venv")
    shutil.copy2(f"{W}/shadow_loop_v3.py", w)
    for f in ("combo_stage.py", "dlw_features.py", "f8_higher_order_features.py", "feature_cache_identity.py", "xfer_syms.npz", "xfer_ref.npz",
              "f10_live_s42_np.npz", "combo_state_snapshot.sh", "combo_live_daemon.sh", "sidecar_blend.py"):
        shutil.copy2(f"{W}/fea171/{f}", f"{w}/fea171/{f}")
    for f in os.listdir(f"{W}/fea171/combosnap"):
        if os.path.isfile(f"{W}/fea171/combosnap/{f}"): shutil.copy2(f"{W}/fea171/combosnap/{f}", f"{w}/fea171/combosnap/{f}")
    shutil.copytree(f"{W}/shadow_bundle", f"{w}/shadow_bundle")
    for f in ("rolling.npz", "aux.json", "leg_returns_live.json", "generation.json"): shutil.copy2(f"{W}/state/snap/{A}/{f}", f"{w}/state/{f}")
    shutil.copy2(f"{HOME}/regime_dash/regime_dash.py", f"{fh}/regime_dash/regime_dash.py")


def main():
    tree, extras, pack, A, work = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
    assert not os.path.exists(work); os.makedirs(work); fh = f"{work}/home"; fake_home(fh, A)
    st = f"{fh}/wide_shadow/state"; pre = {f: sha(f"{st}/{f}") for f in os.listdir(st)}
    pkg = f"{work}/package"; seeded = f"{work}/seeded"
    rc, out = run([f"{HERE}/nc_package.py", pkg, "--home", fh, "--tree", tree, "--extras", extras, "--king", KING, "--f10", F10, "--crypto", CRYPTO, "--label", "MACHINERY_REHEARSAL"])
    C = json.load(open(f"{pkg}/INSTALL_CONTRACT.json")) if rc == 0 else {}
    base = {it["dest"]: it["baseline_sha256"] for it in C.get("files", [])}
    rc2, out2 = run([f"{HERE}/nc_seed_state.py", tree, pack, st, seeded + "_nolive"])
    # post-axis bound cells need their exact raw from a live pack (nc_deploy_fetch.py, venue); the rehearsal uses a STAND-IN pack whose raw
    # values are +-0.35 (beyond the clip, sign of ch0) for exactly the cells the seed tool named — machinery only
    import numpy as np
    # the synthetic machine pack carries NO boundary cells (the real seed pack carries the training table), so the stand-in also covers the
    # pre-axis bound cells of the window; every crypto bound cell of the seeded window not already in the table gets a stand-in raw
    Zs = np.load(f"{seeded}_nolive/state/rolling.npz", allow_pickle=True); Bs = np.load(f"{seeded}_nolive/state/boundary_raw.npz")
    have = set(zip(Bs["ts"].astype(np.int64).tolist(), Bs["col"].astype(np.int64).tolist()))
    crypto = np.zeros(Zs["data"].shape[1], bool); crypto[np.load(pack)["crypto_cols"].astype(np.int64)] = True
    c0 = Zs["data"][:, :, 0].astype(np.float32); B16 = np.float32(np.float16(0.3))
    cells = [(int(Zs["ts"][i]), int(j)) for i, j in np.argwhere(np.isfinite(c0) & (np.abs(c0) == B16)) if crypto[j] and (int(Zs["ts"][i]), int(j)) not in have]
    rp = {int(t): i for i, t in enumerate(Zs["ts"])}
    bt = [t for t, _ in cells]; bc = [c for _, c in cells]
    br = [np.float32(0.35 * np.sign(float(c0[rp[t], c]))) for t, c in cells]
    np.savez(f"{work}/standin_live_pack.npz", row_ts=np.zeros(0, np.int64), row_col=np.zeros(0, np.int64), row_val=np.zeros((0, 7), np.float16),
             bnd_ts=np.array(bt, np.int64), bnd_col=np.array(bc, np.int32), bnd_raw=np.array(br, np.float32),
             pc_sym=np.array([], dtype="<U1"), pc_close=np.zeros(0), pc_ts=np.zeros(0, np.int64))
    rc2, out2 = run([f"{HERE}/nc_seed_state.py", tree, pack, st, seeded, "--live-pack", f"{work}/standin_live_pack.npz"])
    print(f"  (stand-in live pack: {len(bt)} bound cells, {sum(1 for t in bt if t > int(np.load(pack)['axis_end']))} post-axis)", flush=True)
    rc3, out3 = run([f"{HERE}/nc_install.py", "preflight", pkg, "--seeded", seeded, "--seed-pack", pack, "--home", fh])
    check("P1 package + seed + preflight PASS", rc == 0 and rc2 == 0 and rc3 == 0 and "PREFLIGHT_PASS" in out3[0], (rc, out[0][:120], rc2, out2[0][:120], rc3, out3[0][:200]))
    if FAILS: print("baseline not green; stop"); sys.exit(1)
    tgt = f"{fh}/wide_shadow/fea171/combo_stage.py"; keep = open(tgt, "rb").read(); open(tgt, "ab").write(b"\n# drift\n")
    rc, out = run([f"{HERE}/nc_install.py", "preflight", pkg, "--home", fh])
    open(tgt, "wb").write(keep)
    check("N1 destination changed after packaging ⇒ preflight REFUSED", rc == 3 and "not at its baseline" in out[0], out[0][:200])
    common = ["--home", fh, "--no-launchctl", "--ignore-window"]
    rc, out = run([f"{HERE}/nc_install.py", "apply", pkg, f"{work}/bk1", "--seeded", seeded, "--seed-pack", pack] + common)
    R = json.load(open(f"{work}/bk1/NC_INSTALL_RECEIPT.json")) if os.path.exists(f"{work}/bk1/NC_INSTALL_RECEIPT.json") else {}
    pl = R.get("producer_load", {})
    check("A1 apply ⇒ installed_not_started; NC producer (5 STATE_FILES) loads the state",
          rc == 0 and R.get("stage") == "installed_not_started" and len(pl.get("state_files", [])) == 5 and all(sha(f"{fh}/{d}") == c for d, c in R.get("installed", {}).items()),
          (rc, out[0][:200], R.get("stage"), pl))
    rc, out = run([f"{HERE}/nc_install.py", "rollback", pkg, f"{work}/bk1"] + common)
    rb = sorted(x for x in os.listdir(f"{work}/bk1") if x.startswith("rollback_moved_aside_"))
    RR = json.load(open(f"{work}/bk1/{rb[-1]}/NC_ROLLBACK_RECEIPT.json")) if rb else {}
    dest_ok = all((sha(f"{fh}/{d}") if os.path.exists(f"{fh}/{d}") else None) == b for d, b in base.items())
    state_ok = {f: sha(f"{st}/{f}") for f in os.listdir(st) if os.path.isfile(f"{st}/{f}")} == pre
    check("R1 rollback (never advanced) ⇒ backup state; destinations at baseline; new files gone; NC-only state gone; OLD producer loads; state = pre-install bytes",
          rc == 0 and RR.get("stage") == "rolled_back_not_started" and "backup" in RR.get("state_source", "") and dest_ok and state_ok
          and len(RR.get("producer_load", {}).get("state_files", [])) == 3, (rc, out[0][:200], RR.get("state_source"), dest_ok, state_ok))
    rc, out = run([f"{HERE}/nc_install.py", "apply", pkg, f"{work}/bk2", "--seeded", seeded, "--seed-pack", pack] + common)
    check("A2 apply again on the byte-identical production state ⇒ installed", rc == 0 and "installed_not_started" in out[0], out[0][:200])
    # the NC producer "advances" the state: an aux change signed by the NC module's own generation writer
    sys.path.insert(0, HERE); import nc_sandbox_lib as L
    M = L.load_producer(f"{fh}/wide_shadow", "advance")
    aux = json.load(open(f"{st}/aux.json")); aux["nc_backfill_residual"] = ["REHEARSAL_MARK"]; json.dump(aux, open(f"{st}/aux.json", "w"))
    M.atomic_json(f"{st}/generation.json", M.build_generation_record(st, int(aux["last_anchor"])))
    rc, out = run([f"{HERE}/nc_install.py", "rollback", pkg, f"{work}/bk2"] + common)
    check("N2 state advanced, rollback without --downgraded ⇒ REFUSED (named)", rc == 3 and "advanced the state" in out[0], out[0][:200])
    rc, out = run([f"{HERE}/nc_downgrade_state.py", st, f"{work}/dg"])
    rc2, out2 = run([f"{HERE}/nc_install.py", "rollback", pkg, f"{work}/bk2", "--downgraded", f"{work}/dg"] + common)
    rb = sorted(x for x in os.listdir(f"{work}/bk2") if x.startswith("rollback_moved_aside_"))
    RR = json.load(open(f"{work}/bk2/{rb[-1]}/NC_ROLLBACK_RECEIPT.json")) if rb else {}
    dest_ok = all((sha(f"{fh}/{d}") if os.path.exists(f"{fh}/{d}") else None) == b for d, b in base.items())
    check("R2 downgrade the current state, rollback --downgraded ⇒ OLD producer loads; destinations at baseline; no NC-only state file",
          rc == 0 and rc2 == 0 and "downgraded" in RR.get("state_source", "") and dest_ok and len(RR.get("producer_load", {}).get("state_files", [])) == 3
          and not any(os.path.exists(f"{st}/{f}") for f in ("boundary_raw.npz", "members_hist.npz")), (rc, out[0][:160], rc2, out2[0][:200], RR.get("state_source"), dest_ok))
    verdict = "MACHINERY_PASS" if not FAILS else "MACHINERY_FAIL"
    json.dump({"verdict": verdict, "checks": N[0], "failed": FAILS, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "device_sha256": {f: sha(f"{HERE}/{f}") for f in ("nc_package.py", "nc_install.py", "nc_seed_state.py", "nc_downgrade_state.py", "test_nc_install_rehearsal.py")},
               "tree_patch_receipt_sha256": sha(f"{tree}/PATCH_RECEIPT.json"), "snapshot_anchor": A, "stand_in_models": [KING, F10],
               "stand_in_live_pack": "raw = +-0.35 for the seed tool's unresolved post-axis bound cells (machinery only)"},
              open(f"{work}/TEST_NC_INSTALL_REHEARSAL.json", "w"), indent=1)
    print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed"); print("TEST_NC_INSTALL_REHEARSAL", verdict)
    sys.exit(0 if not FAILS else 1)


if __name__ == "__main__":
    main()
