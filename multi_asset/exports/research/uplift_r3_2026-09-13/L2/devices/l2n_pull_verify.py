#!/usr/bin/env python3
"""l2n_pull_verify.py — S1 steps 2-3 (AMENDMENT_L2_NC_population_2026-09-27 §4 rows 1, 3, 4, +1). NON-RETURN DATA ONLY (the public
data.binance.vision metrics archive; no exchange API host, asserted per request by l2_net). Committed before it is run.

Phase REPULL: every (symbol, day) in out/L2N_repull_list.json (sha asserted) is downloaded WITH its official .CHECKSUM, parsed in
memory by l2_net.parse_day (zip CRC, member name, header, 5-min grid, duplicates), label regime classified exactly as l2_b_pull.py
(corr of log taker ratio with logit cache tbf at cache offset 0 vs +1), and written to out/metrics_nc_extra/<SYM>.npz in the
l2_b_pull.py schema (+ row_file_day); file_checksum is 1 / 0 for EVERY file (full verification at pull time).
Phase CHECKSUM (restart checklist row 4, "full CHECKSUM before any statistic"): for EVERY file with status 200 in the A0 pull
(out/metrics/<SYM>.npz, 183,912 files), fetch only the official <file>.zip.CHECKSUM and compare its sha256 token and file name with the
file_zip_sha256 stored at pull time. A mismatch triggers one re-download of the zip with its CHECKSUM: if the new zip matches its own
CHECKSUM, the day is re-parsed and stored in out/metrics_ck_repulled/<SYM>.npz (the builder must use it instead of the stale rows) and the
row is labelled REPULLED_OK; otherwise VOID. A CHECKSUM that cannot be fetched (non-200 after l2_net's retries) is UNVERIFIED -- never read
as OK. Results per symbol in out/checksum_full/<SYM>.json (resumable: a symbol with a complete result file is skipped).
Rate: l2_net.Limiter (<= 20 req/s, halved while PID 333197 is not stopped), 16 threads; request counts by HTTP status in the receipt.
usage: env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 \
       /workspace/venv/bin/python -B l2n_pull_verify.py PATH,HOME,LC_CTYPE,OMP_NUM_THREADS,OPENBLAS_NUM_THREADS,MKL_NUM_THREADS REPULL|CHECKSUM
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C
import l2_net as N

PHASE = sys.argv[2]; assert PHASE in ("REPULL", "CHECKSUM")
envrep = C.check_env(sys.argv[:2])
L2 = C.L2; OUT = f"{L2}/out"; REC = f"{L2}/receipts"; DAY = 86400; SWITCH_DAY = calendar.timegm((2024, 3, 4, 0, 0, 0)) // DAY
REPULL = f"{OUT}/L2N_repull_list.json"; REPULL_SHA = "0c36552b126f4801bf3a85a9f5f69f85b617be9ce517e0e27cce28fedbf4b13a"
CACHE = "/workspace/data/dlnative_5m_wide829_f16_ext.npz"
dstr = lambda d: time.strftime("%Y-%m-%d", time.gmtime(d * DAY))
lim = N.Limiter(); cli = N.Client(lim); T0 = time.time()


def load_tbf():
    Zc = np.load(CACHE, allow_pickle=True); ch = [str(x) for x in Zc["ch"]]; assert ch[6] == "tbf", ch
    csym = [str(x) for x in Zc["symbols"]]; cts = Zc["ts"].astype(np.int64); assert np.all(np.diff(cts) == 300)
    return np.array(Zc["data"][:, :, 6], dtype=np.float32), {s: k for k, s in enumerate(csym)}, cts


def regime_corr(TBF, CIDX, cts, sym, T, R):     # l2_b_pull.py regime_corr, verbatim in effect
    n = CIDX.get(sym)
    if n is None or T.size == 0: return np.nan, np.nan
    k0 = (T - cts[0]) // 300; out = []; ok = np.isfinite(R) & (R > 0) & (T % 300 == 0)
    for s in (0, 1):
        k = k0 + s; inb = (k >= 0) & (k < cts.size); v = np.full(T.size, np.nan); v[inb] = TBF[k[inb], n]; out.append(v)
        ok &= np.isfinite(v) & (v > 0) & (v < 1)
    if ok.sum() < 100: return np.nan, np.nan
    x = np.log(R[ok]); x = x - x.mean(); cs = []
    for v in out:
        y = np.log(v[ok] / (1 - v[ok])); y = y - y.mean(); cs.append(float((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum())))
    return cs[0], cs[1]


def pull_days(sym, days, TB):
    """download + checksum + parse each day; -> dict of arrays in the l2_b_pull schema"""
    labs, Xs, rfd, fday, fstat, fsha, fck, freg, fc0, fc1 = [], [], [], [], [], [], [], [], [], []
    for d in days:
        g = N.fetch_day(cli, sym, dstr(d), with_checksum=True); fday.append(d)
        if g["status"] != 200:
            fstat.append(int(g["status"]) if g["status"] is not None else -1); fsha.append(""); fck.append(-1); freg.append("NA"); fc0.append(np.nan); fc1.append(np.nan); continue
        fstat.append(200); fsha.append(g["zip_sha256"]); fck.append(1 if g["checksum_ok"] is True else 0)
        p = N.parse_day(g["body"], sym, dstr(d))
        if p["ts"] is not None and p["crc_ok"] and p["member_ok"] and not p["errors"]:
            c0, c1 = regime_corr(*TB, sym, p["ts"], p["X"][:, 5])
            freg.append("END" if (np.isfinite(c0) and c0 >= c1 + 0.05) else ("START" if (np.isfinite(c1) and c1 >= c0 + 0.05) else "UNK")); fc0.append(c0); fc1.append(c1)
            labs.append(p["ts"]); Xs.append(p["X"].astype(np.float32)); rfd.append(np.full(p["ts"].size, d, np.int32))
        else:
            freg.append("PARSE_BAD"); fc0.append(np.nan); fc1.append(np.nan)
    L = np.concatenate(labs) if labs else np.zeros(0, np.int64); X = np.concatenate(Xs) if Xs else np.zeros((0, 6), np.float32)
    RF = np.concatenate(rfd) if rfd else np.zeros(0, np.int32); o = np.argsort(L, kind="stable")
    return dict(labels=L[o], X=X[o], row_file_day=RF[o], cols=np.array(N.COLS), file_day=np.array(fday, np.int32), file_status=np.array(fstat, np.int16),
                file_zip_sha256=np.array(fsha), file_checksum=np.array(fck, np.int8), file_regime=np.array(freg), corr0=np.array(fc0, np.float32), corr1=np.array(fc1, np.float32))


def save_npz(path, arrs):
    tmp = path + ".tmp.npz"; np.savez_compressed(tmp, **arrs); os.replace(tmp, path)
    z = np.load(path)
    for k, v in arrs.items(): assert np.array_equal(z[k], v, equal_nan=(v.dtype.kind == "f")), ("read-back mismatch", path, k)
    return C.sha256(path)


def phase_repull():
    assert C.sha256(REPULL) == REPULL_SHA, "re-pull list changed"
    R = json.load(open(REPULL)); TB = load_tbf(); od = f"{OUT}/metrics_nc_extra"; os.makedirs(od, exist_ok=True); man = {}

    def one(sym):
        p = f"{od}/{sym}.npz"
        if os.path.exists(p) and os.path.exists(p + ".done"): return sym, json.load(open(p + ".done"))
        a = pull_days(sym, [int(d) for d in R[sym]], TB); sh = save_npz(p, a)
        ent = {"sha256": sh, "days": len(R[sym]), "files_200": int((a["file_status"] == 200).sum()), "files_404": int((a["file_status"] == 404).sum()),
               "files_failed": int(((a["file_status"] != 200) & (a["file_status"] != 404)).sum()), "checksum_ok": int((a["file_checksum"] == 1).sum()),
               "checksum_mismatch": int((a["file_checksum"] == 0).sum()), "parse_bad": int((a["file_regime"] == "PARSE_BAD").sum()),
               "regime_violations": int(sum(1 for r, d in zip(a["file_regime"], a["file_day"]) if (r == "END" and d >= SWITCH_DAY) or (r == "START" and d < SWITCH_DAY)))}
        C.jdump(ent, p + ".done"); return sym, ent
    with ThreadPoolExecutor(16) as ex:
        for k, (sym, ent) in enumerate(ex.map(one, sorted(R))):
            man[sym] = ent
            if k % 25 == 0: print(f"REPULL progress {k + 1}/{len(R)} requests {cli.n_requests} http {json.dumps(cli.counts)} rate {lim.rate}", flush=True)
    tot = {q: int(sum(v[q] for v in man.values())) for q in ("days", "files_200", "files_404", "files_failed", "checksum_ok", "checksum_mismatch", "parse_bad", "regime_violations")}
    C.jdump(man, f"{od}/MANIFEST_extra.json")
    return {"phase": "REPULL", "repull_list_sha256": REPULL_SHA, "symbols": len(man), "totals": tot, "manifest_sha256": C.sha256(f"{od}/MANIFEST_extra.json")}


def phase_checksum():
    MD = f"{OUT}/metrics"; cd = f"{OUT}/checksum_full"; rd = f"{OUT}/metrics_ck_repulled"; os.makedirs(cd, exist_ok=True); os.makedirs(rd, exist_ok=True)
    syms = sorted(f[:-4] for f in os.listdir(MD) if f.endswith(".npz")); TB = None; tb_lock = __import__("threading").Lock()

    def one(sym):
        rp = f"{cd}/{sym}.json"
        if os.path.exists(rp):
            r = json.load(open(rp))
            if r.get("complete"): return sym, r
        Z = np.load(f"{MD}/{sym}.npz"); res = {"files": {}, "complete": False}; bad_days = []
        for d, st, zsha in zip(Z["file_day"], Z["file_status"], Z["file_zip_sha256"]):
            if int(st) != 200: continue
            name = "%s-metrics-%s.zip" % (sym, dstr(int(d)))
            s2, cb = cli.get("data.binance.vision", "/" + N.PREFIX + sym + "/" + name + ".CHECKSUM")
            if s2 != 200:
                res["files"][dstr(int(d))] = "UNVERIFIED_%s" % s2; continue
            tok = cb.decode("utf-8", "replace").split()
            ok = len(tok) == 2 and tok[0].lower() == str(zsha).lower() and tok[1].lstrip("*") == name
            res["files"][dstr(int(d))] = "OK" if ok else "MISMATCH"
            if not ok: bad_days.append(int(d))
        if bad_days:
            nonlocal_TB = _tb()
            a = pull_days(sym, bad_days, nonlocal_TB); save_npz(f"{rd}/{sym}.npz", a)
            for d, st, ck in zip(a["file_day"], a["file_status"], a["file_checksum"]):
                res["files"][dstr(int(d))] = "REPULLED_OK" if (int(st) == 200 and int(ck) == 1) else "VOID"
        res["complete"] = True; C.jdump(res, rp); return sym, res

    def _tb():
        nonlocal TB
        with tb_lock:
            if TB is None: TB = load_tbf()
        return TB
    agg = {}
    with ThreadPoolExecutor(16) as ex:
        for k, (sym, r) in enumerate(ex.map(one, syms)):
            for v in r["files"].values():
                key = v if not v.startswith("UNVERIFIED") else "UNVERIFIED"; agg[key] = agg.get(key, 0) + 1
            if k % 25 == 0: print(f"CHECKSUM progress {k + 1}/{len(syms)} {json.dumps(agg)} requests {cli.n_requests} http {json.dumps(cli.counts)} rate {lim.rate}", flush=True)
    return {"phase": "CHECKSUM", "symbols": len(syms), "files_by_result": agg, "files_total": int(sum(agg.values())),
            "all_verified": bool(agg.get("OK", 0) + agg.get("REPULLED_OK", 0) == sum(agg.values()))}


def main():
    st0 = C.sysstate(); st0["collector_333197"] = N.collector_state()
    out = phase_repull() if PHASE == "REPULL" else phase_checksum()
    rec = {"device": "l2n_pull_verify.py", "self_sha256": C.sha256(os.path.abspath(__file__)), "l2_net_sha256": C.sha256(os.path.join(os.path.dirname(os.path.abspath(__file__)), "l2_net.py")),
           "env": envrep, "sys_before": st0, "sys_after": dict(C.sysstate(), collector_333197=N.collector_state()), "limiter_states": lim.states,
           "requests": cli.n_requests, "http": cli.counts, "bytes": cli.bytes, "dns": N.DNS_STATS, "wall_s": round(time.time() - T0, 1), **out}
    p = f"{REC}/RECEIPT_L2N_{PHASE}.json"; C.jdump(rec, p); assert json.load(open(p))["self_sha256"] == rec["self_sha256"]
    print(f"L2N_{PHASE} DONE " + json.dumps({k: v for k, v in out.items() if k != 'phase'}) + " " + C.sha256(p)[:16], flush=True)


if __name__ == "__main__":
    main()
