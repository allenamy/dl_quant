#!/usr/bin/env python3
"""NEWS adapter specs: Stage 1 ADAPTER_SPEC_NEW_s* with ONLY arm / data / scaled / lit / new_receipt replaced by this agent's combo files
(price_meta, universe and window_first_anchor copied from the Stage 1 spec byte for byte)."""
import os, sys, json, hashlib
WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
W = sys.argv[2]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
for seed in ("42", "2027"):
    base = json.load(open(f"/workspace/old_vs_new_2026-09-23/devices/ADAPTER_SPEC_NEW_s{seed}.json"))
    c = f"{W}/work/combo_s{seed}"
    spec = {"arm": f"NEWS2_s{seed}", "data": f"NEW_S2 (nc_2026-09-23 features, news2_2026-09-23 models) combo_s{seed}: full corrected producer contract, King + F10 s{seed} retrained",
            "scaled": {"npz": f"{c}/scaled_diagnostic.npz", "sha256": sha(f"{c}/scaled_diagnostic.npz")},
            "lit": {"npz": f"{c}/literal.npz", "sha256": sha(f"{c}/literal.npz")},
            "new_receipt": {"path": f"{c}/TARGET_RECEIPT.json", "sha256": sha(f"{c}/TARGET_RECEIPT.json")},
            "price_meta": base["price_meta"], "universe": base["universe"], "window_first_anchor": base["window_first_anchor"]}
    assert set(spec) == set(base), (sorted(spec), sorted(base))
    json.dump(spec, open(f"{W}/configs/ADAPTER_SPEC_NEWS2_s{seed}.json", "w"), indent=1)
    print("spec", seed, json.dumps(spec)[:300])
