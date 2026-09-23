#!/usr/bin/env python3
"""FRESH adapter specs — news_adapter_specs.py with the arm/data/combo paths pointed at this agent's FRESH combo files.
price_meta / universe / window_first_anchor are copied byte for byte from the Stage 1 spec, and (when NEW_S's own spec already
exists) asserted equal to NEW_S's, so FRESH and NEW_S enter the adapter through identical price/universe/window settings.
usage: python -B fresh_adapter_specs.py PATH,HOME,LC_CTYPE <fresh_root>"""
import os, sys, json, hashlib
WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
W = sys.argv[2]
N = "/dev/shm/news_2026-09-23"
COPIED = ("price_meta", "universe", "window_first_anchor")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
out = {"device": "fresh_adapter_specs.py", "self_sha256": sha(os.path.abspath(__file__)),
       "prereg": {"path": "docs/PREREG_fresh_models_newS_2026-09-23.md", "commit": "b6e682e0a"}, "specs": {}, "news_spec_agreement": {}}
for seed in ("42", "2027"):
    bp = f"/workspace/old_vs_new_2026-09-23/devices/ADAPTER_SPEC_NEW_s{seed}.json"; base = json.load(open(bp))
    c = f"{W}/work/combo_s{seed}"
    spec = {"arm": f"FRESH_s{seed}", "data": f"FRESH (fresh_2026-09-23) combo_s{seed}: NEW_S producer-replayed features, King monthly folds + F10 all-monthly full-window, seed {seed}",
            "scaled": {"npz": f"{c}/scaled_diagnostic.npz", "sha256": sha(f"{c}/scaled_diagnostic.npz")},
            "lit": {"npz": f"{c}/literal.npz", "sha256": sha(f"{c}/literal.npz")},
            "new_receipt": {"path": f"{c}/TARGET_RECEIPT.json", "sha256": sha(f"{c}/TARGET_RECEIPT.json")},
            "price_meta": base["price_meta"], "universe": base["universe"], "window_first_anchor": base["window_first_anchor"]}
    assert set(spec) == set(base), (sorted(spec), sorted(base))
    np_ = f"{N}/configs/ADAPTER_SPEC_NEWS_s{seed}.json"
    if os.path.exists(np_):
        nb = json.load(open(np_)); agree = {k: (nb.get(k) == spec[k]) for k in COPIED}
        assert all(agree.values()), f"FRESH vs NEW_S adapter spec differs on a copied key: {agree}"
        out["news_spec_agreement"][seed] = {"news_spec": np_, "news_spec_sha256": sha(np_), "identical_keys": list(COPIED)}
    else:
        out["news_spec_agreement"][seed] = {"news_spec": np_, "status": "ABSENT at spec time; copied keys taken from the Stage 1 spec both arms derive from", "stage1_spec": bp, "stage1_spec_sha256": sha(bp)}
    op = f"{W}/configs/ADAPTER_SPEC_FRESH_s{seed}.json"
    json.dump(spec, open(op, "w"), indent=1)
    out["specs"][seed] = {"path": op, "sha256": sha(op)}
    print("spec", seed, json.dumps(spec)[:300], flush=True)
json.dump(out, open(f"{W}/receipts/engine/FRESH_ADAPTER_SPECS.json", "w"), indent=1)
print("FRESH_ADAPTER_SPECS VERDICT=PASS", json.dumps(out["specs"]), flush=True)
