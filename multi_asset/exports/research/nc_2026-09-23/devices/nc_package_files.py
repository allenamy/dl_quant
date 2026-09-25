#!/usr/bin/env python3
"""nc_package_files.py — the FILES-ONLY release package (v2 + C on top of the NC release; lead ruling 2026-09-25). No state is part of it:
the producer's state is already in the NC format; the release changes code files and archives three stale files + one plist (k1).

Contract `nc_files_contract_v1` (<out>/INSTALL_CONTRACT.json), files copied under <out>/files/<dest>:
  files          every producer file of the derived tree whose bytes differ from production (dest relative to HOME), with candidate_sha256
                 (sha of the in-memory bytes packaged) and baseline_sha256 (production now; None = new file)
  archive_moves  k1 (gate 3' revision 2): src -> dst under wide_shadow/fea171/_archive_2026-09-25/, expected_sha256 = production now
  unchanged      tree files equal to production + the model / bundle pins, with their sha (must not change during the install)
  services       stop = producer-side launchd labels that must not be running; not_loaded = labels that must not even be loaded (sidecar)
  forbidden_dest_prefixes  wide_shadow/state/ — a files-only package can never write state (the installer refuses such a contract)
  release_basis  the governing records (NC verdict unchanged; this release changes no model)
usage: ~/wide_shadow/venv/bin/python nc_package_files.py <derived tree> <out dir> --label L
"""
import argparse, hashlib, json, os, shutil, sys, time

HOME = os.path.expanduser("~")
ARCHIVE = "wide_shadow/fea171/_archive_2026-09-25"
K1 = ["wide_shadow/fea171/sidecar_blend.py", "wide_shadow/fea171/combo_stage_t3c_candidate.py", "wide_shadow/fea171/sidecar_daemon.sh",
      "Library/LaunchAgents/com.hsy.sidecar.plist"]
PINNED_UNCHANGED = ["wide_shadow/shadow_bundle/config.json", "wide_shadow/shadow_bundle/MANIFEST.json", "wide_shadow/shadow_bundle/slow2026.txt",
                    "wide_shadow/fea171/f10_live_s42_np.npz"]


def sha_b(b): return hashlib.sha256(b).hexdigest()


def sha(p):
    with open(p, "rb") as f: return sha_b(f.read())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("tree"); ap.add_argument("out"); ap.add_argument("--label", required=True)
    ap.add_argument("--home", default=HOME); a = ap.parse_args()
    assert not os.path.exists(a.out), f"refusing to overwrite {a.out}"
    tree = os.path.abspath(a.tree)
    rec_t = json.load(open(f"{tree}/PATCH_RECEIPT.json"))
    assert rec_t.get("m3_v2") and rec_t.get("durable"), "the files-only release is built from a --m3-v2 --durable tree"
    files, unchanged = [], {}
    for root, _, fs in os.walk(tree):
        for f in fs:
            rel = os.path.relpath(os.path.join(root, f), tree)
            if rel == "PATCH_RECEIPT.json" or "__pycache__" in rel or rel.endswith(".pyc"):
                continue
            dest = f"wide_shadow/{rel}"
            raw = open(os.path.join(root, f), "rb").read()
            cur = f"{a.home}/{dest}"
            base = sha(cur) if os.path.exists(cur) else None
            if base == sha_b(raw):
                unchanged[dest] = base; continue
            p = f"{a.out}/files/{dest}"; os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as fh: fh.write(raw)
            os.chmod(p, os.stat(os.path.join(root, f)).st_mode & 0o777)
            files.append({"dest": dest, "candidate_sha256": sha_b(raw), "baseline_sha256": base})
    for u in PINNED_UNCHANGED:
        unchanged[u] = sha(f"{a.home}/{u}")
    moves = []
    for s in K1:
        p = f"{a.home}/{s}"
        assert os.path.isfile(p) and not os.path.islink(p), f"k1 source missing or a symlink: {s}"
        moves.append({"src": s, "dst": f"{ARCHIVE}/{os.path.basename(s)}", "expected_sha256": sha(p)})
    assert not any(it["dest"].startswith("wide_shadow/state/") for it in files), "a files-only package must not carry state"
    C = {"schema": "nc_files_contract_v1", "label": a.label, "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "device_sha256": sha(os.path.abspath(__file__)), "home": a.home, "tree": tree, "tree_receipt_sha256": sha(f"{tree}/PATCH_RECEIPT.json"),
         "files": sorted(files, key=lambda x: x["dest"]), "archive_moves": moves, "unchanged": dict(sorted(unchanged.items())),
         "services": {"stop": ["com.hsy.shadowloop", "com.hsy.combolive", "com.hsy.combosnap", "com.hsy.comboparity"], "not_loaded": ["com.hsy.sidecar"]},
         "forbidden_dest_prefixes": ["wide_shadow/state/"],
         "release_basis": {"statement": "code-only release on top of the NC s42 book: m3_beta_v2 (DESIGN_ret5_single_accessor_2026-09-24) + C durable "
                                        "writes / snapshot retention (lead + user rulings 2026-09-25) + k1 archive; no model or state changes. The NC "
                                        "release's VERDICT=NO_DEPLOY USER_OVERRIDE=053d50f4ab034ca5e311600b10864d0e30046f2aedf2fca369ebecdc8d032b6b "
                                        "still governs the models, which this release does not touch."}}
    os.makedirs(a.out, exist_ok=True)
    with open(f"{a.out}/INSTALL_CONTRACT.json", "w") as fh:          # explicit close: a write error raises (E-0925-A family)
        json.dump(C, fh, indent=1)
    print("NC_PACKAGE_FILES_OK", json.dumps({"files": [(it["dest"], it["candidate_sha256"][:12], (it["baseline_sha256"] or "NEW")[:12]) for it in C["files"]],
                                             "archive_moves": len(moves), "unchanged": len(unchanged),
                                             "contract_sha256": sha(f"{a.out}/INSTALL_CONTRACT.json")}), flush=True)


if __name__ == "__main__":
    main()
