#!/usr/bin/env python3
"""l4b_desc_stops.py -- L4b descriptive (written after reading TABLES_L4b.md; changes no reading, no survival statement). For each unique P_F event in
RECEIPT_L4b_marks.json: after the stopped leg's last traded minute tau, until L4's forced-exit anchor E_out, count (i) archive rows of that leg that are
present but untraded (number_of_trades == 0) and how many distinct closes they carry, (ii) perp funding events in (tau_perp, E_out] from fund_aug.json.gz,
(iii) present markPrice / indexPrice / premiumIndex rows after tau_perp and distinct premium closes. Purpose: explain why L4's tradability flags (5m closes)
and funding-based forced exit kept a hold open after a leg had stopped trading.
Usage: python3 l4b_desc_stops.py <env_whitelist_csv> <L4b_work_dir>
"""
import os, sys, json, time, calendar, hashlib, gzip
WHITE = set(x for x in sys.argv[1].split(",") if x); assert WHITE, "non-empty env whitelist required"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
W = os.path.abspath(sys.argv[2]); assert W.startswith("/workspace/uplift_r3_2026-09-13/L4b/")
import numpy as np
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ts(s): return None if s is None else calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%MZ"))
def iso(t): return None if t is None else time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
R = json.load(open(os.path.join(W, "RECEIPT_L4b_marks.json"))); PR = json.load(open(os.path.join(W, "RECEIPT_L4b_pull.json")))
FUND = "/workspace/fund_aug.json.gz"; assert sha(FUND) == "8a9e771577602dd1875a87fb07f982bc2c255e740966f911469420a44a53a8c2"
fund = json.load(gzip.open(FUND, "rt"))["rates"]
OUT = dict(device="l4b_desc_stops.py", label="DESCRIPTIVE", device_sha256=sha(os.path.abspath(__file__)), marks_receipt_sha256=sha(os.path.join(W, "RECEIPT_L4b_marks.json")), events=[])
cache = {}
for e in sorted(R["events"], key=lambda x: (x["exit"], x["sym"], x["entry"])):
    p = e["sym"]; fn = os.path.join(W, "sym", p + ".npz"); assert sha(fn) == PR["outputs"][p]["sha256"]
    if p not in cache:
        Z = np.load(fn, allow_pickle=True); segs = []
        for q in range(int(Z["n_seg"])):
            s0 = int(Z["seg%d_s0" % q]); m = {c: Z["seg%d_m_%s" % (q, c)] for c in ("spot_close", "spot_cnt", "perp_close", "perp_cnt", "mark_close", "index_close", "premium_close")}
            m["t"] = s0 + 60 * np.arange(len(m["spot_close"]), dtype=np.int64); segs.append(m)
        cache[p] = {c: np.concatenate([s[c] for s in segs]) for c in segs[0]}
    m = cache[p]; E_out = ts(e["exit"]); tS = ts(e["tau_spot"]); tP = ts(e["tau_perp"])
    rec = dict(sym=p, entry=e["entry"], exit=e["exit"], stopped=e["stopped"], nostop=e["nostop"], tau_spot=e["tau_spot"], tau_perp=e["tau_perp"])
    for leg, tau in (("spot", tS), ("perp", tP)):
        if tau is None: continue
        w = (m["t"] >= tau) & (m["t"] + 60 <= E_out)
        pres = w & np.isfinite(m[leg + "_close"]); untr = pres & (m[leg + "_cnt"] == 0); trd = pres & (m[leg + "_cnt"] > 0)
        rec[leg + "_after_tau"] = dict(minutes=int(w.sum()), rows_present=int(pres.sum()), rows_untraded=int(untr.sum()), rows_traded=int(trd.sum()),
                                       distinct_closes_untraded=int(len(np.unique(m[leg + "_close"][untr]))) if untr.any() else 0)
    if tP is not None:
        w = (m["t"] >= tP) & (m["t"] + 60 <= E_out)
        for c in ("mark_close", "index_close", "premium_close"):
            v = m[c][w & np.isfinite(m[c])]; rec[c + "_after_tau_perp"] = dict(rows=int(len(v)), distinct=int(len(np.unique(v))) if len(v) else 0)
        rows = fund.get(p, []); ev = [(r[0] // 1000 // 3600 * 3600, r[1]) for r in rows]
        sel = [x for x in ev if tP < x[0] <= E_out]
        rec["funding_after_tau_perp"] = dict(events=len(sel), first=iso(sel[0][0]) if sel else None, last=iso(sel[-1][0]) if sel else None, sum_rate_bps=float(sum(x[1] for x in sel) * 1e4),
                                             distinct_rates=len(set(x[1] for x in sel)))
    OUT["events"].append(rec)
    print("EV %-13s %s->%s stopped %-5s | spot after tau: %s | perp after tau: %s | funding after tau_perp: %s | premium after tau_perp: %s" % (
        p, e["entry"][:13], e["exit"][:13], "NOSTOP" if e["nostop"] else e["stopped"], rec.get("spot_after_tau"), rec.get("perp_after_tau"), rec.get("funding_after_tau_perp"), rec.get("premium_close_after_tau_perp")), flush=True)
json.dump(OUT, open(os.path.join(W, "DESC_L4b_stops.json"), "w"), indent=1)
print("SUMMARY l4b_desc_stops events=%d self_sha256=%s" % (len(OUT["events"]), OUT["device_sha256"][:16]))
