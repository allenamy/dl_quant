#!/usr/bin/env python3
"""NC deploy package builder (DESIGN §A7 / §D / §F; FREEZE b30e4afa5 + amendment 1). Pure file assembly into a NEW directory; reads
production only to record baselines; never writes ~/wide_shadow, ~/regime_dash or ~/dl_quant_live.
The package holds every CHANGED or NEW producer-side file at its install path (relative to HOME) and INSTALL_CONTRACT.json:
  files[]        dest (relative to HOME), candidate_sha256, baseline_sha256 (the production bytes at packaging; null = new file)
  unchanged      files the release must NOT change, with their production sha (asserted again at install)
  executor_pins  booster_sha_pin = sha(King model), f10_sha_pin = sha(F10 model)
  tree           the derive receipt (release build, arm switches at defaults) and its sha
Sources:
  --tree     the release tree from nc_derive_producer.py --release (shadow_loop_v3.py + fea171/*)
  --extras   release extras (combosnap / regime_dash; DESIGN §A7-5)
  --king     King model (bundle slow2026.txt)      --f10  F10 serving model (fea171/f10_live_s42_np.npz)
  --crypto   the frozen crypto npz on the 829 axis -> shadow_bundle/crypto_axis.json (bytes identical to the rehearsal sandbox's)
MANIFEST.json = the production MANIFEST with slow2026.txt and crypto_axis.json set to the package's bytes; every other entry unchanged.
  --export-manifest M --ruling R  (lead 2026-09-24, user ruling RULING_user_NC_s42_override_2026-09-24.md): bind the contract to news2's
             export manifest (news2_export_models.py P5_DEPLOY_MANIFEST.json). Asserted: lineage_bound, seed s42, the exported slow2026.txt /
             f10_live_s42_np.npz shas == sha(--king) / sha(--f10) == the manifest's executor_pins; VERDICT copied VERBATIM; if VERDICT != DEPLOY the
             manifest's USER_OVERRIDE == its verified override sha == sha(--ruling) measured here. Any mismatch ⇒ REFUSED (exit 3), nothing written.
             The manifest and the ruling are copied into <out>/verdict/ so nc_install.py re-verifies them from the package. Without the pair the
             contract says verdict.bound=false; nc_install.py refuses such a contract on the real home (rehearsal homes only).
             Wording: the verdict is recorded as VERDICT=<frozen verdict> + USER_OVERRIDE=<ruling sha>; this tool never writes an admission word.
usage: ~/wide_shadow/venv/bin/python nc_package.py <out dir> --tree T --extras X --king K --f10 F --crypto C [--label NAME]
       [--export-manifest M --ruling R]"""
import argparse, hashlib, json, os, shutil, sys, time
import numpy as np

HOME = os.path.expanduser("~")
TREE_FILES = ["shadow_loop_v3.py", "fea171/combo_stage.py", "fea171/dlw_features.py", "fea171/f8_higher_order_features.py",
              "fea171/feature_cache_identity.py", "fea171/nc_contract.py", "fea171/tradability.py", "fea171/beta_overlay_producer.py",
              "fea171/stable_trend_reference.py"]
TREE_UNCHANGED = ["fea171/xfer_syms.npz", "fea171/xfer_ref.npz"]
EXTRAS = ["wide_shadow/fea171/combo_state_snapshot.sh", "wide_shadow/fea171/combosnap/combo_parity_replay.sh",
          "wide_shadow/fea171/combosnap/generation_files.py", "regime_dash/regime_dash.py"]
UNCHANGED = ["wide_shadow/shadow_bundle/config.json", "wide_shadow/fea171/xfer_syms.npz", "wide_shadow/fea171/xfer_ref.npz",
             "wide_shadow/fea171/combosnap/check_snapshot_generation.py", "wide_shadow/fea171/combosnap/combo_parity_agent.sh",
             "wide_shadow/fea171/combosnap/combo_parity_compare.py", "wide_shadow/fea171/combosnap/offline_stage.py",
             "wide_shadow/fea171/combosnap/replay_paths.py", "wide_shadow/fea171/combo_live_daemon.sh", "wide_shadow/fea171/sidecar_blend.py"]


def sha_b(b): return hashlib.sha256(b).hexdigest()
def sha(p): return sha_b(open(p, "rb").read())


def crypto_axis_bytes(crypto_npz, symbols_panel):
    """Same construction as nc_sandbox_lib.crypto_axis_json + json.dumps (the rehearsal / timing sandboxes) — asserted equal below."""
    z = np.load(crypto_npz, allow_pickle=True); cr = z["crypto"].astype(bool)
    assert [str(x) for x in z["symbols"]] == list(symbols_panel), "crypto npz axis differs from symbols_panel"
    return json.dumps({"symbols": list(symbols_panel), "crypto": [bool(x) for x in cr], "rule": "P1 frozen crypto rule (AMENDMENT 1 §3.2)"}).encode()


class Refused(Exception):
    pass


def bind_verdict(manifest, ruling, king_sha, f10_sha):
    """The verdict record, from news2's export manifest; raises Refused on any mismatch. Reads only."""
    def need(ok, msg):
        if not ok: raise Refused(msg)
    M = json.load(open(manifest))
    need(M.get("lineage_bound") is True, "export manifest: lineage_bound is not true")
    need(M.get("seed") == "s42", f"export manifest: seed {M.get('seed')!r} != 's42' (the ruling releases s42 only)")
    ex = M.get("exported_files") or []
    byname = {}
    for e in ex: byname.setdefault(e.get("name"), []).append(e)
    need(sorted(byname) == ["f10_live_s42_np.npz", "slow2026.txt"] and all(len(v) == 1 for v in byname.values()),
         f"export manifest: exported_files names {sorted(byname)} (want exactly slow2026.txt and f10_live_s42_np.npz once each)")
    need(byname["slow2026.txt"][0]["sha256"] == king_sha, f"--king sha {king_sha} != export manifest slow2026.txt {byname['slow2026.txt'][0]['sha256']}")
    need(byname["f10_live_s42_np.npz"][0]["sha256"] == f10_sha, f"--f10 sha {f10_sha} != export manifest f10_live_s42_np.npz {byname['f10_live_s42_np.npz'][0]['sha256']}")
    pins = (M.get("deploy") or {}).get("executor_pins")
    need(pins == {"booster_sha_pin": king_sha, "f10_sha_pin": f10_sha}, f"export manifest deploy.executor_pins {pins} != the package's models")
    V = M.get("VERDICT"); need(isinstance(V, str) and V, "export manifest: no VERDICT")
    uo = M.get("user_override") or {}
    rec = {"bound": True, "VERDICT": V, "seed": "s42", "export_manifest": {"path": os.path.abspath(manifest), "sha256": sha(manifest)},
           "exported_files": [{"name": n, "sha256": byname[n][0]["sha256"], "path_at_export": byname[n][0].get("path")} for n in sorted(byname)]}
    if V == "DEPLOY":
        need("USER_OVERRIDE" not in M, "export manifest: VERDICT=DEPLOY but a USER_OVERRIDE is present")
        rec["USER_OVERRIDE"] = None; rec["ruling"] = None
    else:
        need(ruling is not None, f"VERDICT={V}: --ruling (the user ruling file) is required")
        rs = sha(ruling)
        need(M.get("USER_OVERRIDE") == rs, f"export manifest USER_OVERRIDE {M.get('USER_OVERRIDE')} != sha(--ruling) {rs}")
        need(uo.get("override_verified") is True and uo.get("override_sha_measured") == rs, f"export manifest user_override record not verified for {rs}: {uo}")
        rec["USER_OVERRIDE"] = rs; rec["ruling"] = {"path": os.path.abspath(ruling), "sha256": rs}
    rec["statement"] = (f"VERDICT={V}" + (f" USER_OVERRIDE={rec['USER_OVERRIDE']}" if rec["USER_OVERRIDE"] else "")
                        + ("; a user permission recorded against the frozen verdict, not an admission; FREEZE §2 unamended" if rec["USER_OVERRIDE"] else ""))
    return rec


def main():
    global HOME
    ap = argparse.ArgumentParser()
    for k in ("out", ): ap.add_argument(k)
    for k in ("--tree", "--extras", "--king", "--f10", "--crypto"): ap.add_argument(k, required=True)
    ap.add_argument("--label", default="NC"); ap.add_argument("--home", default=os.path.expanduser("~"), help="machine layout the baselines are read from (rehearsal: a copy)")
    ap.add_argument("--export-manifest", default=None); ap.add_argument("--ruling", default=None)
    a = ap.parse_args(); HOME = a.home
    assert not os.path.exists(a.out), "refusing to overwrite"
    if a.ruling and not a.export_manifest:
        raise Refused("--ruling without --export-manifest")
    verdict = (bind_verdict(a.export_manifest, a.ruling, sha(a.king), sha(a.f10)) if a.export_manifest else
               {"bound": False, "VERDICT": None, "USER_OVERRIDE": None, "statement": "no export manifest given: rehearsal-only contract (nc_install.py refuses it on the real home)"})
    rec = json.load(open(f"{a.tree}/PATCH_RECEIPT.json"))
    assert rec["release_build"] is True and rec["arm_switches_at_defaults"] is True, "not a release build"
    for f in TREE_FILES + TREE_UNCHANGED:
        assert sha(f"{a.tree}/{f}") == rec["outputs"][f], ("tree file differs from its receipt", f)
    for f in TREE_UNCHANGED:
        assert sha(f"{a.tree}/{f}") == sha(f"{HOME}/wide_shadow/{f}"), ("tree changes a file the release keeps", f)
    cfg = json.load(open(f"{HOME}/wide_shadow/shadow_bundle/config.json"))
    cax = crypto_axis_bytes(a.crypto, cfg["symbols_panel"])
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import nc_sandbox_lib as L
    assert json.dumps(L.crypto_axis_json(cfg["symbols_panel"])).encode() == cax, "crypto_axis.json bytes differ from the rehearsal sandbox's"
    man = json.load(open(f"{HOME}/wide_shadow/shadow_bundle/MANIFEST.json"))
    man_new = dict(man); man_new["slow2026.txt"] = sha(a.king); man_new["crypto_axis.json"] = sha_b(cax)
    items = {}                                                   # dest (rel HOME) -> bytes
    for f in TREE_FILES: items[f"wide_shadow/{f}"] = open(f"{a.tree}/{f}", "rb").read()
    for f in EXTRAS: items[f] = open(f"{a.extras}/{f}", "rb").read()
    items["wide_shadow/shadow_bundle/crypto_axis.json"] = cax
    items["wide_shadow/shadow_bundle/slow2026.txt"] = open(a.king, "rb").read()
    items["wide_shadow/shadow_bundle/MANIFEST.json"] = json.dumps(man_new, indent=1).encode()
    items["wide_shadow/fea171/f10_live_s42_np.npz"] = open(a.f10, "rb").read()
    files = []
    for dest, raw in sorted(items.items()):
        p = f"{a.out}/files/{dest}"; os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(raw)
        cur = f"{HOME}/{dest}"
        files.append({"dest": dest, "candidate_sha256": sha_b(raw), "baseline_sha256": sha(cur) if os.path.exists(cur) else None})
    changed_to_same = [f["dest"] for f in files if f["baseline_sha256"] == f["candidate_sha256"]]
    unchanged = {u: sha(f"{HOME}/{u}") for u in UNCHANGED}
    contract = {"schema": "nc_install_contract_v1", "label": a.label, "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "device_sha256": sha(os.path.abspath(__file__)), "home": HOME, "files": files, "files_already_equal_to_production": changed_to_same,
                "unchanged": unchanged, "executor_pins": {"booster_sha_pin": sha(a.king), "f10_sha_pin": sha(a.f10)},
                "verdict": verdict, "VERDICT": verdict["VERDICT"], "USER_OVERRIDE": verdict["USER_OVERRIDE"],
                "tree": {"path": os.path.abspath(a.tree), "patch_receipt_sha256": sha(f"{a.tree}/PATCH_RECEIPT.json"), "derive_self_sha256": rec["self_sha256"]},
                "inputs": {"king": os.path.abspath(a.king), "f10": os.path.abspath(a.f10), "crypto": {"path": os.path.abspath(a.crypto), "sha256": sha(a.crypto)},
                           "extras": os.path.abspath(a.extras)},
                "state_files_nc": ["rolling.npz", "aux.json", "leg_returns_live.json", "boundary_raw.npz", "members_hist.npz"],
                "services": {"stop": ["com.hsy.shadowloop", "com.hsy.combolive", "com.hsy.combosnap", "com.hsy.comboparity", "com.hsy.sidecar"],
                             "restart": ["com.hsy.comboparity", "com.hsy.combosnap", "com.hsy.combolive", "com.hsy.shadowloop"],
                             "disabled": ["com.hsy.sidecar"]}}
    shutil.copyfile(f"{a.tree}/PATCH_RECEIPT.json", f"{a.out}/PATCH_RECEIPT.json")
    if verdict["bound"]:                                         # the package carries its own verdict evidence (re-verified by nc_install.py)
        os.makedirs(f"{a.out}/verdict")
        shutil.copyfile(a.export_manifest, f"{a.out}/verdict/export_manifest.json")
        assert sha(f"{a.out}/verdict/export_manifest.json") == verdict["export_manifest"]["sha256"], "export manifest changed while packaging"
        if verdict["ruling"]:
            shutil.copyfile(a.ruling, f"{a.out}/verdict/ruling.md")
            assert sha(f"{a.out}/verdict/ruling.md") == verdict["USER_OVERRIDE"], "ruling changed while packaging"
    json.dump(contract, open(f"{a.out}/INSTALL_CONTRACT.json", "w"), indent=1)
    print("NC_PACKAGE", json.dumps({"out": a.out, "files": len(files), "new_files": [f["dest"] for f in files if f["baseline_sha256"] is None],
                                    "already_equal": changed_to_same, "executor_pins": contract["executor_pins"],
                                    "contract_sha256": sha(f"{a.out}/INSTALL_CONTRACT.json")}), flush=True)
    print("NC_PACKAGE_VERDICT_RECORD", verdict["statement"] if verdict["bound"] else "UNBOUND (rehearsal-only contract)", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Refused as e:
        print(f"NC_PACKAGE REFUSED: {e}", flush=True); sys.exit(3)
