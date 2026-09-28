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
ARM = sys.argv[4]   # DLARCH: the arm name is PASSED IN so it has exactly one source of truth
                    # (dlarch_chain_run). It used to be rebuilt as f"DLARCH_T0_s{seed}" here and in
                    # three other places; the copies drifted the moment a second arm existed
                    # (--reference), and bt_objb_targets caught it as arm_mismatch.
for seed in [sys.argv[3]]:
    base = json.load(open("/workspace/old_vs_new_2026-09-23/devices/ADAPTER_SPEC_NEW_s42.json"))
    _b2 = json.load(open("/workspace/old_vs_new_2026-09-23/devices/ADAPTER_SPEC_NEW_s2027.json"))
    for _k in ("price_meta", "universe", "window_first_anchor"):
        assert json.dumps(base[_k], sort_keys=True) == json.dumps(_b2[_k], sort_keys=True), \
            f"DLARCH: base spec field {_k} is NOT seed-independent; using s42 for all seeds would be wrong"
    c = f"{W}/work/combo_s{seed}"
    spec = {"arm": ARM, "data": f"NEW_S2 (nc_2026-09-23 features, news2_2026-09-23 models) combo_s{seed}: sealed NC liquidity-blend configuration, fixed King + F10 s{seed}, not retrained",
            "scaled": {"npz": f"{c}/scaled_diagnostic.npz", "sha256": sha(f"{c}/scaled_diagnostic.npz")},
            "lit": {"npz": f"{c}/literal.npz", "sha256": sha(f"{c}/literal.npz")},
            "new_receipt": {"path": f"{c}/TARGET_RECEIPT.json", "sha256": sha(f"{c}/TARGET_RECEIPT.json")},
            "price_meta": base["price_meta"], "universe": base["universe"], "window_first_anchor": base["window_first_anchor"]}
    assert set(spec) == set(base), (sorted(spec), sorted(base))
    json.dump(spec, open(f"{W}/configs/ADAPTER_SPEC_{ARM}.json", "w"), indent=1)
    print("spec", seed, json.dumps(spec)[:300])
