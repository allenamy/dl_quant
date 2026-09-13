"""l2_b_pull.py — L2 metrics rebuild on pod2 from the public data.binance.vision archive (NON-RETURN DATA; may run before the prereg).
Request set = union over seeds of the UTC days touched by the label window of every A0 fund-leg short population row (i, n):
labels for data times [E_i − 24h − 10min, E_i − 10min], label = data time (window-END regime, days < 2024-03-04) or data time − 5min
(window-START regime, days ≥ 2024-03-04) ⇒ days floor((E − 86400 − 900)/86400) .. floor((E − 600)/86400); ∩ archive listing.
Per symbol: every needed day is downloaded once (<= 20 req/s global, 10 req/s while PID 333197 is not stopped), parsed in memory
(zip CRC, member name, header, 5-min grid, duplicate labels), raw zips never written to disk. CHECKSUM verified for the deterministic
10% subset int(sha256(symbol + '|' + day)[:8], 16) % 10 == 0, plus every file with a parse/CRC anomaly; any mismatch in a symbol ⇒
all of that symbol's files are checksum-verified.
Per-file regime check, network-free: corr(log taker ratio, logit cache tbf) at cache offset 0 (bar closing at T = window END label)
vs +1 (window START label); class END / START if one exceeds the other by >= 0.05 with >= 100 pairs, else UNK.
Output per symbol: out/metrics/<SYM>.npz (labels int64, X float32 n×6 in l2_net.COLS order, file_day int32, file_status int16,
file_zip_sha256, file_checksum int8 {1 ok, 0 mismatch, -1 not checked}, file_regime U5, corr0/corr1 float32); manifest with sha256.
Run 2 (12:23Z) was stopped by me at 10/618 symbols because 8 symbol threads gave ~12 req/s (latency-bound); run 3 uses 16 threads, same cap.
Resumable: a symbol whose npz sha matches out/metrics/MANIFEST.json and whose files are all 200 or 404 is skipped; a symbol with
transport / 5xx failures is REPAIRED day by day (rows of good days kept via row_file_day; npz written before row_file_day existed are
re-pulled whole). Run 1 (12:08–12:21Z) was stopped by me after 56 DNS gaierror / 16 timeouts left 2 of 621 BONK files missing; l2_net now caches
DNS (10 min) and retries transport errors 6× with back-off. dd probe (1600 MB) before the first write."""
import os, sys, time, json, calendar, hashlib, subprocess
import numpy as np
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C
import l2_net as N

T_START = time.time()
envrep = C.check_env(sys.argv)
st0 = C.sysstate(); st0["collector_333197"] = N.collector_state()
assert st0["gpu"].replace(" ", "") == "0%,2MiB", ("GPU not idle before run", st0["gpu"])
DEV = ("l2_common.py", "l2_net.py", "l2_b_pull.py", "run_l2.sh")
dev_sha = {f: C.sha256(os.path.join(C.L2, "devices", f)) for f in DEV}
DAY = 86400; SWITCH_DAY = calendar.timegm((2024, 3, 4, 0, 0, 0)) // DAY
ARCH = os.path.join(C.L2, "receipts", "RECEIPT_L2_A_archive.json")
ARCH_SHA = sys.argv[2] if len(sys.argv) > 2 else None
assert ARCH_SHA and C.sha256(ARCH) == ARCH_SHA, ("archive receipt sha must be passed and match", ARCH_SHA)
ar = json.load(open(ARCH)); assert all(ar["gates"].values()), ar["gates"]
LISTING = ar["listing"]["out"]; assert C.sha256(LISTING) == ar["listing"]["out_sha256"], "listing changed since the archive receipt"
POP = json.load(open(os.path.join(C.L2, "receipts", "RECEIPT_L2_A_population.json")))
OUTD = os.path.join(C.L2, "out", "metrics"); os.makedirs(OUTD, exist_ok=True)
MAN = os.path.join(OUTD, "MANIFEST.json")
CACHE = "/workspace/data/dlnative_5m_wide829_f16_ext.npz"

# dd probe (quota) before the first write
probe = os.path.join(C.L2, "out", "_ddprobe.bin")
pr = subprocess.run(["dd", "if=/dev/zero", "of=" + probe, "bs=1M", "count=1600", "conv=fsync"], capture_output=True, text=True)
probe_ok = pr.returncode == 0 and os.path.getsize(probe) == 1600 * 1024 * 1024
if os.path.exists(probe):
    os.remove(probe)
assert probe_ok, ("dd probe failed", pr.returncode, pr.stderr[-300:])

listed = {s: set(calendar.timegm(time.strptime(d, "%Y-%m-%d")) // DAY for d in v["zip_dates"]) for s, v in json.load(open(LISTING)).items()}
need = {}
for s in C.SEEDS:
    Z = np.load(POP["per_seed"][s]["out"]); assert C.sha256(POP["per_seed"][s]["out"]) == POP["per_seed"][s]["out_sha256"]
    P = Z["P"]; ts = Z["ts"]; sym = [str(x) for x in Z["symbols"]]
    lo = (ts - DAY - 900) // DAY; hi = (ts - 600) // DAY
    for n in np.nonzero(P.any(axis=0))[0]:
        rows = np.nonzero(P[:, n])[0]
        S = need.setdefault(sym[n], set())
        for i in rows:
            S.update(range(int(lo[i]), int(hi[i]) + 1))
SYMS = sorted(need)
req_total = sum(len(v) for v in need.values()); not_listed = {s: sorted(need[s] - listed.get(s, set())) for s in SYMS if need[s] - listed.get(s, set())}
print("request set: %d symbols, %d symbol-days, %d not in listing (%d symbols)" % (len(SYMS), req_total, sum(len(v) for v in not_listed.values()), len(not_listed)), flush=True)

Zc = np.load(CACHE, allow_pickle=True); ch = [str(x) for x in Zc["ch"]]; assert ch[6] == "tbf", ch
csym = [str(x) for x in Zc["symbols"]]; cts = Zc["ts"].astype(np.int64); assert np.all(np.diff(cts) == 300)
TBF = np.array(Zc["data"][:, :, 6], dtype=np.float32); CIDX = {s: k for k, s in enumerate(csym)}; del Zc

lim = N.Limiter(); cli = N.Client(lim)
man = json.load(open(MAN)) if os.path.exists(MAN) else {}


def dstr(d):
    return time.strftime("%Y-%m-%d", time.gmtime(d * DAY))


def in_ck_sample(sym, d):
    return int(hashlib.sha256((sym + "|" + dstr(d)).encode()).hexdigest()[:8], 16) % 10 == 0


def regime_corr(sym, T, R):
    n = CIDX.get(sym)
    if n is None or T.size == 0:
        return np.nan, np.nan, 0
    k0 = (T - cts[0]) // 300
    out = []; ok = np.isfinite(R) & (R > 0) & (T % 300 == 0)
    for s in (0, 1):
        k = k0 + s; inb = (k >= 0) & (k < cts.size)
        v = np.full(T.size, np.nan); v[inb] = TBF[k[inb], n]
        out.append(v); ok &= np.isfinite(v) & (v > 0) & (v < 1)
    if ok.sum() < 100:
        return np.nan, np.nan, int(ok.sum())
    x = np.log(R[ok]); x = x - x.mean()
    cs = []
    for v in out:
        y = np.log(v[ok] / (1 - v[ok])); y = y - y.mean()
        cs.append(float((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum())))
    return cs[0], cs[1], int(ok.sum())


def do_symbol(sym):
    days = sorted(need[sym] & listed.get(sym, set())); n_listed = len(days)
    out_p = os.path.join(OUTD, sym + ".npz")
    labs, Xs, rfd, fday, fstat, fsha, fck, freg, fc0, fc1 = [], [], [], [], [], [], [], [], [], []
    anomalies = {}; mismatch = False; repaired = 0
    if sym in man and os.path.exists(out_p) and C.sha256(out_p) == man[sym]["sha256"]:
        Zo = np.load(out_p, allow_pickle=False)
        st_o = Zo["file_status"].astype(int)
        if bool(np.all((st_o == 200) | (st_o == 404))):
            return sym, man[sym], "skipped"
        if "row_file_day" in Zo.files:   # keep good days, re-fetch the rest
            good = {int(d) for d, st in zip(Zo["file_day"], st_o) if st in (200, 404)}
            keep_rows = np.isin(Zo["row_file_day"], np.array(sorted(good), np.int32))
            labs.append(Zo["labels"][keep_rows]); Xs.append(Zo["X"][keep_rows]); rfd.append(Zo["row_file_day"][keep_rows])
            for q, d in enumerate(Zo["file_day"]):
                if int(d) in good:
                    fday.append(int(d)); fstat.append(int(st_o[q])); fsha.append(str(Zo["file_zip_sha256"][q])); fck.append(int(Zo["file_checksum"][q]))
                    freg.append(str(Zo["file_regime"][q])); fc0.append(float(Zo["corr0"][q])); fc1.append(float(Zo["corr1"][q]))
            days = [d for d in days if d not in good]; repaired = len(days)
    for d in days:
        f = N.fetch_day(cli, sym, dstr(d), with_checksum=False)
        fday.append(d)
        if f["status"] != 200:
            fstat.append(int(f["status"]) if f["status"] is not None else -1); fsha.append(""); fck.append(-1); freg.append("NA"); fc0.append(np.nan); fc1.append(np.nan)
            anomalies["http_%s" % f["status"]] = anomalies.get("http_%s" % f["status"], 0) + 1
            continue
        p = N.parse_day(f["body"], sym, dstr(d))
        bad = (not p["crc_ok"]) or (not p["member_ok"]) or p["ts"] is None or bool(p["errors"])
        if p["ts"] is not None:
            grid_bad = int((p["ts"] % 300 != 0).sum()); dups = int(p["n_rows"] - np.unique(p["ts"]).size)
            if grid_bad or dups:
                bad = True; anomalies["grid_or_dup"] = anomalies.get("grid_or_dup", 0) + 1
        ck = -1
        if bad or in_ck_sample(sym, d):
            g = N.fetch_day(cli, sym, dstr(d), with_checksum=True)
            ck = 1 if (g["checksum_ok"] is True and g["zip_sha256"] == f["zip_sha256"]) else 0
            mismatch |= ck == 0
        fstat.append(200); fsha.append(f["zip_sha256"]); fck.append(ck)
        if p["ts"] is not None:
            c0, c1, npairs = regime_corr(sym, p["ts"], p["X"][:, 5])
            freg.append("END" if (np.isfinite(c0) and c0 >= c1 + 0.05) else ("START" if (np.isfinite(c1) and c1 >= c0 + 0.05) else "UNK"))
            fc0.append(c0); fc1.append(c1)
            labs.append(p["ts"]); Xs.append(p["X"].astype(np.float32)); rfd.append(np.full(p["ts"].size, d, np.int32))
        else:
            freg.append("NA"); fc0.append(np.nan); fc1.append(np.nan)
        if bad:
            anomalies["parse_anomaly"] = anomalies.get("parse_anomaly", 0) + 1
    if mismatch:   # verify every file of this symbol
        for q, d in enumerate(fday):
            if fstat[q] == 200 and fck[q] == -1:
                g = N.fetch_day(cli, sym, dstr(d), with_checksum=True)
                fck[q] = 1 if (g["checksum_ok"] is True and g["zip_sha256"] == fsha[q]) else 0
    L = np.concatenate(labs) if labs else np.zeros(0, np.int64); X = np.concatenate(Xs) if Xs else np.zeros((0, 6), np.float32)
    RF = np.concatenate(rfd) if rfd else np.zeros(0, np.int32)
    o = np.argsort(L, kind="stable"); L = L[o]; X = X[o]; RF = RF[o]
    fo = np.argsort(np.array(fday, np.int64), kind="stable")
    fday = [fday[q] for q in fo]; fstat = [fstat[q] for q in fo]; fsha = [fsha[q] for q in fo]; fck = [fck[q] for q in fo]
    freg = [freg[q] for q in fo]; fc0 = [fc0[q] for q in fo]; fc1 = [fc1[q] for q in fo]
    tmp = out_p + ".tmp.npz"
    np.savez_compressed(tmp, labels=L, X=X, row_file_day=RF, cols=np.array(N.COLS), file_day=np.array(fday, np.int32), file_status=np.array(fstat, np.int16),
                        file_zip_sha256=np.array(fsha), file_checksum=np.array(fck, np.int8), file_regime=np.array(freg), corr0=np.array(fc0, np.float32),
                        corr1=np.array(fc1, np.float32))
    os.replace(tmp, out_p)
    ent = dict(sha256=C.sha256(out_p), size=os.path.getsize(out_p), files_needed=len(need[sym]), files_listed=n_listed, files_200=int(sum(1 for x in fstat if x == 200)),
               checksum_checked=int(sum(1 for x in fck if x != -1)), checksum_mismatch=int(sum(1 for x in fck if x == 0)), rows=int(L.size),
               regime_counts={k: int(sum(1 for q, x in enumerate(freg) if x == k)) for k in ("END", "START", "UNK", "NA")},
               regime_violations=int(sum(1 for q, x in enumerate(freg) if (x == "END" and fday[q] >= SWITCH_DAY) or (x == "START" and fday[q] < SWITCH_DAY))),
               anomalies=anomalies, repaired_days=repaired, files_404=int(sum(1 for x in fstat if x == 404)),
               files_failed=int(sum(1 for x in fstat if x not in (200, 404))))
    return sym, ent, "done"


done = 0; t_last = time.time()
NTHREADS = 16   # run 2 (8 symbol threads) reached only ~12 req/s (latency-bound, limiter never binding); the global <= 20 req/s cap is unchanged
with ThreadPoolExecutor(NTHREADS) as ex:
    for sym, ent, how in ex.map(do_symbol, SYMS):
        man[sym] = ent; done += 1
        if how == "done" and (done % 10 == 0 or time.time() - t_last > 120):
            C.jdump(man, MAN); t_last = time.time()
            print("progress %d/%d symbols, requests %d, http %s, dns %s, rate %.0f, wall %.0fs" % (done, len(SYMS), cli.n_requests, json.dumps(cli.counts), json.dumps(N.DNS_STATS), lim.rate, time.time() - T_START), flush=True)
C.jdump(man, MAN)
repair_passes = []
for rp in range(2):   # up to two repair passes over symbols that still have transport / 5xx failures
    todo = [s for s in SYMS if man[s].get("files_failed", man[s]["files_listed"] - man[s]["files_200"]) > 0]
    if not todo:
        break
    with ThreadPoolExecutor(NTHREADS) as ex:
        for sym, ent, how in ex.map(do_symbol, todo):
            man[sym] = ent
    C.jdump(man, MAN)
    repair_passes.append(dict(pass_no=rp + 1, symbols=len(todo), still_failed=int(sum(man[s].get("files_failed", 0) for s in todo))))
    print("repair pass %d: %s" % (rp + 1, json.dumps(repair_passes[-1])), flush=True)
tot = dict(symbols=len(SYMS), symbol_days_needed=req_total, not_in_listing=sum(len(v) for v in not_listed.values()),
           files_200=sum(man[s]["files_200"] for s in SYMS), files_404=sum(man[s].get("files_404", 0) for s in SYMS),
           files_failed=sum(man[s].get("files_failed", man[s]["files_listed"] - man[s]["files_200"]) for s in SYMS), checksum_checked=sum(man[s]["checksum_checked"] for s in SYMS),
           checksum_mismatch=sum(man[s]["checksum_mismatch"] for s in SYMS), rows=sum(man[s]["rows"] for s in SYMS),
           bytes_out=sum(man[s]["size"] for s in SYMS), regime_violations=sum(man[s]["regime_violations"] for s in SYMS),
           regime_counts={k: sum(man[s]["regime_counts"][k] for s in SYMS) for k in ("END", "START", "UNK", "NA")})
st1 = C.sysstate(); st1["collector_333197"] = N.collector_state()
rep = dict(device="l2_b_pull.py", device_sha256=dev_sha, env=envrep, sys_before=st0, sys_after=st1, archive_receipt_sha256=ARCH_SHA,
           listing_sha256=ar["listing"]["out_sha256"], dd_probe_mb=1600, totals=tot, repair_passes=repair_passes, not_in_listing=not_listed, manifest=dict(path=MAN, sha256=C.sha256(MAN)),
           http=dict(counts=dict(cli.counts), requests=cli.n_requests, bytes=cli.bytes), dns=dict(N.DNS_STATS), limiter_collector_states=lim.states,
           wall_s=round(time.time() - T_START, 1))
C.jdump(rep, os.path.join(C.L2, "receipts", "RECEIPT_L2_B_pull.json"))
assert st1["gpu"].replace(" ", "") == "0%,2MiB", ("GPU not idle after run", st1["gpu"])
print("SUMMARY l2_b_pull OK %s wall=%.0fs" % (json.dumps(tot), rep["wall_s"]), flush=True)
