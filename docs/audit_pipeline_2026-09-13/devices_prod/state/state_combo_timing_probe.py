#!/usr/bin/env python3
"""state_combo_timing_probe.py -- AUDIT_PROD item 4/S5, READ-ONLY on ~/wide_shadow.
Per anchor since combo went live (2026-08-26 04:00Z): producer king-file write time (state/target_live_king/{A}.json
'written_utc'), combo rewrite time (state/target_live/{A}.json 'written_utc' when producer starts with combo_stage), and the
combo daemon end line in fea171/combo_live.log. Margins against the combo hard deadline N+22:40 (combo_stage.py L321-323,
A+1360 s) and the daemon's silent-skip threshold N+22:35 (combo_live_daemon.sh L32-34, now-A > 1355 s), and against the
executor read at N+24 (dl_quant_live config/book.json external_book.anchor_offset_min = 24).
Usage (Mac, outside anchor windows): env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B \
  docs/audit_pipeline_2026-09-13/devices_prod/state/state_combo_timing_probe.py PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING,PYTHONDONTWRITEBYTECODE
"""
import os, sys, json, time, hashlib, glob, re, datetime
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "env whitelist argv[1] required"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
WS = "/Users/haosiyu/wide_shadow"; REPO = "/Users/haosiyu/Desktop/quant_research"
OUT = f"{REPO}/docs/audit_pipeline_2026-09-13/receipts_prod/state_combo_timing_probe.json"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ts(s): return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()
def U(t): return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%d %H:%MZ")
LOGP = f"{WS}/fea171/combo_live.log"
SRC = {"combo_live_log": LOGP, "combo_stage": f"{WS}/fea171/combo_stage.py", "combo_live_daemon": f"{WS}/fea171/combo_live_daemon.sh",
       "executor_book_json": "/Users/haosiyu/dl_quant_live/config/book.json"}
SHA0 = {k: sha(p) for k, p in SRC.items()}
book = json.load(open(SRC["executor_book_json"])); exec_off = int(book["external_book"]["anchor_offset_min"])
ends = {}
for m in re.finditer(r"=== combo_live anchor=(\d+) rc=(\d+) (.+)", open(LOGP).read()):
    A = int(m.group(1)); ends[A] = (int(m.group(2)), datetime.datetime.strptime(m.group(3).strip(), "%a %b %d %H:%M:%S UTC %Y").replace(tzinfo=datetime.timezone.utc).timestamp())
rows = []
for p in sorted(glob.glob(f"{WS}/state/target_live/*.json")):
    d = json.load(open(p)); A = int(d["anchor_ts"])
    if A < 1787716800: continue
    kp = f"{WS}/state/target_live_king/{A}.json"
    k_w = ts(json.load(open(kp))["written_utc"]) - A if os.path.exists(kp) else (ts(d["written_utc"]) - A if str(d.get("producer", "")).startswith("shadow_loop") else None)
    c_w = ts(d["written_utc"]) - A if str(d.get("producer", "")).startswith("combo_stage") else None
    e = ends.get(A)
    rows.append({"anchor": U(A), "king_written_s": k_w, "combo_written_s": c_w, "daemon_end_s": (e[1] - A) if e else None, "rc": e[0] if e else None})
cw = np.array([r["combo_written_s"] for r in rows if r["combo_written_s"] is not None], float)
kw = np.array([r["king_written_s"] for r in rows if r["king_written_s"] is not None], float)
R = {"self_sha256": sha(os.path.abspath(__file__)), "inputs_sha256": SHA0, "executor_anchor_offset_min": exec_off,
     "env": {"whitelist": sorted(WHITE), "actual": {k: os.environ[k] for k in sorted(os.environ)}},
     "n_anchors": len(rows), "n_combo": int(len(cw)), "n_king_form": sum(1 for r in rows if r["combo_written_s"] is None),
     "king_written_s": {"median": float(np.median(kw)), "p90": float(np.quantile(kw, 0.9)), "max": float(kw.max()), "n_over_1355": int((kw > 1355).sum())},
     "combo_written_s": {"median": float(np.median(cw)), "p90": float(np.quantile(cw, 0.9)), "p99": float(np.quantile(cw, 0.99)), "max": float(cw.max()),
                         "min_margin_to_hard_deadline_1360s": float(1360 - cw.max()), "median_margin_to_hard_deadline_s": float(1360 - np.median(cw)),
                         "n_within_60s_of_deadline": int((cw > 1300).sum()), "margin_to_executor_read_s_min": float(exec_off * 60 - cw.max())},
     "latest_10": rows[-10:], "king_form_rows": [r for r in rows if r["combo_written_s"] is None],
     "slowest_5_combo": sorted([r for r in rows if r["combo_written_s"] is not None], key=lambda r: -r["combo_written_s"])[:5],
     "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
R["inputs_unchanged_during_run"] = {k: sha(p) for k, p in SRC.items()} == SHA0
json.dump(R, open(OUT, "w"), indent=1, default=str)
print(json.dumps({k: R[k] for k in ("n_anchors", "n_combo", "n_king_form", "king_written_s", "combo_written_s", "king_form_rows", "slowest_5_combo", "inputs_unchanged_during_run")}, indent=1, default=str))
print("SUMMARY state_combo_timing_probe rc=0")
