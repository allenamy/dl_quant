"""l2_a_switch.py — L2 Stage A: date the metrics-archive label-semantics switch found by l2_a_semantics2 (rc=0, 11:48:06Z):
2022–2023 files: taker ratio = base-volume buy/sell over [T−5min, T) and the OI snapshot matches the 1m close at T (label = window END);
2024-04 onward: taker ratio = quote-volume buy/sell over [T, T+5min) and the OI snapshot matches the close at T+5min (label = window START);
2024-02-25 still END, 2024-04-09 already START. This scan classifies EVERY day 2024-01-15..2024-05-15 for BTCUSDT and ETHUSDT.
Per day: metrics d (+CHECKSUM), 1m klines d−1, d, d+1 (+CHECKSUM, each fetched once). Classes per day:
  K2: exact-match rate (|R/ratio − 1| ≤ 1e-4) of base over [T−5m,T) and quote over [T,T+5m), restricted to labels whose windows stay inside the day's klines;
  K3: median |OI value/qty ÷ 1m close − 1| at T (close of minute ending T) and at T+5min.
  END if base_end ≥ 0.5 and k3(T) < k3(T+5); START if quote_start ≥ 0.5 and k3(T+5) < k3(T); else MIXED/NONE.
DATA FACTS ONLY: price levels are used only to locate the OI minute; no return is computed. Gate: none (reported facts); rc 0 unless an exception."""
import os, sys, time, json, calendar, io, zipfile, csv, hashlib
import numpy as np
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C
import l2_net as N

T_START = time.time()
envrep = C.check_env(sys.argv)
st0 = C.sysstate(); st0["collector_333197"] = N.collector_state()
assert st0["gpu"].replace(" ", "") == "0%,2MiB", ("GPU not idle before run", st0["gpu"])
DEV = ("l2_common.py", "l2_net.py", "l2_a_switch.py", "run_l2.sh")
dev_sha = {f: C.sha256(os.path.join(C.L2, "devices", f)) for f in DEV}
DAY = 86400; KPFX = "/data/futures/um/daily/klines/"
D0 = calendar.timegm((2024, 1, 15, 0, 0, 0)) // DAY; D1 = calendar.timegm((2024, 5, 15, 0, 0, 0)) // DAY
SYMS = ("BTCUSDT", "ETHUSDT")
lim = N.Limiter(); cli = N.Client(lim)


def dstr(d):
    return time.strftime("%Y-%m-%d", time.gmtime(d * DAY))


def kl1m(job):
    sym, d = job
    path = "%s%s/1m/%s-1m-%s.zip" % (KPFX, sym, sym, dstr(d))
    st, body = cli.get("data.binance.vision", path)
    if st != 200:
        return job, dict(status=st)
    st2, cb = cli.get("data.binance.vision", path + ".CHECKSUM")
    ok = bool(st2 == 200 and cb.decode().split()[0].lower() == hashlib.sha256(body).hexdigest())
    txt = zipfile.ZipFile(io.BytesIO(body)).read("%s-1m-%s.csv" % (sym, dstr(d))).decode("utf-8-sig")
    rows = [r for r in csv.reader(io.StringIO(txt)) if r and r[0].strip().isdigit()]
    A = np.array([[float(r[0]), float(r[4]), float(r[5]), float(r[7]), float(r[9]), float(r[10])] for r in rows], np.float64)
    return job, dict(status=200, checksum_ok=ok, o=A[:, 0].astype(np.int64) // 1000, c=A[:, 1], v=A[:, 2], q=A[:, 3], tb=A[:, 4], tq=A[:, 5])


def met(job):
    sym, d = job
    f = N.fetch_day(cli, sym, dstr(d), with_checksum=True)
    return job, dict(status=f["status"], checksum_ok=f["checksum_ok"], p=(N.parse_day(f["body"], sym, dstr(d)) if f["body"] is not None else None))


with ThreadPoolExecutor(8) as ex:
    K = dict(ex.map(kl1m, [(s, d) for s in SYMS for d in range(D0 - 1, D1 + 2)]))
    M = dict(ex.map(met, [(s, d) for s in SYMS for d in range(D0, D1 + 1)]))
days = []
for s in SYMS:
    for d in range(D0, D1 + 1):
        rec = dict(sym=s, day=dstr(d), metrics_status=M[(s, d)]["status"], metrics_checksum_ok=M[(s, d)]["checksum_ok"])
        ks = [K[(s, dd)] for dd in (d - 1, d, d + 1)]
        p = M[(s, d)]["p"]
        if p is None or p["ts"] is None or any(k["status"] != 200 for k in ks):
            rec["cls"] = "NODATA"; days.append(rec); continue
        o = np.concatenate([k["o"] for k in ks]); assert np.all(np.diff(o) == 60)
        c = np.concatenate([k["c"] for k in ks]); v = np.concatenate([k["v"] for k in ks]); q = np.concatenate([k["q"] for k in ks])
        tb = np.concatenate([k["tb"] for k in ks]); tq = np.concatenate([k["tq"] for k in ks])
        pos = {int(t): i for i, t in enumerate(o)}
        T = p["ts"]; R = p["X"][:, 5]; OIQ = p["X"][:, 0]; OIV = p["X"][:, 1]

        def win(start_off, vol, buy):
            out = np.full(T.size, np.nan)
            for a, t in enumerate(T):
                i = pos.get(int(t) + start_off)
                if i is not None and i + 5 <= o.size:
                    b = buy[i:i + 5].sum(); tot = vol[i:i + 5].sum()
                    if tot - b > 0:
                        out[a] = b / (tot - b)
            return out
        rb_end = win(-300, v, tb); rq_start = win(0, q, tq)
        ok_b = np.isfinite(R) & (R > 0) & np.isfinite(rb_end); ok_q = np.isfinite(R) & (R > 0) & np.isfinite(rq_start)
        base_end = float((np.abs(R[ok_b] / rb_end[ok_b] - 1) <= 1e-4).mean()) if ok_b.any() else None
        quote_start = float((np.abs(R[ok_q] / rq_start[ok_q] - 1) <= 1e-4).mean()) if ok_q.any() else None

        def k3(minute_off):
            idx = np.array([pos.get(int(t) + minute_off * 60 - 60, -1) for t in T])
            g = (idx >= 0) & np.isfinite(OIQ) & np.isfinite(OIV) & (OIQ > 0)
            return float(np.median(np.abs((OIV[g] / OIQ[g]) / c[idx[g]] - 1))) if g.any() else None
        k0 = k3(0); k5 = k3(5)
        cls = "MIXED"
        if base_end is not None and base_end >= 0.5 and k0 is not None and k5 is not None and k0 < k5:
            cls = "END"
        elif quote_start is not None and quote_start >= 0.5 and k0 is not None and k5 is not None and k5 < k0:
            cls = "START"
        rec.update(base_end=base_end, quote_start=quote_start, k3_T=k0, k3_T5=k5, cls=cls)
        days.append(rec)
first_start = {s: next((r["day"] for r in days if r["sym"] == s and r["cls"] == "START"), None) for s in SYMS}
last_end = {s: max((r["day"] for r in days if r["sym"] == s and r["cls"] == "END"), default=None) for s in SYMS}
st1 = C.sysstate(); st1["collector_333197"] = N.collector_state()
rep = dict(device="l2_a_switch.py", device_sha256=dev_sha, env=envrep, sys_before=st0, sys_after=st1, window=[dstr(D0), dstr(D1)], symbols=SYMS,
           days=days, first_START=first_start, last_END=last_end,
           class_counts={s: {k: sum(1 for r in days if r["sym"] == s and r["cls"] == k) for k in ("END", "START", "MIXED", "NODATA")} for s in SYMS},
           http=dict(cli.counts), requests=cli.n_requests, wall_s=round(time.time() - T_START, 1))
C.jdump(rep, os.path.join(C.L2, "receipts", "RECEIPT_L2_A_switch.json"))
for r in days:
    print("DAY %s %s %s base_end=%s quote_start=%s k3T=%s k3T5=%s" % (r["sym"], r["day"], r["cls"], r.get("base_end"), r.get("quote_start"), r.get("k3_T"), r.get("k3_T5")), flush=True)
assert st1["gpu"].replace(" ", "") == "0%,2MiB", ("GPU not idle after run", st1["gpu"])
print("SUMMARY l2_a_switch OK last_END=%s first_START=%s counts=%s requests=%d wall=%.0fs" % (
    json.dumps(last_end), json.dumps(first_start), json.dumps(rep["class_counts"]), cli.n_requests, rep["wall_s"]), flush=True)
