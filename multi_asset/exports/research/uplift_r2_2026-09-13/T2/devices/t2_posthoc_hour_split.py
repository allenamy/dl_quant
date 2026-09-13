#!/usr/bin/env python3
"""t2_posthoc_hour_split.py — POST-HOC, NOT PRE-REGISTERED, NO VERDICT WEIGHT.
Question (raised after the §7 tripwire failed for ARM-Nσ): is each arm's Δg vs A0 concentrated at the anchors where 8h-interval
names settle (00/08/16Z, where f_fund_now is the rate settled exactly at the anchor) or spread over 04/12/20Z as well?
Reads only the rec-only copies in receipts/arms_rec (sha-checked against SHA256_arms_rec.json) and the §7 tripwire artifacts'
recorded Δg; bootstrap kernel = r18/T2 boot() verbatim (UTC-day blocks, 2000 draws, default_rng([20260905,k])).
Local: env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t2_posthoc_hour_split.py <T2 dir>
"""
import json, sys, os, time, hashlib, calendar
import numpy as np
T2 = sys.argv[1]; AR = T2 + "/receipts/arms_rec"
S = json.load(open(AR + "/SHA256_arms_rec.json"))
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); NB = 2000
def load(tag):
    p = AR + "/%s.npz" % tag; assert sha(p) == S[os.path.basename(p)], p
    Z = np.load(p, allow_pickle=True); C = [str(c) for c in Z["cols"]]; r = Z["rec"]
    ts = r[:, C.index("ts")].astype(np.int64); gt = r[:, C.index("gross_total")]
    return ts, r[:, C.index("net_ex")] / gt, r[:, C.index("pnl_ex")] / gt, r[:, C.index("carry_ex")] / gt, r[:, C.index("cost_ex")] / gt
_D = {}
def boot(d, mask, day):
    idx = np.nonzero(mask)[0]; u, inv = np.unique(day[idx], return_inverse=True); tot = np.zeros(len(u)); cnt = np.zeros(len(u)); np.add.at(tot, inv, d[idx]); np.add.at(cnt, inv, 1.0); nd = len(u)
    if nd not in _D: _D[nd] = np.stack([np.random.default_rng([20260905, k]).integers(0, nd, nd) for k in range(NB)])
    ms = tot[_D[nd]].sum(1) / cnt[_D[nd]].sum(1)
    return [float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))]
OUT = dict(label="POST-HOC descriptive, not pre-registered, no verdict weight", self_sha256=sha(os.path.abspath(__file__)), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), arms={})
for s in ("42", "2027"):
    ts, g0, p0, c0, k0 = load("GP_A0_s%s" % s); wa = ts <= UB; wa[:900] = False; assert wa.sum() == 9138
    hour = (ts % 86400) // 3600; day = ts // 86400; settle8 = np.isin(hour, (0, 8, 16))
    for a in ("N", "Ns", "SK"):
        t1, g1, p1, c1, k1 = load("%s_A0_s%s" % (a, s)); assert np.array_equal(t1, ts)
        d = g1 - g0; o = {}
        for lab, m in (("all", wa), ("settle8_00_08_16Z", wa & settle8), ("nonsettle8_04_12_20Z", wa & ~settle8)):
            o[lab] = dict(n=int(m.sum()), dg=float(d[m].mean()), ci95=boot(d, m, day), dpnl=float((p1 - p0)[m].mean()), dcarry=float((c1 - c0)[m].mean()), dcost=float((k1 - k0)[m].mean()))
        o["by_hour"] = {int(h): dict(n=int((wa & (hour == h)).sum()), dg=float(d[wa & (hour == h)].mean()), dpnl=float((p1 - p0)[wa & (hour == h)].mean()), dcarry=float((c1 - c0)[wa & (hour == h)].mean())) for h in (0, 4, 8, 12, 16, 20)}
        o["share_of_dg_from_settle8"] = float(d[wa & settle8].sum() / d[wa].sum()) if abs(d[wa].sum()) > 1e-12 else None
        OUT["arms"]["%s_s%s" % (a, s)] = o
        print("%-3s s%-4s all %+.4f | 00/08/16Z %+.4f %s dpnl %+.3f dcarry %+.3f | 04/12/20Z %+.4f %s dpnl %+.3f dcarry %+.3f | by hour %s" % (a, s, o["all"]["dg"], o["settle8_00_08_16Z"]["dg"], [round(x, 3) for x in o["settle8_00_08_16Z"]["ci95"]], o["settle8_00_08_16Z"]["dpnl"], o["settle8_00_08_16Z"]["dcarry"],
              o["nonsettle8_04_12_20Z"]["dg"], [round(x, 3) for x in o["nonsettle8_04_12_20Z"]["ci95"]], o["nonsettle8_04_12_20Z"]["dpnl"], o["nonsettle8_04_12_20Z"]["dcarry"], {h: round(v["dg"], 3) for h, v in o["by_hour"].items()}))
json.dump(OUT, open(T2 + "/receipts/POSTHOC_T2_settlement_hour_split.json", "w"), indent=1)
print("wrote receipts/POSTHOC_T2_settlement_hour_split.json")
