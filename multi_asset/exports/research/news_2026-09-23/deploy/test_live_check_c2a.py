"""Red/green for news_live_check.fetch_coverage (C2a) on a real snapshot's venue list: production config (450) must be RED naming the
unfetched TRADING crypto axis names; fetch = expected must be GREEN; expected minus one name must be RED naming exactly that name."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.expanduser("~/cc_tmp/news_20260923/deploy"))
import news_live_check as L
A = int(sys.argv[1]); WS = os.path.expanduser("~/wide_shadow")
aux = json.load(open(f"{WS}/state/snap/{A}/aux.json")); cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]
crypto = np.load(os.path.expanduser("~/cc_tmp/news_20260923/package_NEW_S/crypto_P1_members_2025H2on.npz"))["crypto"].astype(bool)
m0, x0, n = L.fetch_coverage(aux["base_syms"], syms, crypto, cfg["symbols_live"])
exp = sorted(set(cfg["symbols_live"]) | set(m0)) ; exp = [s for s in exp if s not in x0]
m1, _, _ = L.fetch_coverage(aux["base_syms"], syms, crypto, exp)
drop = m0[0] if m0 else None; m2, _, _ = L.fetch_coverage(aux["base_syms"], syms, crypto, [s for s in exp if s != drop])
added = json.load(open(os.path.expanduser("~/cc_tmp/news_20260923/package_NEW_S/added_names.json")))
r = {"anchor": A, "expected_n": n, "RED_production_450": {"missing_n": len(m0), "missing_first": m0[:10], "fetched_not_expected": x0},
     "GREEN_fetch_eq_expected": {"missing_n": len(m1)}, "RED_minus_one": {"dropped": drop, "missing": m2},
     "missing_vs_NEW_S_added72": {"in_missing_not_in_added": sorted(set(m0) - set(added)), "in_added_not_in_missing": sorted(set(added) - set(m0))}}
r["PASS"] = len(m0) > 0 and len(m1) == 0 and m2 == [drop]
print(json.dumps(r)); sys.exit(0 if r["PASS"] else 3)
