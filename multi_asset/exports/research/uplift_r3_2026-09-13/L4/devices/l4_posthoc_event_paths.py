#!/usr/bin/env python3
"""l4_posthoc_event_paths.py -- L4 POST-HOC descriptive (written after reading POSTHOC_L4_basis_reconcile.json; not in the PREREG; changes no verdict).
For the holds that carry the B1-minus-B2 basis difference (top 10 by |difference| in arms A01 and A05), dump the raw per-anchor path over the last
24 anchors of the hold and 6 anchors after: perp eligibility, spot tradable, spot_ok, funding events and summed rate in the window, raw B1 (perp/spot
close - 1, not carried) and raw B2 (premium index), in bps. Reads the build inputs (sha asserted) and the POST-HOC receipt only.
Usage: python3 l4_posthoc_event_paths.py <inputs_npz> <posthoc_json> <out_json>
"""
import sys, json, time, hashlib, calendar
import numpy as np
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
INP, PH, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
assert sha(INP) == "3d9d3466ce0078730c3630876d3767ba69da0135cfad9edf42fbfe59bfce05dd"
R = json.load(open(PH)); Z = np.load(INP, allow_pickle=True)
EG = Z["EG"].astype(np.int64); SYM = [str(s) for s in Z["SYM"]]; gi = {int(t): i for i, t in enumerate(EG)}
def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%MZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
seen = set(); out = dict(device="l4_posthoc_event_paths.py", label="POST-HOC", device_sha256=sha(__file__), inputs_sha256=sha(INP), posthoc_sha256=sha(PH), events=[])
for arm in ("A01", "A05"):
    for h in R["arms"][arm]["top10_by_abs_diff"]:
        key = (h["sym"], h["exit"])
        if key in seen or h["exit"] is None: continue
        seen.add(key); k = SYM.index(h["sym"]); ie = gi[ts(h["exit"])]; ii = gi[ts(h["entry"])]
        rows = []
        for i in range(max(ii, ie - 24), min(len(EG), ie + 7)):
            b1 = float(Z["B1"][i, k]); b2 = float(Z["B2"][i, k])
            rows.append(dict(t=iso(EG[i]), rel=int(i - ie), elig=bool(Z["ELIG"][i, k]), spot_trad=bool(Z["TRAD"][i, k]), spot_ok=bool(Z["SPOT_OK"][i, k]), nev_window=int(Z["NEV"][i, k]),
                             rate_sum_bps=float(Z["A"][i, k] * 1e4), b1_bps=(round(b1 * 1e4, 1) if np.isfinite(b1) else None), b2_bps=(round(b2 * 1e4, 1) if np.isfinite(b2) else None)))
        out["events"].append(dict(arm=arm, sym=h["sym"], entry=h["entry"], exit=h["exit"], reason=h["reason"], b1_pnl=h["b1_pnl"], b2_pnl=h["b2_pnl"], path=rows))
        last_b1 = [r for r in rows if r["rel"] <= 0 and r["b1_bps"] is not None]
        print("EVENT %s %-12s exit %s %-8s | b1 last-6 %s | b2 last-6 %s | spot_trad last-6 %s | nev last-6 %s" % (
            arm, h["sym"], h["exit"], h["reason"], [r["b1_bps"] for r in rows if -5 <= r["rel"] <= 0], [r["b2_bps"] for r in rows if -5 <= r["rel"] <= 0],
            "".join("1" if r["spot_trad"] else "0" for r in rows if -5 <= r["rel"] <= 0), [r["nev_window"] for r in rows if -6 <= r["rel"] <= -1]), flush=True)
json.dump(out, open(OUT, "w"), indent=1)
print("SUMMARY l4_posthoc_event_paths (POST-HOC) events=%d self_sha256=%s" % (len(out["events"]), out["device_sha256"][:16]))
