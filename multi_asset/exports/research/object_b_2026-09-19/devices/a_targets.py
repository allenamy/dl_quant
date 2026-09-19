#!/usr/bin/env python3
"""Object A targets (PREREG §3 S7, target part only; no prices, no returns): the files the production executor actually traded,
2026-08-26 00Z -> 2026-09-18 20Z (144 anchors), from the frozen archive tar 33910c01 and the per-anchor census A1 (exec final action, file kind,
executor json_sha == archive sha 141/141). Same layout as object B's TARGETS npz, one reading "lit" (the production literal record):
  lit_kind[A] = 2 combo | 1 king (TRADE of that target_live file) | 0 hold (executor HOLD, or no executor action) — the simulator carries the book
  lit_off / lit_idx / lit_val = the traded file's weights on the 829-name panel axis (bundle config 3a8422f3 symbols_panel)
Also per anchor: file sha256 (== the executor's json_sha on TRADE), universe_sha, n_names, gross, exec action / reason, opening_halted is NOT here
(execution-layer flag, stream E). Runs on the Mac (read-only on the repo tar and ~/wide_shadow config); writes targets/ and receipts/TARGETS_A.json.
usage: python3 a_targets.py"""
import os, sys, json, time, tarfile, hashlib, io
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
CPD = os.path.join(os.path.dirname(ROOT), "certified_path_design_2026-09-19", "receipts")
TAR = (os.path.join(CPD, "production_overlap_archive_20260826_20260918.tar.gz"), "33910c01c7ad253d952613cead5ecf627d467126c7bb88598efa36ac4c9e7495")
CENSUS = os.path.join(CPD, "A1_PRODUCTION_OVERLAP_CENSUS.json")
CONFIG = (os.path.expanduser("~/wide_shadow/shadow_bundle/config.json"), "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e")
PANEL_SHA = "381b7f01eedcf31b6d6a94116a32855b545bf584b26f3000aa9545c81068c19a"


def sha_b(b): return hashlib.sha256(b).hexdigest()
def sha(p): return sha_b(open(p, "rb").read())
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def main():
    assert sha(TAR[0]) == TAR[1] and sha(CONFIG[0]) == CONFIG[1]
    cfg = json.load(open(CONFIG[0])); SYMS = list(cfg["symbols_panel"]); assert sha_b("\n".join(SYMS).encode()) == PANEL_SHA
    col = {s: j for j, s in enumerate(SYMS)}
    C = json.load(open(CENSUS)); assert C["archive"]["tar_sha256"] == TAR[1]; rows = C["rows"]; assert len(rows) == 144
    files = {}
    with tarfile.open(TAR[0], "r:gz") as tf:
        for m in tf.getmembers():
            if m.isfile(): files[m.name] = tf.extractfile(m).read()
    kinds, offs, idxs, vals, per = [], [0], [], [], []
    for r in rows:
        A = int(r["anchor"]); act = r.get("exec_final_action"); name = f"target_live/{A}.json"
        rec = {"anchor": iso(A), "exec_action": act, "exec_reason": r.get("exec_final_reason"), "tl_kind": r.get("tl_kind")}
        if act == "TRADE":
            b = files[name]; s = sha_b(b); assert s == r["tl_sha256"], ("archive file != census sha", A)
            assert files[name + ".sha256"].decode().split()[0] == s, ("sidecar", A)
            d = json.loads(b); assert int(d["anchor_ts"]) == A
            w = {k: float(v) for k, v in d["weights"].items()}; assert all(k in col for k in w), ("name outside the panel axis", A)
            j = np.array(sorted(col[k] for k in w), np.int64); v = np.array([w[SYMS[x]] for x in j], np.float64)
            kd = {"combo": 2, "king": 1}[r["tl_kind"]]
            rec.update({"file_sha256": s, "universe_sha": d.get("universe_sha"), "n_names": len(w), "gross": float(np.abs(v).sum()),
                        "producer": d.get("producer"), "f10_sha": d.get("f10_sha"), "booster_sha": d.get("booster_sha")})
        else:
            kd = 0; j = np.zeros(0, np.int64); v = np.zeros(0)
        kinds.append(kd); idxs.append(j.astype(np.int16)); vals.append(v); offs.append(offs[-1] + len(j)); per.append(rec)
    os.makedirs(os.path.join(ROOT, "targets"), exist_ok=True); out = os.path.join(ROOT, "targets", "TARGETS_A_production_overlap.npz")
    np.savez_compressed(out, anchor=np.array([int(r["anchor"]) for r in rows], np.int64), lit_kind=np.array(kinds, np.int8),
                        lit_off=np.array(offs, np.int64), lit_idx=np.concatenate(idxs), lit_val=np.concatenate(vals), symbols=np.array(SYMS))
    cnt = {k: int(sum(1 for x in kinds if x == c)) for k, c in (("combo", 2), ("king", 1), ("hold", 0))}
    doc = {"comparison_type": "(A-lit) production literal record — not a comparison", "prereg": "PREREG_object_B_recipe_oof_and_object_A_paper_2026-09-19.md §3 S7 (target part)",
           "tar_sha256": TAR[1], "census_sha256": sha(CENSUS), "config_sha256": CONFIG[1], "panel_axis_sha256": PANEL_SHA,
           "targets_npz": os.path.relpath(out, ROOT), "targets_npz_sha256": sha(out), "n_anchors": len(rows), "counts": cnt,
           "universe_sha_values": sorted({p.get("universe_sha") for p in per if p.get("universe_sha")}),
           "hold_rule": "kind 0 = executor HOLD or no executor action: the simulator carries the previous book (S7)", "per_anchor": per,
           "self_sha256": sha(os.path.abspath(__file__)), "python": sys.version.split()[0], "numpy": np.__version__, "utc": iso(time.time())}
    json.dump(doc, open(os.path.join(ROOT, "receipts", "TARGETS_A.json"), "w"), indent=1)
    print(json.dumps({k: doc[k] for k in ("n_anchors", "counts", "universe_sha_values", "targets_npz_sha256")}))
    print("holds", [(p["anchor"], p["exec_action"], p["exec_reason"]) for p in per if p["exec_action"] != "TRADE"])


if __name__ == "__main__":
    main()
