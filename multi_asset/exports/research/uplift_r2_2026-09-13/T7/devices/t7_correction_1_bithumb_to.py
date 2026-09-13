#!/usr/bin/env python3
"""t7_correction_1_bithumb_to.py — CORRECTION 1 to RESULT_T7_feasibility (committed fbf36ffd): what Bithumb returns for a `to` spelled with 'Z' or '+09:00'.
The committed RESULT said 'HTTP 200 + empty list (silent empty)'. PROBE_A's JSON could not tell a non-list body from an empty list (both became newest_open_utc = None,
and the body was saved only for non-200 responses). The HTTP log of the same requests keeps short bodies. Sources:
(1) receipts/http_log_probe_a.jsonl (07:46Z original probe); (2) receipts/http_log_correction1_bithumb_to_recheck.jsonl = the full pull's run-start negative `to` control
request line(s) copied from /Users/haosiyu/cc_tmp/krw_pull/logs/http_bithumb.jsonl (09:18Z, independent live recheck; that log stores bodies only for non-200, so the body is identified by sha256 and by
receipts/controls_bithumb_pull_run1_correction1.jsonl, the pull's control record, which keeps the body head).
Found by that negative control in the pull's test run, which expected [] and received an error body (the test worker aborted before any data request)."""
import os, json
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R = T7 + "/receipts"
def classify(r):
    head = r.get("body_head")
    if head is None: return "LIST_OR_UNSAVED_BODY(body_len=%d)" % r["body_len"]
    try: js = json.loads(head)
    except Exception: return "UNPARSEABLE_HEAD"
    if isinstance(js, list): return "LIST(n=%d)" % len(js)
    return "ERROR_BODY: " + json.dumps(js, ensure_ascii=False)
out = {"device": os.path.basename(__file__), "original_probe": [], "recheck_pull_control": []}
for l in open(R + "/http_log_probe_a.jsonl"):
    r = json.loads(l)
    if r["tag"].startswith("bithumb_to_"):
        out["original_probe"].append({"utc": r["utc"], "tag": r["tag"], "url": r["url"], "status": r["status"], "body_len": r["body_len"], "body_sha256": r["body_sha256"], "body": classify(r)})
for l in open(R + "/http_log_correction1_bithumb_to_recheck.jsonl"):
    r = json.loads(l)
    out["recheck_pull_control"].append({"utc": r["utc"], "url": r["url"], "status": r["status"], "body_len": r["body_len"], "body_sha256": r["body_sha256"], "body": classify(r)})
ERR_SHA = {x["body_sha256"] for x in out["original_probe"] if x["body"].startswith("ERROR_BODY")}
ctl = [json.loads(l) for l in open(R + "/controls_bithumb_pull_run1_correction1.jsonl")]   # the pull's own control record keeps the body head
for x in out["recheck_pull_control"]:
    if x["body"].startswith("LIST_OR_UNSAVED") and x["body_sha256"] in ERR_SHA:
        x["body"] = "ERROR_BODY (sha256 identical to the original probe's error body); control record body_head: " + ctl[0]["neg_to"].get("body_head", "")
errs = [x for x in out["original_probe"] + out["recheck_pull_control"] if x["body"].startswith("ERROR_BODY")]
out["finding"] = {"n_error_body_responses": len(errs), "distinct_error_bodies": sorted({x["body"] for x in errs}), "distinct_error_body_sha256": sorted({x["body_sha256"] for x in errs}),
                  "corrected_fact": "Bithumb v1 candles: a `to` spelled with 'Z' or '+09:00' returns HTTP 200 + {\"error\":{\"name\":400,\"message\":\"Invalid parameter. Check the given value!\"}} (an error body, NOT an empty list); the naive KST spelling works",
                  "wrong_fact_as_committed": "HTTP 200 + empty list (silent empty)"}
json.dump(out, open(R + "/CORRECTION_1_bithumb_to_spelling.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(out["finding"], indent=1, ensure_ascii=False))
for x in out["original_probe"] + out["recheck_pull_control"]: print(x.get("tag", "pull_control"), x["utc"], x["status"], x["body_len"], x["body"][:90])
