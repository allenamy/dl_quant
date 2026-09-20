#!/usr/bin/env python3
"""bt_approved_inputs.py — builds the APPROVED INPUTS table that bt_gate_external.py binds to (round-6 review R6-02).

The table is not a copy of what a receipt says: every entry is re-hashed FROM ITS OWN PATH here, and the three frozen run configs (A0, A0ext,
V4) must AGREE on every pin they share and on the economics block — a disagreement is a refusal, not a merge. The economics block
(current_production_config + nav0_usdt + paths_R) is hashed as one unit so no single field (initial cash, gross multiplier, chase weights)
can be changed silently. The table is then committed in the research repo, so the gate compares against git history rather than against files
that live next to the artefacts it is checking.
usage: /workspace/venv/bin/python -B bt_approved_inputs.py PATH,HOME,LC_CTYPE <out.json> <config.json> [<config.json> ...]
"""
import os, sys, json, time, hashlib

if __name__ == "__main__":
    WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
    assert WL, "env whitelist (argv[1]) must be non-empty"
    extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"

OUT, CFGS = sys.argv[2], sys.argv[3:]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def canon(o): return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


inputs, econ, seen_econ = {}, None, {}
for cp in CFGS:
    C = json.load(open(cp)); nm = os.path.basename(cp)
    e = {"current_production_config": C["current_production_config"], "nav0_usdt": C["nav0_usdt"], "paths_R": C["paths_R"]}
    seen_econ[nm] = hashlib.sha256(canon(e).encode()).hexdigest()
    econ = econ or e
    for k, v in C["pins"].items():
        if "path" not in v or "sha256" not in v: continue
        got = sha(v["path"])
        assert got == v["sha256"], f"{nm} pin {k}: the file does not match the config's own sha ({got[:16]} vs {v['sha256'][:16]})"
        if k in inputs:
            assert inputs[k]["path"] == v["path"] and inputs[k]["sha256"] == got, f"configs disagree on pin {k}"
        else:
            inputs[k] = {"path": v["path"], "sha256": got, "first_seen_in": nm}
    for r in C["runs"]:
        for s in (r.get("targets") or {}).get("sources", []):
            for kind, pth, want in (("npz", s["npz"], s["npz_sha256"]), ("receipt", s["receipt"], s["receipt_sha256"])):
                got = sha(pth); assert got == want, f"{nm} target {pth}: file sha != the config's own ({got[:16]} vs {want[:16]})"
                key = "targets_" + os.path.basename(pth).replace("TARGETS_", "").replace(".npz", "_npz").replace(".json", "_receipt")
                if key in inputs: assert inputs[key]["sha256"] == got, f"configs disagree on {key}"
                else: inputs[key] = {"path": pth, "sha256": got, "first_seen_in": nm}
assert len(set(seen_econ.values())) == 1, f"the configs do not share one economics block: {seen_econ}"
out = {"device": "bt_approved_inputs.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "built_from_configs": {os.path.basename(c): sha(c) for c in CFGS},
       "rule": "every entry re-hashed from its own path here; the configs must agree on every shared pin and on the economics block",
       "economics": dict(econ, sha256=list(seen_econ.values())[0]), "pin_role": {}, "inputs": inputs}
json.dump(out, open(OUT, "w"), indent=1, ensure_ascii=False)
print("BT_APPROVED_INPUTS wrote", OUT, sha(OUT)[:16], "| inputs:", len(inputs), "| economics sha", out["economics"]["sha256"][:16], "| configs:", len(CFGS))
