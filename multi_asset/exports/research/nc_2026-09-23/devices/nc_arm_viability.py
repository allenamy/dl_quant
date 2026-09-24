"""Arm viability (lead 2026-09-23, after news2 ARM_VIABILITY.json): every single-family test arm of nc_derive_producer.py must run the
replay's King block (pass 1) and the F10 mini block (pass 2) on one anchor without error, now that the replay capture reads
c7 := fin5.sum(0) (defined in every arm) instead of the D5/D6 screen's c7. One subprocess per arm (set_tree is module state).
Each arm row records: families, tree receipt sha, pass-1 members / King features, pass-2 X82 / X89 shapes, or the exception.
usage: python nc_arm_viability.py <out json> <anchor> <arm name>=<tree dir> ...   (env NC_W, NC_CFG; members history from work/)"""
import os, sys, json, subprocess, hashlib

HERE = os.path.dirname(os.path.abspath(__file__)); W = os.environ.get("NC_W", "/dev/shm/nc_2026-09-23")
CFG = os.environ.get("NC_CFG", f"{W}/inputs/bundle_config.json")

CHILD = r'''
import sys, json, traceback, numpy as np
sys.path.insert(0, @@HERE@@)
import nc_hist_features as H
out = {"arm": @@ARM@@}
try:
    H.set_tree(@@TREE@@); I = H.Inputs(); cfg = json.load(open(@@CFG@@)); P = cfg["params"]
    r = H.pass1_anchor(I, @@A@@, P, cfg, H._king_block())
    out["pass1"] = {"members": None if r.get("members") is None else int(len(r["members"])), "king": bool(r.get("king")),
                    "n_legal": int(r.get("n_legal", -1)) if r.get("n_legal") is not None else None}
    mh = np.load(@@W@@ + "/work/members_hist_all.npz"); MH = {int(a): mh["idx"][mh["off"][i]:mh["off"][i + 1]].astype(np.int64) for i, a in enumerate(mh["anchors"])}
    wk = @@W@@ + "/scratch/armviab_" + @@ARM@@; import os; os.makedirs(wk, exist_ok=True)
    r2 = H.pass2_anchor(I, @@A@@, MH, wk, H._mini_block(), H._combo_funcs())
    out["pass2"] = {"X82": list(np.asarray(r2["X82"]).shape), "X89": list(np.asarray(r2["X89"]).shape), "n_keep": int(r2["n_keep"])}
    out["status"] = "OK"
    import shutil; shutil.rmtree(wk, ignore_errors=True)            # /dev/shm is shared with news2's chain: leave nothing behind
except Exception as e:
    out["status"] = "ERROR"; out["error"] = type(e).__name__ + ": " + str(e)[:300]; out["trace"] = traceback.format_exc()[-800:]
print("ARM_ROW " + json.dumps(out))
'''


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    out, A = sys.argv[1], int(sys.argv[2]); arms = [x.split("=", 1) for x in sys.argv[3:]]
    rows = []
    for name, tree in arms:
        rec = json.load(open(f"{tree}/PATCH_RECEIPT.json"))
        code = CHILD
        for tok, val in (("@@HERE@@", repr(HERE)), ("@@TREE@@", repr(tree)), ("@@CFG@@", repr(CFG)), ("@@A@@", str(A)), ("@@ARM@@", repr(name)), ("@@W@@", repr(W))):
            assert tok in code, ("placeholder absent from the child source", tok)
            code = code.replace(tok, val)
        assert "@@" not in code and 'print("ARM_ROW "' in code, "substitution damaged the child source"
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=dict(os.environ))
        line = [l for l in p.stdout.splitlines() if l.startswith("ARM_ROW ")]
        row = json.loads(line[-1][8:]) if line else {"arm": name, "status": "NO_ROW", "rc": p.returncode, "stderr": p.stderr[-600:]}
        row.update({"families": rec.get("news2_families"), "tree_receipt_sha256": sha(f"{tree}/PATCH_RECEIPT.json"), "rc": p.returncode})
        rows.append(row); print(name, row["status"], row.get("error", ""), flush=True)
    rec = {"anchor": A, "device_sha256": sha(os.path.abspath(__file__)), "replay_device_sha256": sha(f"{HERE}/nc_hist_features.py"),
           "rows": rows, "all_ok": all(r["status"] == "OK" for r in rows)}
    json.dump(rec, open(out, "w"), indent=1)
    print("ARM_VIABILITY", "ALL_OK" if rec["all_ok"] else "NOT_ALL_OK", flush=True)


if __name__ == "__main__":
    main()
