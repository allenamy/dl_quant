#!/usr/bin/env python3
"""ATTR §4 consequence check (docs/PREREG_combo_chain_residual_attribution_2026-09-13.md §4): does H-d (cache left boundary of the full-tail 171 pipeline)
reach the S2 F10 score path? S2 injects I2 (p2_driver.py L10-16, L219: pipeline-skip files mini/data/f8_fea89.npz + dlw_targets E_ts[-1] >= A, so the combo stage's
`need` branch is False and the pipeline never runs). Evidence read here, per S2 arm receipt (RUN_S2_*.json.gz, committed): per-anchor combo wall time
(timing_s.combo; the pipeline takes ~30 s per anchor on pod2 in the G2-C chain, a skipped anchor well under 1 s), and any combo tail line containing the pipeline
trigger text. Descriptive, no gate. Reads local committed receipts only; writes phase2/receipts/ATTR_s2_pipeline_skip.json.
usage: python3 p2_attr_s2_pipeline_skip.py"""
import os, sys, json, gzip, hashlib, glob, stat
HERE = os.path.dirname(os.path.abspath(__file__)); S2 = os.path.join(os.path.dirname(HERE), "receipts", "s2"); OUT = os.path.join(os.path.dirname(HERE), "receipts", "ATTR_s2_pipeline_skip.json")
def gsha(p):
    st = os.stat(p); assert not (st.st_flags & getattr(stat, "SF_DATALESS", 0x40000000)), ("dataless", p)
    b = open(p, "rb").read(); assert len(b) == st.st_size, p; return hashlib.sha256(b).hexdigest()
ARMS = ["RUN_S2_v4_s42", "RUN_S2_v4_s2027", "RUN_S2_A0pred_s42", "RUN_S2_A0pred_s2027", "RUN_S2_v4_s42_pins", "RUN_S2_v4_s42_serveall"]
TRIG = "触发 171"
R = {"device": os.path.basename(__file__), "self_sha256": gsha(os.path.abspath(__file__)), "arms": {}}
for a in ARMS:
    p = f"{S2}/{a}.json.gz"; d = json.load(gzip.open(p)); recs = d["records"]
    ran = [r for r in recs if r.get("combo_rc") is not None]
    ct = [float((r.get("timing_s") or {}).get("combo", float("nan"))) for r in ran]
    trig = [r["anchor"] for r in ran if any(TRIG in str(t) for t in (r.get("combo_tail") or []) + (r.get("combo_err") or []))]
    R["arms"][a] = {"sha256": gsha(p), "n_records": len(recs), "n_combo_ran": len(ran), "combo_s_max": max(ct) if ct else None, "n_combo_s_gt_5": sum(1 for x in ct if x > 5),
                    "n_combo_s_gt_1": sum(1 for x in ct if x > 1), "anchors_tail_with_trigger_text": trig[:20], "n_tail_with_trigger_text": len(trig)}
R["all_arms_no_pipeline_signature"] = all(v["n_combo_s_gt_5"] == 0 and v["n_tail_with_trigger_text"] == 0 for v in R["arms"].values())
json.dump(R, open(OUT, "w"), indent=1)
print("ATTR_S2_PIPELINE_SKIP all_arms_no_pipeline_signature=%s %s" % (R["all_arms_no_pipeline_signature"], json.dumps({k: (v["n_combo_ran"], v["combo_s_max"], v["n_combo_s_gt_1"], v["n_combo_s_gt_5"]) for k, v in R["arms"].items()})))
