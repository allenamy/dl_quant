"""Researcher cell `sidecar_complete_identity_positive`, corrected to the shape pod_f10_refit_v4.py actually writes.
Their fixture put the four inputs at <F>/<role>.bin and the weights at <f8>/model.pt, omitted env_given.SEED /
best_ep_kept / self_sha256, and called the helper with the round-2 five-argument form. Nothing about the FILES was
wrong - only about WHERE they were and WHAT the sidecar declared. Relocate to the canonical layout and re-run."""
import hashlib, json, os, subprocess, sys, tempfile
D = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""): h.update(c)
    return h.hexdigest()
out = {}
for label, canonical in (("researcher_layout_as_written", False), ("same_bytes_at_canonical_paths", True)):
    with tempfile.TemporaryDirectory() as d:
        dlw, f8 = f"{d}/dlw", f"{d}/f8"
        for r in ("dlw/data", "f8/data", "f8/models"): os.makedirs(f"{d}/{r}", exist_ok=True)
        roles = {"targets": "dlw/data/dlw_targets.npz", "fea82": "dlw/data/dlw_fea82.npz", "fea89": "f8/data/f8_fea89.npz", "legs": "f8/data/f10v2_legs.npz"}
        ins = {}
        for k, rel in roles.items():
            p = f"{d}/{rel}" if canonical else f"{d}/{k}.bin"
            open(p, "wb").write(k.encode()); ins[k] = p            # SAME BYTES in both arms
        pt = f"{d}/f8/models/f10_live_s42.pt" if canonical else f"{d}/f8/model.pt"
        open(pt, "wb").write(b"original synthetic weights")
        m = {"seed": 42, "best_ep_rule": "fix7", "env_given": {"F10_DLW": dlw, "F10_OUT": f8, "BEST_EP_FIX": "7"},
             "inputs": ins, "inputs_sha256": {k: sha(p) for k, p in ins.items()}, "pt": pt, "pt_sha256": sha(pt)}
        if canonical: m["best_ep_kept"] = 7; m["env_given"]["SEED"] = "42"; m["self_sha256"] = sha(f"{D}/pod_f10_refit_v4.py")
        sc = f"{d}/f8/models/f10_live_s42.json"; json.dump(m, open(sc, "w"))
        args = f" 42 {D}/pod_f10_refit_v4.py" if canonical else ""
        log = f"{d}/say.log"; open(log, "w").close()
        p = subprocess.run(["/bin/bash", "-c", f". {D}/chain_lib.sh; prereq_refit_sidecar arms refit_s42 {sc} {dlw} {f8}{args}"],
                           capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "L": log, "PY": sys.executable, "R": d})
        out[label] = {"rc": p.returncode, "stderr": p.stderr.strip()[-600:], "chain_log": open(log).read().strip()[-400:]}
print(json.dumps(out, indent=1))
