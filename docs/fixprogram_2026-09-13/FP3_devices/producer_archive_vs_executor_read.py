#!/usr/bin/env python3
"""FP3 item C, part 1 (2026-09-17): for EVERY live anchor since the combo switch, is the producer's archived target file the file the executor read
and traded? Read-only. Sources: executor LIVE ledger rows (state/live/pilot_log/*/anchors.jsonl, book_source == external) carry the target's
json_sha / weights_sha / booster_sha / universe_sha / f10_sha / path / age; the producer archive (~/wide_shadow/state/target_live/<A>.json + .sha256,
state/weights_combo/<A>.npz). Checks per anchor: (a) sha256(archived json bytes NOW) == ledger json_sha == sidecar; (b) archived doc.weights_sha ==
ledger weights_sha == sha256(weights_combo/<A>.npz bytes); (c) booster/universe sha equal; (d) doc.anchor_ts == A == ledger nominal. Any mismatch
is listed by anchor; the verdict is the count of anchors with all four identities, over the count of external rows. Not a replay: it does not say
the producer would write the same file again (that is part 2, the snapshot + sandbox replay)."""
import glob, hashlib, json, os, sys, time
HOME = os.path.expanduser("~"); LED = f"{HOME}/dl_quant_live/state/live/pilot_log"; WS = f"{HOME}/wide_shadow/state"
OUT = sys.argv[1] if len(sys.argv) > 1 else "PRODUCER_ARCHIVE_VS_EXECUTOR_READ.json"
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
rows = []
for f in sorted(glob.glob(f"{LED}/*/anchors.jsonl")):
    for l in open(f):
        if not l.strip(): continue
        r = json.loads(l)
        if r.get("book_source") == "external" and isinstance(r.get("external_book"), dict): rows.append((f, r))
per = []; n_ok = 0; first = None; last = None
for f, r in rows:
    eb = r["external_book"]; A = eb.get("anchor_ts") or eb.get("nominal_ts"); rec = {"anchor_ts": A, "ledger": os.path.relpath(f, LED), "executor_ok": eb.get("ok"), "reason": eb.get("reason"), "age_s": eb.get("age_s"), "producer": (eb.get("producer") or "")[:40]}
    if not A: rec["why"] = ["ledger row has no anchor_ts"]; per.append(rec); continue
    A = int(A); first = A if first is None else min(first, A); last = A if last is None else max(last, A)
    p = f"{WS}/target_live/{A}.json"; w = f"{WS}/weights_combo/{A}.npz"; why = []
    if not os.path.isfile(p): why.append("archived target json missing")
    else:
        js = sha(p); side = open(p + ".sha256").read().split()[0] if os.path.isfile(p + ".sha256") else None; doc = json.load(open(p))
        rec.update({"json_sha_now": js[:16], "json_sha_ledger": (eb.get("json_sha") or "")[:16], "sidecar": (side or "")[:16], "doc_weights_sha": (doc.get("weights_sha") or "")[:16], "ledger_weights_sha": (eb.get("weights_sha") or "")[:16], "doc_f10_sha": (doc.get("f10_sha") or None), "ledger_f10_sha": eb.get("f10_sha")})
        if js != eb.get("json_sha"): why.append("json bytes now != what the executor validated (json_sha)")
        if side != js: why.append("sidecar != json bytes now")
        if doc.get("anchor_ts") != A: why.append(f"doc.anchor_ts {doc.get('anchor_ts')} != {A}")
        if doc.get("weights_sha") != eb.get("weights_sha"): why.append("doc.weights_sha != ledger weights_sha")
        if os.path.isfile(w):
            ws = sha(w); rec["weights_npz_sha"] = ws[:16]
            if ws != doc.get("weights_sha"): why.append("weights_combo npz bytes != doc.weights_sha")
        else: rec["weights_npz_sha"] = None; why.append("weights_combo/<A>.npz missing (pre-combo king form or not archived)")
        for k in ("booster_sha", "universe_sha"):
            if doc.get(k) != eb.get(k): why.append(f"{k}: doc {str(doc.get(k))[:8]} != ledger {str(eb.get(k))[:8]}")
        if doc.get("f10_sha") != eb.get("f10_sha"): why.append(f"f10_sha: doc {str(doc.get('f10_sha'))[:8]} != ledger {str(eb.get('f10_sha'))[:8]}")
    rec["why"] = why; per.append(rec); n_ok += (not why)
by_why = {}
for r in per:
    for wv in r["why"]: by_why[wv] = by_why.get(wv, 0) + 1
out = {"device": "producer_archive_vs_executor_read.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "n_external_rows": len(rows), "anchor_first": first, "anchor_last": last,
       "n_all_identities_hold": n_ok, "n_with_mismatch": len(per) - n_ok, "mismatch_kinds": by_why, "per_anchor": per,
       "reads": "executor ledger rows are what the executor wrote at trade time; archive bytes are read NOW; a match means the file the executor validated is still the archived one, byte for byte, and its weights npz matches its declared sha"}
json.dump(out, open(OUT, "w"), indent=1)
print(f"external rows {len(rows)} anchors {first}..{last}; all identities hold {n_ok}/{len(per)}; mismatch kinds {by_why}")
for r in per:
    if r["why"]: print("  ", r["anchor_ts"], r["ledger"], r["why"][:3])
