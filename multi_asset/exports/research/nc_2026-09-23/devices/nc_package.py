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
usage: ~/wide_shadow/venv/bin/python nc_package.py <out dir> --tree T --extras X --king K --f10 F --crypto C [--label NAME]"""
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


def main():
    global HOME
    ap = argparse.ArgumentParser()
    for k in ("out", ): ap.add_argument(k)
    for k in ("--tree", "--extras", "--king", "--f10", "--crypto"): ap.add_argument(k, required=True)
    ap.add_argument("--label", default="NC"); ap.add_argument("--home", default=os.path.expanduser("~"), help="machine layout the baselines are read from (rehearsal: a copy)")
    a = ap.parse_args(); HOME = a.home
    assert not os.path.exists(a.out), "refusing to overwrite"
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
                "tree": {"path": os.path.abspath(a.tree), "patch_receipt_sha256": sha(f"{a.tree}/PATCH_RECEIPT.json"), "derive_self_sha256": rec["self_sha256"]},
                "inputs": {"king": os.path.abspath(a.king), "f10": os.path.abspath(a.f10), "crypto": {"path": os.path.abspath(a.crypto), "sha256": sha(a.crypto)},
                           "extras": os.path.abspath(a.extras)},
                "state_files_nc": ["rolling.npz", "aux.json", "leg_returns_live.json", "boundary_raw.npz", "members_hist.npz"],
                "services": {"stop": ["com.hsy.shadowloop", "com.hsy.combolive", "com.hsy.combosnap", "com.hsy.comboparity", "com.hsy.sidecar"],
                             "restart": ["com.hsy.comboparity", "com.hsy.combosnap", "com.hsy.combolive", "com.hsy.shadowloop"],
                             "disabled": ["com.hsy.sidecar"]}}
    shutil.copyfile(f"{a.tree}/PATCH_RECEIPT.json", f"{a.out}/PATCH_RECEIPT.json")
    json.dump(contract, open(f"{a.out}/INSTALL_CONTRACT.json", "w"), indent=1)
    print("NC_PACKAGE", json.dumps({"out": a.out, "files": len(files), "new_files": [f["dest"] for f in files if f["baseline_sha256"] is None],
                                    "already_equal": changed_to_same, "executor_pins": contract["executor_pins"],
                                    "contract_sha256": sha(f"{a.out}/INSTALL_CONTRACT.json")}), flush=True)


if __name__ == "__main__":
    main()
