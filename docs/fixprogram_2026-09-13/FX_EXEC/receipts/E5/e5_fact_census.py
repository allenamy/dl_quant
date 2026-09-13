"""E5 fact census (READ-ONLY on ~/dl_quant_live/state/live/pilot_log/*/orders.jsonl): every persisted request-level `inconsistent`
string and every row-level `ledger_inconsistent` entry — how many carry origQty pairs, how many reasons, whether each reason has
exactly one pair, whether the pairs agree, and whether each row-level origQty entry equals its request's str(inconsistent)[:120]."""
import collections, glob, json, os, re, sys
sys.path.insert(0, "/Users/haosiyu/cc_tmp/fx_exec/live")
import reconcile as RC
C = collections.Counter(); ex = collections.defaultdict(list)
files = sorted(glob.glob(os.path.expanduser("~/dl_quant_live/state/live/pilot_log/*/orders.jsonl")))
for f in files:
    for l in open(f):
        if not l.strip(): continue
        try: o = json.loads(l)
        except ValueError: C["unparseable_row"] += 1; continue
        reqs = [r for r in (o.get("request_ledger") or ()) if isinstance(r, dict)]
        if reqs: C["rows_with_ledger"] += 1
        req_inc = {}
        for r in reqs:
            inc = r.get("inconsistent")
            if not inc: continue
            C["request_inconsistent"] += 1
            s = str(inc); req_inc[r.get("client_id")] = s
            pairs = RC._ORIGQTY_PAIR.findall(s)
            if pairs: C["request_with_origqty_pair"] += 1
            parts = [p.strip() for p in s.split(";") if p.strip()]
            C[f"request_parts_{min(len(parts), 3)}"] += 1
            if len(pairs) > 1:
                C["request_multi_pair"] += 1; ex["multi_pair"].append((os.path.basename(os.path.dirname(f)), o.get("symbol"), s[:200]))
            if pairs and any(len(RC._ORIGQTY_PAIR.findall(p)) != 1 for p in parts if RC._is_identity_origqty_kind(p)):
                C["request_reason_not_exactly_one_pair"] += 1
            if len({tuple(p) for p in pairs}) > 1:
                C["request_pairs_disagree"] += 1
            if RC._is_identity_origqty_kind(s):
                C["request_origqty_kind"] += 1; ex["origqty_kind"].append((os.path.basename(os.path.dirname(f)), o.get("symbol"), r.get("client_id"), s[:160]))
        for e in (o.get("ledger_inconsistent") or ()):
            cid, why = (e.get("client_id"), e.get("why")) if isinstance(e, dict) else (None, e)
            C["row_entry"] += 1
            if RC._is_identity_origqty_kind(why):
                C["row_entry_origqty_kind"] += 1
                if cid in req_inc and str(why) == req_inc[cid][:120]: C["row_entry_origqty_equals_request_copy"] += 1
                else: C["row_entry_origqty_NOT_equal_request_copy"] += 1; ex["row_not_equal"].append((o.get("symbol"), cid, str(why)[:160]))
print("files", len(files), "first", files[0].split("/")[-2] if files else None, "last", files[-1].split("/")[-2] if files else None)
print(json.dumps(dict(C), indent=1, sort_keys=True))
for k, v in ex.items(): print(k, len(v), v[:6])
