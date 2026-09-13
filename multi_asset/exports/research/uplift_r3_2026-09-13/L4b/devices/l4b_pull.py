#!/usr/bin/env python3
"""l4b_pull.py -- L4b step 1 (pod2, CPU only). Implements PREREG_L4b_executable_marks_2026-09-13.md (sha256 bd7ad1e4..., frozen 2026-09-13T12:28:31Z,
commit ff41b981) section 3 and gate G-ARCHIVE. For every required (symbol, month) of FEAS_L4b (recomputed from its hold list with the frozen rule and
asserted equal to its counts) download from data.binance.vision (host allowlist; fapi/api absent) the monthly 1m zips of spot klines (<SPOT>),
perp klines, markPriceKlines, indexPriceKlines (<PERP>) and, for P_F symbols, premiumIndexKlines; verify each zip against the archive .CHECKSUM
(sha256); parse in memory (never written to disk); build minute arrays per contiguous month segment; derive per-anchor values:
  S(E), P(E)   = close of the latest TRADED minute (number_of_trades > 0) with bar end <= E, plus that bar end (staleness = E - bar end)
  MARK, INDEX, PREM(E) = close of the latest present bar with bar end <= E, plus that bar end
  S5(E), P5(E) = same as S, P at E - 300 s;  SN(E), PN(E) = first traded minute starting >= E and ending <= E + 3660 s
Writes <out>/sym/<PERP>.npz (anchor values; P_F symbols also the minute arrays), <out>/MANIFEST_pull.jsonl (one line per zip), <out>/http_log_pull.jsonl,
<out>/RECEIPT_L4b_pull.json; runs a 600 MB dd probe before the pull and after every 100 symbols. Prints one SUMMARY line; exits 3 if G-ARCHIVE fails.
Usage: python3 l4b_pull.py <env_whitelist_csv> <FEAS_L4b.json> <out_dir> <n_proc<=8>
"""
import os, sys, json, time, hashlib, calendar, io, zipfile, subprocess
WHITE = set(x for x in sys.argv[1].split(",") if x); assert WHITE, "non-empty env whitelist required"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
FEAS = os.path.abspath(sys.argv[2]); OUT = os.path.abspath(sys.argv[3]); NPROC = int(sys.argv[4]); assert 1 <= NPROC <= 8
assert OUT.startswith("/workspace/uplift_r3_2026-09-13/L4b/"), OUT
import numpy as np
import urllib.request, urllib.parse
from multiprocessing import Pool
PREREG_SHA = "bd7ad1e45be81647ce923e1117ca533439266edd8de4614946b52b8cd70e5586"
def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ut(y, m, d, h=0): return calendar.timegm((y, m, d, h, 0, 0))
END = ut(2026, 8, 31, 0); H4 = 14400
HOST = "data.binance.vision"; BANNED = ("fapi.binance.com", "api.binance.com", "dapi.binance.com", "api1.binance.com", "api2.binance.com", "api3.binance.com")
FAMS = dict(spot_1m="spot/monthly/klines/{S}/1m/{S}-1m-{M}.zip", perp_1m="futures/um/monthly/klines/{P}/1m/{P}-1m-{M}.zip",
            mark_1m="futures/um/monthly/markPriceKlines/{P}/1m/{P}-1m-{M}.zip", index_1m="futures/um/monthly/indexPriceKlines/{P}/1m/{P}-1m-{M}.zip",
            premium_1m="futures/um/monthly/premiumIndexKlines/{P}/1m/{P}-1m-{M}.zip")

def months(lo, hi):
    out = []; y, mo = time.gmtime(lo).tm_year, time.gmtime(lo).tm_mon; y1, m1 = time.gmtime(hi).tm_year, time.gmtime(hi).tm_mon
    while (y, mo) <= (y1, m1):
        out.append("%04d-%02d" % (y, mo)); mo += 1
        if mo == 13: y += 1; mo = 1
    return out
def mstart(m): return ut(int(m[:4]), int(m[5:7]), 1)
def mnext(m): y, mo = int(m[:4]), int(m[5:7]); return ut(y + (mo == 12), 1 if mo == 12 else mo + 1, 1)

def fetch(path):
    url = "https://%s/data/%s" % (HOST, path); pr = urllib.parse.urlparse(url)
    assert pr.hostname == HOST and pr.path.startswith("/data/") and not any(b in url for b in BANNED), url
    log = []; last = None
    for attempt in range(4):
        t0 = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "research-l4b/1.0"}), timeout=90) as r:
                body = r.read(); st = r.status
            log.append(dict(url=url, status=st, bytes=len(body), secs=round(time.time() - t0, 2), attempt=attempt)); return body, st, log
        except urllib.error.HTTPError as e:
            log.append(dict(url=url, status=e.code, secs=round(time.time() - t0, 2), attempt=attempt))
            if e.code == 404: return None, 404, log
            last = "HTTP %d" % e.code
        except Exception as e:
            log.append(dict(url=url, error=repr(e), secs=round(time.time() - t0, 2), attempt=attempt)); last = repr(e)
        time.sleep(2 * (attempt + 1))
    return None, -1, log

def parse(body, fam):
    import pandas as pd
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        names = z.namelist(); assert len(names) == 1, names; raw = z.read(names[0])
    header = raw[:1].isalpha()
    cols = [0, 4, 7, 8] if fam in ("spot_1m", "perp_1m") else [0, 4]
    d = pd.read_csv(io.BytesIO(raw), header=0 if header else None, usecols=cols)
    ot = d.iloc[:, 0].to_numpy(np.int64); unit = "us" if (len(ot) and ot.max() > 10**14) else "ms"
    ot_s = ot // 1000000 if unit == "us" else ot // 1000
    close = d.iloc[:, 1].to_numpy(np.float64)
    qv = d.iloc[:, 2].to_numpy(np.float64) if len(cols) == 4 else None
    cnt = d.iloc[:, 3].to_numpy(np.float64) if len(cols) == 4 else None
    return dict(ot_s=ot_s, close=close, qv=qv, cnt=cnt, header=bool(header), unit=unit, rows=int(len(ot)))

def job(args):
    perp, spot, mult, mos, is_pf, prem_months = args
    segs = []; cur = [mos[0]]
    for m in mos[1:]:
        if mstart(m) == mnext(cur[-1]): cur.append(m)
        else: segs.append(cur); cur = [m]
    segs.append(cur)
    man = []; logs = []; seg_out = []
    for seg in segs:
        s0 = mstart(seg[0]); s1 = mnext(seg[-1]); T = (s1 - s0) // 60
        arr = dict(spot_close=np.full(T, np.nan), spot_qv=np.full(T, np.nan), spot_cnt=np.zeros(T), perp_close=np.full(T, np.nan), perp_qv=np.full(T, np.nan), perp_cnt=np.zeros(T),
                   mark_close=np.full(T, np.nan), index_close=np.full(T, np.nan), premium_close=np.full(T, np.nan))
        for fam in ("spot_1m", "perp_1m", "mark_1m", "index_1m") + (("premium_1m",) if is_pf else ()):
            for m in (seg if fam != "premium_1m" else [x for x in seg if x in prem_months]):
                path = FAMS[fam].format(S=spot, P=perp, M=m)
                body, st, lg = fetch(path); logs += lg
                rec = dict(family=fam, perp=perp, spot=spot, month=m, path=path, status=st)
                if body is None:
                    rec["ok"] = False; man.append(rec); continue
                cks, cst, lg2 = fetch(path + ".CHECKSUM"); logs += lg2
                h = hashlib.sha256(body).hexdigest(); rec.update(bytes=len(body), sha256=h, checksum_status=cst)
                rec["checksum_ok"] = bool(cks is not None and cks.decode().split()[0].strip().lower() == h)
                try:
                    p_ = parse(body, fam)
                except Exception as e:
                    rec.update(ok=False, parse_error=repr(e)); man.append(rec); continue
                ot = p_["ot_s"]; idx = (ot - s0) // 60; on = (ot % 60 == 0) & (idx >= 0) & (idx < T)
                dup = int(len(idx[on]) - len(np.unique(idx[on])))
                rec.update(rows=p_["rows"], on_grid=int(on.sum()), dup_minutes=dup, header=p_["header"], ts_unit=p_["unit"],
                           first_open=int(ot.min()) if len(ot) else None, last_open=int(ot.max()) if len(ot) else None)
                key = fam.split("_")[0]
                arr[key + "_close"][idx[on]] = p_["close"][on]
                if p_["qv"] is not None:
                    arr[key + "_qv"][idx[on]] = p_["qv"][on]; arr[key + "_cnt"][idx[on]] = p_["cnt"][on]
                    rec["traded_minutes"] = int((p_["cnt"][on] > 0).sum())
                if key == "spot": arr["spot_close"][idx[on]] *= mult
                rec["ok"] = bool(rec["checksum_ok"] and p_["rows"] >= 0)
                man.append(rec); del body, p_
        # derived anchor values (bar end = open + 60 s)
        mi = np.arange(T)
        def last_idx(valid):
            li = np.where(valid, mi, -1); return np.maximum.accumulate(li)
        L = dict(S=last_idx((arr["spot_cnt"] > 0) & np.isfinite(arr["spot_close"])), P=last_idx((arr["perp_cnt"] > 0) & np.isfinite(arr["perp_close"])),
                 MARK=last_idx(np.isfinite(arr["mark_close"])), INDEX=last_idx(np.isfinite(arr["index_close"])), PREM=last_idx(np.isfinite(arr["premium_close"])))
        src = dict(S="spot_close", P="perp_close", MARK="mark_close", INDEX="index_close", PREM="premium_close")
        E = np.arange(s0 + H4, s1 + 1, H4, dtype=np.int64)   # anchors whose bars (end <= E) lie inside the segment
        o = dict(E=E)
        for nm, off in (("", 0), ("5", 300)):
            j = (E - off - 60 - s0) // 60                     # the minute whose bar ends exactly at E - off
            for leg in (("S", "P") if nm else ("S", "P", "MARK", "INDEX", "PREM")):
                val = np.full(len(E), np.nan); tb = np.full(len(E), -1, np.int64)
                ok = (j >= 0) & (j < T)
                li = np.where(ok, L[leg][np.clip(j, 0, T - 1)], -1); has = li >= 0
                val[has] = arr[src[leg]][li[has]]; tb[has] = s0 + li[has] * 60 + 60
                o[leg + nm] = val; o["t" + leg + nm] = tb
        # first traded minute starting at or after E and ending by E + 3660 s (stale-entry fallback, PREREG 4)
        for leg, vk in (("S", "spot"), ("P", "perp")):
            valid = (arr[vk + "_cnt"] > 0) & np.isfinite(arr[vk + "_close"])
            nx = np.where(valid, mi, T); nx = np.minimum.accumulate(nx[::-1])[::-1]
            j0 = (E - s0) // 60; ok = (j0 >= 0) & (j0 < T)
            ni = np.where(ok, nx[np.clip(j0, 0, T - 1)], T); has = (ni < T)
            tend = s0 + ni * 60 + 60; has &= tend <= E + 3660
            val = np.full(len(E), np.nan); tb = np.full(len(E), -1, np.int64)
            val[has] = arr[vk + "_close"][ni[has]]; tb[has] = tend[has]
            o[leg + "N"] = val; o["t" + leg + "N"] = tb
        seg_out.append(dict(s0=s0, s1=s1, anchors=o, minutes=(arr if is_pf else None)))
    # save
    fn = os.path.join(OUT, "sym", perp + ".npz"); save = dict(perp=perp, spot=spot, mult=mult, is_pf=is_pf, n_seg=len(seg_out))
    for q, so in enumerate(seg_out):
        save["seg%d_s0" % q] = so["s0"]; save["seg%d_s1" % q] = so["s1"]
        for k, v in so["anchors"].items(): save["seg%d_a_%s" % (q, k)] = v
        if so["minutes"] is not None:
            for k, v in so["minutes"].items(): save["seg%d_m_%s" % (q, k)] = v
    np.savez_compressed(fn, **save)
    return perp, man, logs, sha_file(fn), os.path.getsize(fn)

def ddprobe(tag):
    p = os.path.join(OUT, "_ddprobe"); t0 = time.time()
    r = subprocess.run(["dd", "if=/dev/zero", "of=" + p, "bs=1M", "count=600", "conv=fsync"], capture_output=True, text=True)
    ok = r.returncode == 0 and os.path.exists(p) and os.path.getsize(p) == 600 * 1024 * 1024
    try: os.remove(p)
    except OSError: pass
    return dict(tag=tag, ok=bool(ok), rc=r.returncode, secs=round(time.time() - t0, 1), stderr_tail=r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "")

if __name__ == "__main__":
    T_START = time.time(); os.makedirs(os.path.join(OUT, "sym"), exist_ok=True)
    F = json.load(open(FEAS)); holds = F["holds"]
    req = {}; pf = set()
    for h in holds:
        lo = h["entry_ts"] - 86400; hi = min((h["exit_ts"] if h["exit_ts"] is not None else END) + 2 * 86400, END)
        key = (h["sym"], h["spot"], float(h["price_mult"]))
        req.setdefault(key, set()).update(months(lo, hi))
        if h["reason"] in ("forced_a", "forced_b"): pf.add(h["sym"])
    n_nm = sum(len(v) for v in req.values()); n_pf_nm = sum(len(v) for k, v in req.items() if k[0] in pf)
    assert len(req) == F["f2_symbols"] and n_nm == F["f2_name_months"], (len(req), n_nm)
    pop_nm = {}
    for h in holds:
        if h["reason"] in ("forced_a", "forced_b"):
            lo = h["entry_ts"] - 86400; hi = min(h["exit_ts"] + 2 * 86400, END); pop_nm.setdefault(h["sym"], set()).update(months(lo, hi))
    assert len(pop_nm) == F["pop_symbols"] and sum(len(v) for v in pop_nm.values()) == F["pop_name_months"]
    REC = dict(device="l4b_pull.py", device_sha256=sha_file(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, run_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               feas_sha256=sha_file(FEAS), python=sys.version.split()[0], numpy=np.__version__, nproc=NPROC, affinity=sorted(os.sched_getaffinity(0)),
               env_actual={k: os.environ[k] for k in sorted(os.environ)}, n_symbols=len(req), n_name_months=n_nm, pf_symbols=sorted(pf), dd_probes=[])
    assert len(REC["affinity"]) <= 8
    print("CONFIG " + json.dumps(dict(self_sha256=REC["device_sha256"], prereg=PREREG_SHA, symbols=len(req), name_months=n_nm, pf_symbols=len(pf), nproc=NPROC)), flush=True)
    d0 = ddprobe("start"); REC["dd_probes"].append(d0); print("DDPROBE " + json.dumps(d0), flush=True); assert d0["ok"], "dd probe failed before pull"
    # premiumIndexKlines only for the P_F-hold months of P_F symbols (FEAS pop set, 39 name-months)
    jobs = [(k[0], k[1], k[2], sorted(v), k[0] in pf, sorted(pop_nm.get(k[0], set()))) for k, v in sorted(req.items())]
    MAN = open(os.path.join(OUT, "MANIFEST_pull.jsonl"), "w"); HLOG = open(os.path.join(OUT, "http_log_pull.jsonl"), "w")
    outs = {}; done = 0
    with Pool(NPROC) as pool:
        for perp, man, logs, fsha, fsz in pool.imap_unordered(job, jobs):
            for r_ in man: MAN.write(json.dumps(r_) + "\n")
            for l_ in logs: HLOG.write(json.dumps(l_) + "\n")
            outs[perp] = dict(sha256=fsha, bytes=fsz, zips=len(man), zips_ok=sum(1 for r_ in man if r_.get("ok")))
            done += 1
            if done % 25 == 0: print("PROG %d/%d %.0fs" % (done, len(jobs), time.time() - T_START), flush=True)
            if done % 100 == 0:
                dp = ddprobe("after_%d" % done); REC["dd_probes"].append(dp); print("DDPROBE " + json.dumps(dp), flush=True); assert dp["ok"], "dd probe failed"
    MAN.close(); HLOG.close()
    mrows = [json.loads(l) for l in open(os.path.join(OUT, "MANIFEST_pull.jsonl"))]
    need = dict(spot_1m=n_nm, perp_1m=n_nm, mark_1m=n_nm, index_1m=n_nm, premium_1m=sum(len(v) for v in pop_nm.values()))
    by = {f: dict(required=need[f], rows=sum(1 for r_ in mrows if r_["family"] == f), ok=sum(1 for r_ in mrows if r_["family"] == f and r_.get("ok")),
                  checksum_ok=sum(1 for r_ in mrows if r_["family"] == f and r_.get("checksum_ok")), status_200=sum(1 for r_ in mrows if r_["family"] == f and r_.get("status") == 200),
                  empty_rows=sum(1 for r_ in mrows if r_["family"] == f and r_.get("rows") == 0), bytes=sum(r_.get("bytes", 0) for r_ in mrows if r_["family"] == f),
                  dup_minutes=sum(r_.get("dup_minutes", 0) for r_ in mrows if r_["family"] == f), us_files=sum(1 for r_ in mrows if r_["family"] == f and r_.get("ts_unit") == "us")) for f in need}
    pop_cover = all(any(r_["family"] == "premium_1m" and r_["perp"] == s and r_["month"] == m and r_.get("ok") for r_ in mrows) for s, ms in pop_nm.items() for m in ms)
    G_ARCHIVE = bool(all(v["rows"] == v["required"] and v["ok"] == v["required"] for v in by.values()) and pop_cover)
    REC.update(by_family=by, premium_covers_pop_months=bool(pop_cover), outputs=outs, gates={"G-ARCHIVE": dict(pass_=G_ARCHIVE)}, elapsed_s=round(time.time() - T_START, 1))
    d1 = ddprobe("end"); REC["dd_probes"].append(d1)
    REC["manifest_sha256"] = sha_file(os.path.join(OUT, "MANIFEST_pull.jsonl")); REC["http_log_sha256"] = sha_file(os.path.join(OUT, "http_log_pull.jsonl"))
    json.dump(REC, open(os.path.join(OUT, "RECEIPT_L4b_pull.json"), "w"), indent=1)
    print("SUMMARY l4b_pull G-ARCHIVE=%s %s symbols=%d elapsed=%.0fs self_sha256=%s" % (G_ARCHIVE, " ".join("%s %d/%d ck%d %.2fGB" % (f, v["ok"], v["required"], v["checksum_ok"], v["bytes"] / 1e9) for f, v in by.items()),
          len(outs), REC["elapsed_s"], REC["device_sha256"][:16]), flush=True)
    sys.exit(0 if G_ARCHIVE else 3)
