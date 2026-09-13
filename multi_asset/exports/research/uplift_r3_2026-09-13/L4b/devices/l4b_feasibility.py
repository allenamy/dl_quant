#!/usr/bin/env python3
"""l4b_feasibility.py -- L4b step 0 (pod2, CPU; archive listings only). Feasibility for the lead's L4b task (rebuild executable marks for L4's
forced-exit holds from raw 1m archives). Reads no price, computes no P&L. Written and committed before the L4b PREREG so that the PREREG can pin
the population and the exact archive coverage; the only network calls are S3 listings of data.binance.vision (static CDN exemption; host allowlist).
(1) Re-run L4's frozen state machine for A01..A08 by exec-ing the constants/core section of the committed l4_run.py (sha asserted) on the committed
L4 inputs (sha asserted); assert the per-anchor base net series equal L4_SERIES.npz bitwise. (2) Enumerate every hold (arm, perp symbol, spot symbol,
price_mult, entry anchor, exit anchor or open, exit reason, length). (3) Required (symbol, month) sets: months touched by [entry - 1 day, exit + 2 days]
(open holds to 2026-08-31) for all A01..A08 holds (family F2 marks) and for forced-exit holds (reasons forced_a / forced_b). (4) List the archive
prefixes spot/monthly/klines/<SPOT>/1m/, futures/um/monthly/{klines,markPriceKlines,indexPriceKlines}/<PERP>/1m/ for every F2 symbol and
futures/um/monthly/premiumIndexKlines/<PERP>/1m/ for forced-exit symbols; record keys and sizes; compute coverage of the required months and bytes.
Writes <out>/FEAS_L4b.json and <out>/http_log_feasibility.jsonl; prints one SUMMARY line.
Usage: python3 l4b_feasibility.py <env_whitelist_csv> <L4_work_dir> <l4_run.py> <trackA_perp_to_spot_map.json> <out_dir>
"""
import os, sys, json, time, math, hashlib, calendar, re
WHITE = set(x for x in sys.argv[1].split(",") if x); assert WHITE, "non-empty env whitelist required"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
L4W, RUNDEV, MAPP, OUT = [os.path.abspath(x) for x in sys.argv[2:6]]
assert OUT.startswith("/workspace/uplift_r3_2026-09-13/L4b/"), OUT
import numpy as np
import http.client, urllib.parse
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def ut(y, m, d, h=0): return calendar.timegm((y, m, d, h, 0, 0))
KNOWN = dict(run="cfa2517120979a46881eae42e4968a34a8d529e8fc817a0a54e16e45a0fc8a22", inputs="3d9d3466ce0078730c3630876d3767ba69da0135cfad9edf42fbfe59bfce05dd",
             series="8ba4ba1fa6220d9763443a920ea37a9abcba0536f55954a6d5d7fa05c2bb4473", map="b17eb0ba8fb50894bd268cdc79ba382d8c6bf07a43f38886ad8bfab9d0ee717a")
got = dict(run=sha(RUNDEV), inputs=sha(os.path.join(L4W, "l4_inputs.npz")), series=sha(os.path.join(L4W, "L4_SERIES.npz")), map=sha(MAPP))
assert got == KNOWN, ("input sha mismatch", got)
os.makedirs(OUT, exist_ok=True)
REC = dict(device="l4b_feasibility.py", device_sha256=sha(os.path.abspath(__file__)), run_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs_sha256=got,
           python=sys.version.split()[0], numpy=np.__version__, affinity=sorted(os.sched_getaffinity(0)))
assert len(REC["affinity"]) <= 8
src = open(RUNDEV).read(); a = src.index("# ---------------------------------------------------------------- constants"); b = src.index("# ---------------------------------------------------------------- G-SYN")
NS_ = {"np": np, "math": math, "REC": {"gates": {}}}; exec(compile(src[a:b], "l4_run_core", "exec"), NS_)
ARMS = NS_["ARMS"][:8]; assert [x["id"] for x in ARMS] == ["A%02d" % i for i in range(1, 9)]
Zf = np.load(os.path.join(L4W, "l4_inputs.npz"), allow_pickle=True); Z = {k: Zf[k] for k in Zf.files}; SER = np.load(os.path.join(L4W, "L4_SERIES.npz"))
EG = Z["EG"].astype(np.int64); SYM = [str(s) for s in Z["SYM"]]; iW0 = int(Z["iW0"]); iW1 = int(Z["iW1"])
D = NS_["prepare"](Z["A"].astype(np.float64), Z["NEV"].astype(np.int16), Z["ELIG"].astype(bool), Z["TRAD"].astype(bool), Z["SPOT_OK"].astype(bool), Z["B2"].astype(np.float64), Z["B1"].astype(np.float64))
MAPD = json.load(open(MAPP))["map"]
holds = []; eq = {}
for arm in ARMS:
    POS, hl, oh = NS_["simulate"](arm, D, iW0, iW1); acc = NS_["account"](POS, D, iW0, arm["K"], NS_["CS_BASE"])
    eq[arm["id"]] = bool(np.array_equal(acc["net"], SER["%s_net" % arm["id"]]))
    for (k, t0, t1, why) in hl + oh:
        s = SYM[k]; m = MAPD[s]
        holds.append(dict(arm=arm["id"], sym=s, spot=m["spot"], price_mult=m["price_mult"], entry_ts=int(EG[iW0 + t0]), exit_ts=(int(EG[iW0 + t1]) if t1 is not None else None),
                          reason=why, anchors=int((t1 if t1 is not None else iW1 - iW0 + 1) - t0)))
assert all(eq.values()), ("series mismatch", eq)
END = ut(2026, 8, 31, 0)
def months(lo, hi):
    out = []; y, mo = time.gmtime(lo).tm_year, time.gmtime(lo).tm_mon; y1, m1 = time.gmtime(hi).tm_year, time.gmtime(hi).tm_mon
    while (y, mo) <= (y1, m1):
        out.append("%04d-%02d" % (y, mo)); mo += 1
        if mo == 13: y += 1; mo = 1
    return out
req_f2 = {}; req_pop = {}
for h in holds:
    lo = h["entry_ts"] - 86400; hi = min((h["exit_ts"] if h["exit_ts"] is not None else END) + 2 * 86400, END)
    for mo in months(lo, hi):
        req_f2.setdefault((h["sym"], h["spot"]), set()).add(mo)
        if h["reason"] in ("forced_a", "forced_b"): req_pop.setdefault((h["sym"], h["spot"]), set()).add(mo)
# ---------------------------------------------------------------- archive listings (S3 static listing of data.binance.vision; allowlisted host, keep-alive)
S3HOST = "s3-ap-northeast-1.amazonaws.com"; LOG = open(os.path.join(OUT, "http_log_feasibility.jsonl"), "w")
BANNED = ("fapi.binance.com", "api.binance.com", "dapi.binance.com")
conn = [None]; last_req = [0.0]
def s3_list(prefix):
    keys = {}; marker = ""
    while True:
        q = "/data.binance.vision?delimiter=/&prefix=" + urllib.parse.quote(prefix, safe="/") + ("&marker=" + urllib.parse.quote(marker, safe="") if marker else "")
        assert not any(bn in S3HOST for bn in BANNED) and q.startswith("/data.binance.vision?")
        for attempt in range(4):
            wait = 0.25 - (time.time() - last_req[0])
            if wait > 0: time.sleep(wait)
            last_req[0] = time.time(); t0 = time.time()
            try:
                if conn[0] is None: conn[0] = http.client.HTTPSConnection(S3HOST, timeout=60)
                conn[0].request("GET", q); r = conn[0].getresponse(); body = r.read().decode(); st = r.status
                LOG.write(json.dumps(dict(t=time.strftime("%FT%TZ", time.gmtime()), host=S3HOST, path=q, status=st, bytes=len(body), secs=round(time.time() - t0, 2), attempt=attempt)) + "\n")
                if st != 200: raise RuntimeError("HTTP %d" % st)
                break
            except Exception as e:
                LOG.write(json.dumps(dict(t=time.strftime("%FT%TZ", time.gmtime()), host=S3HOST, path=q, error=repr(e), attempt=attempt)) + "\n")
                try: conn[0].close()
                except Exception: pass
                conn[0] = None; time.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError("listing failed after retries: " + prefix)
        for k_, s_ in re.findall(r"<Key>([^<]+)</Key>.*?<Size>(\d+)</Size>", body, flags=re.S): keys[k_] = int(s_)
        trunc = re.search(r"<IsTruncated>(\w+)</IsTruncated>", body); nm = re.search(r"<NextMarker>([^<]+)</NextMarker>", body)
        if not (trunc and trunc.group(1) == "true"): break
        marker = nm.group(1) if nm else sorted(keys)[-1]
    return keys
FAM = dict(spot_1m="data/spot/monthly/klines/{S}/1m/", perp_1m="data/futures/um/monthly/klines/{P}/1m/", mark_1m="data/futures/um/monthly/markPriceKlines/{P}/1m/",
           index_1m="data/futures/um/monthly/indexPriceKlines/{P}/1m/", premium_1m="data/futures/um/monthly/premiumIndexKlines/{P}/1m/")
cov = {}; tot = {}; listings = {}
t_start = time.time()
for (p, s), mos in sorted(req_f2.items()):
    for fam, pat in FAM.items():
        if fam == "premium_1m" and (p, s) not in req_pop: continue
        need = sorted(req_pop[(p, s)]) if fam == "premium_1m" else sorted(mos)
        sym_ = s if fam == "spot_1m" else p
        keys = s3_list(pat.format(S=s, P=p))
        have = {}
        for k_, sz in keys.items():
            mm = re.search(r"-1m-(\d{4}-\d{2})\.zip$", k_)
            if mm: have[mm.group(1)] = sz
        listings["%s|%s" % (fam, sym_)] = dict(n_zip=len(have), first=min(have) if have else None, last=max(have) if have else None)
        miss = [m_ for m_ in need if m_ not in have]; byt = sum(have[m_] for m_ in need if m_ in have)
        cov.setdefault(fam, dict(required=0, present=0, missing=[], bytes=0))
        cov[fam]["required"] += len(need); cov[fam]["present"] += len(need) - len(miss); cov[fam]["bytes"] += byt
        cov[fam]["missing"] += ["%s:%s" % (sym_, m_) for m_ in miss]
LOG.close()
pop = [h for h in holds if h["reason"] in ("forced_a", "forced_b")]
uniq = sorted(set((h["sym"], h["entry_ts"], h["exit_ts"], h["reason"]) for h in pop), key=lambda x: (x[2] or 0, x[0]))
REC.update(series_bitwise_equal=eq, n_holds=len(holds), holds_by_arm_reason={a_["id"]: {r_: sum(1 for h in holds if h["arm"] == a_["id"] and h["reason"] == r_) for r_ in ("normal", "forced_a", "forced_b", "forced_c", "open")} for a_ in ARMS},
           n_forced_ab_holds=len(pop), n_unique_forced_ab_events=len(uniq), unique_forced_ab_events=[dict(sym=u[0], entry=iso(u[1]), exit=iso(u[2]), reason=u[3]) for u in uniq],
           f2_symbols=len(req_f2), f2_name_months=sum(len(v) for v in req_f2.values()), pop_symbols=len(req_pop), pop_name_months=sum(len(v) for v in req_pop.values()),
           coverage={f: dict(required=v["required"], present=v["present"], missing_n=len(v["missing"]), missing=v["missing"][:200], bytes=v["bytes"]) for f, v in cov.items()},
           listings=listings, listing_seconds=round(time.time() - t_start, 1), holds=holds)
json.dump(REC, open(os.path.join(OUT, "FEAS_L4b.json"), "w"), indent=1)
print("SUMMARY l4b_feasibility series_equal=%d/8 holds=%d forced_ab_holds=%d unique_events=%d f2 sym=%d name-months=%d pop sym=%d name-months=%d | %s | listing %.0fs self_sha256=%s" % (
    sum(eq.values()), len(holds), len(pop), len(uniq), len(req_f2), REC["f2_name_months"], len(req_pop), REC["pop_name_months"],
    " ".join("%s %d/%d %.2fGB" % (f, v["present"], v["required"], v["bytes"] / 1e9) for f, v in cov.items()), REC["listing_seconds"], REC["device_sha256"][:16]), flush=True)
