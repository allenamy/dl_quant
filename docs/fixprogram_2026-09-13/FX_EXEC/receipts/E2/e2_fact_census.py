"""E2 fact census (read-only; census copy of ~/dl_quant_live/state taken 2026-09-13T13:04:09Z).
Top-up request ledgers: how many requests exist, how many carry a re-query identity contradiction, how many are
origQty-kind (the only trace the OLD direct GET path could leave: the 6->8 direction was an identity contradiction;
the 8->6 direction was ACCEPTED silently and leaves no trace at all)."""
import json, glob, collections, sys
P = sys.argv[1] if len(sys.argv) > 1 else "/Users/haosiyu/cc_tmp/fx_exec_census"
n_rows = n_req = 0; kinds = collections.Counter(); ex = []
per_day = collections.Counter()
for f in sorted(glob.glob(P + "/pilot_log/*/orders.jsonl")):
    for ln in open(f, errors="replace"):
        try: o = json.loads(ln)
        except Exception: continue
        if not isinstance(o, dict) or o.get("order_type") != "topup_taker" or o.get("submit_ts") is None: continue
        n_rows += 1
        for r in (o.get("request_ledger") or ()):
            if not isinstance(r, dict): continue
            n_req += 1; per_day[f.split("/")[-2]] += 1
            inc = str(r.get("inconsistent") or "")
            if not inc: continue
            k = ("re-query identity" if "re-query identity" in inc else ("submit identity" if "submit identity" in inc else "other"))
            k2 = "origQty" if "origQty" in inc else "non-origQty"
            kinds[(k, k2)] += 1
            if len(ex) < 8: ex.append((f.split("/")[-2], o.get("symbol"), inc[:160]))
print("sent top-up rows:", n_rows, "requests in their ledgers:", n_req, "first/last day with requests:", (min(per_day), max(per_day)) if per_day else None)
print("requests carrying `inconsistent`, by (gate, kind):", dict(kinds))
for e in ex: print("  e.g.", e)
