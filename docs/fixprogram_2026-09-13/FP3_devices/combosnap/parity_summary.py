#!/usr/bin/env python3
"""Aggregate the per-anchor parity receipts (state/snap/<A>/PARITY.json) into one receipt: anchors, verdicts, weight diffs, version deltas, gaps in the
anchor sequence (anchors with a snapshot but no receipt, and 4h slots without a snapshot). Read-only. usage: parity_summary.py <out.json>"""
import glob, json, os, sys, time, hashlib
S = os.path.expanduser("~/wide_shadow/state/snap"); OUT = sys.argv[1]; PF = os.environ.get("PARITY_FILE", "PARITY.json")   # v2 receipts: PARITY_FILE=PARITY_v2.json
snaps = sorted(int(os.path.basename(d)) for d in glob.glob(f"{S}/1[0-9]*") if os.path.isdir(d))
rows = []
for A in snaps:
    p = f"{S}/{A}/{PF}"; c = os.path.isfile(f"{S}/{A}/COMPLETE")
    if os.path.isfile(p):
        j = json.load(open(p)); rows.append({"anchor_ts": A, "utc": time.strftime("%m-%d %HZ", time.gmtime(A)), "snapshot_complete": c, "VERDICT": j.get("VERDICT"), "weights": j.get("weights"), "version_delta": j.get("version_delta"), "why": j.get("why"), "anchor_identity_ok": (j.get("anchor_identity") or {}).get("archived") == A if j.get("anchor_identity") else None, "receipt_sha16": hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]})
    else: rows.append({"anchor_ts": A, "utc": time.strftime("%m-%d %HZ", time.gmtime(A)), "snapshot_complete": c, "VERDICT": None})
missing_slots = [time.strftime("%m-%d %HZ", time.gmtime(t)) for t in range(snaps[0], snaps[-1] + 1, 14400) if t not in set(snaps)] if snaps else []
out = {"device": "parity_summary.py", "parity_file": PF, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "n_snapshots": len(snaps), "first": rows[0]["utc"] if rows else None, "last": rows[-1]["utc"] if rows else None, "n_parity": sum(1 for r in rows if r["VERDICT"] == "PARITY"), "n_mismatch": sum(1 for r in rows if r["VERDICT"] == "MISMATCH"), "n_no_receipt": sum(1 for r in rows if r["VERDICT"] is None), "missing_4h_slots": missing_slots, "rows": rows,
       "reads": "single-step combo parity per anchor (archived king input + snapshotted rolling state → combo_stage in a sandbox); NOT the continuous production-path replay"}
json.dump(out, open(OUT, "w"), indent=1); print({k: out[k] for k in ("n_snapshots", "first", "last", "n_parity", "n_mismatch", "n_no_receipt", "missing_4h_slots")})
