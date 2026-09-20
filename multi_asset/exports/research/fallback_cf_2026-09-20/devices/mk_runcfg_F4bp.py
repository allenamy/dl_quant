#!/usr/bin/env python3
"""mk_runcfg_F4bp.py — a SEPARATE frozen run config for the F4b′ arm only.

It does NOT touch RUN_CONFIG_fallback_cf_F_2026-09-20.json, whose sha is already cited in receipts and in the result doc: a frozen
config must stay frozen. This one inherits every pin, the window, nav0, paths_R and the production config from it byte-for-byte and
changes only the single run entry, so F4b′'s 32 paths are produced by exactly the judge that produced the other four arms' paths.

F4b′ IS NOT THE PREREG'S F4 AS WRITTEN — it renormalises the masked seat (the way combo_stage L232-233 does) where §2 says
"不改席位". That reading is the lead's to rule on. Until then its outputs carry the arm label F4bp and must not be reported as F4.
usage: mk_runcfg_F4bp.py
"""
import hashlib, json, os, time

OUT = "/workspace/fallback_cf_2026-09-20"
BASE = f"{OUT}/RUN_CONFIG_fallback_cf_F_2026-09-20.json"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


C = json.load(open(BASE))
npz = f"{OUT}/work/TARGETS_F4bp_A0_main.npz"; rcp = f"{OUT}/receipts/TARGETS_F4bp_A0_main.json"
for p in (npz, rcp):
    assert os.path.exists(p), f"F4b′ targets not built yet: {p}"
tmpl = C["runs"][0]
C["runs"] = [{"arm": "OBJB_F4bp", "events": "rule", "price": "raw", "policy": "UA-FREEZE-EXCLUDE", "ua_set": "UNAVAILABLE_3084",
              "tag": "OBJB_F4bp|scaled|rule|raw|UAFE", "book": "scaled",
              "targets": {"source": "objb", "reading": "scaled", "arm": "A0",
                          "sources": [{"npz": npz, "npz_sha256": sha(npz), "receipt": rcp, "receipt_sha256": sha(rcp)}],
                          "universe": dict(tmpl["targets"]["universe"])},
              "role": "PREREG F-family §2 F4 reading b′ — rev24 removed AND the masked seat renormalised the way production itself "
                      "does it (combo_stage L232-233). NOT the prereg's F4 as literally written; pending the lead's ruling it may not be "
                      "reported as F4. Differs from F4a (= kc) by FTRIM alone."}]
C["config"] = "RUN_CONFIG_fallback_cf_F4bp_2026-09-20"
C["status"] = ("FROZEN before any F4b′ number exists (targets built and structurally asserted first: receipts/TARGETS_F4bp_GATE.json). "
               "Every pin, the window and the production config are inherited byte-for-byte from the four-arm config below.")
C["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
C["inherited_from"] = {"path": BASE, "sha256": sha(BASE), "rule": "only `runs`, `config`, `status`, `created_utc` differ"}
C["frozen_by"] = {"device": "fcf_targets_F4bp.py", "receipt": f"{OUT}/receipts/TARGETS_F4bp_GATE.json",
                  "receipt_sha256": sha(f"{OUT}/receipts/TARGETS_F4bp_GATE.json")}
p = f"{OUT}/RUN_CONFIG_fallback_cf_F4bp_2026-09-20.json"
json.dump(C, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p)
print("wrote", p, "sha256", sha(p), "| inherited from", os.path.basename(BASE), sha(BASE)[:16])
