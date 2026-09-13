"""l2_a_semantics2.py — L2 Stage A (second pass, per-file): pin the clock semantics of (a) the metrics archive labels and (b) the 5m cache labels, with
independent public kline files whose open_time / close_time are explicit. Triggered by l2_a_archive run 1 (receipts/failed_first_runs/,
11:37:38Z): the 5m spectrum peaked at cache offset +1 (0.590; offset 0 0.432; others <= 0.025), outside both readings on record.
DATA FACTS ONLY — no return is computed; price LEVELS are used once, to locate the OI snapshot minute (K3), and only offsets and
level-match rates are reported.
Run 1 (l2_a_semantics.py, receipt RECEIPT_L2_A_semantics.json, rc=1 at GATE K2): K1 cache = CLOSE-time labels (c=+1: 0.9998 base / 1.0
quote); K2 no single window (exact: base o=-5 0.368, quote o=0 0.456) => a MIXTURE; K3 OI minimum at o=+5. This pass classifies per FILE.
Sample: 20 (symbol, day) pairs per year drawn at random (rng [20260913, year, 2]) from the seeded 200-pair l2_a_archive sample.
Per pair: metrics day d; 1m klines d−1, d, d+1; 5m klines d (all zip + CHECKSUM).
 K1 cache label: 5m-kline taker-buy fraction by open_time vs cache 'tbf' at cache ts = open_time + c·300, c ∈ {−2..+2}; match |Δ| ≤ 1.5e-3.
 K2 metrics taker window: metrics sum_taker_long_short_vol_ratio at label T vs Σbuy/Σsell over 1m bars with open_time in
    [T + o·60, T + o·60 + 300), o ∈ {−10..+10} min, base and quote volumes; exact match |R/ratio − 1| ≤ 1e-4 (6-decimal archive values).
 K3 OI snapshot: sum_open_interest_value / sum_open_interest at label T vs the 1m close of the minute ending at T + o·60,
    o ∈ {−10..+10}; median |level/close − 1| and share ≤ 5e-4.
Per file: K2 exact-match rate for every (offset, base|quote); class = the (offset, volume) cell with rate >= 0.90, else "none";
K3 best minute. Gate (asserted after the receipt is written): K1 unique offset >= 0.95. K2 / K3 are reported facts (no gate)."""
import os, sys, time, json, calendar, io, zipfile, csv
import numpy as np
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C
import l2_net as N

T_START = time.time()
envrep = C.check_env(sys.argv)
st0 = C.sysstate(); st0["collector_333197"] = N.collector_state()
assert st0["gpu"].replace(" ", "") == "0%,2MiB", ("GPU not idle before run", st0["gpu"])
DEV = ("l2_common.py", "l2_net.py", "l2_a_semantics2.py", "run_l2.sh")
dev_sha = {f: C.sha256(os.path.join(C.L2, "devices", f)) for f in DEV}
POP_RECEIPT = os.path.join(C.L2, "receipts", "RECEIPT_L2_A_population.json")
POP_SHA = "5696948998072f6bee0e98e8832fe9b45e56d5e45b2cc5736086299f469bfc0e"
LISTING = os.path.join(C.L2, "out", "L2_A_listing.json")
CACHE = "/workspace/data/dlnative_5m_wide829_f16_ext.npz"
assert C.sha256(POP_RECEIPT) == POP_SHA, "population receipt sha changed"
pr = json.load(open(POP_RECEIPT))
pop42 = pr["per_seed"]["42"]["out"]; assert C.sha256(pop42) == pr["per_seed"]["42"]["out_sha256"]
YEARS = (2022, 2023, 2024, 2025, 2026); DAY = 86400; KPFX = "/data/futures/um/daily/klines/"
lim = N.Limiter(); cli = N.Client(lim)
rep = dict(device="l2_a_semantics2.py", device_sha256=dev_sha, env=envrep, sys_before=st0, cache=dict(path=CACHE, sha256=C.sha256(CACHE)),
           listing=dict(path=LISTING, sha256=C.sha256(LISTING)), population_receipt_sha256=POP_SHA)
LJ = json.load(open(LISTING))
listed = {s: set(calendar.timegm(time.strptime(d, "%Y-%m-%d")) // DAY for d in v["zip_dates"]) for s, v in LJ.items()}
Z = np.load(pop42); P42 = Z["P"]; ts42 = Z["ts"]; SYM = [str(x) for x in Z["symbols"]]; SIDX = {s: k for k, s in enumerate(SYM)}
yr = C.year_of(ts42)


def dstr(d):
    return time.strftime("%Y-%m-%d", time.gmtime(d * DAY))


pairs_by_year = {}
for y in YEARS:   # identical construction and rng stream to l2_a_archive.py (3); first 8 of the sorted draw
    pairs = set()
    for i in np.nonzero(yr == y)[0]:
        d = int(ts42[i]) // DAY
        for n in np.nonzero(P42[i])[0]:
            pairs.add((SYM[n], d))
    pairs = sorted(p for p in pairs if (p[1] in listed[p[0]] and (p[1] - 1) in listed[p[0]]))
    rng = np.random.default_rng([20260913, y])
    pick = rng.choice(len(pairs), size=min(200, len(pairs)), replace=False)
    samp = [pairs[k] for k in sorted(pick)]
    sub = np.random.default_rng([20260913, y, 2]).choice(len(samp), size=min(20, len(samp)), replace=False)
    pairs_by_year[y] = [samp[k] for k in sorted(sub)]


def get_zip_csv(path):
    st, body = cli.get("data.binance.vision", path)
    if st != 200:
        return st, None, None
    st2, cb = cli.get("data.binance.vision", path + ".CHECKSUM")
    import hashlib
    ok = bool(st2 == 200 and cb.decode().split()[0].lower() == hashlib.sha256(body).hexdigest())
    z = zipfile.ZipFile(io.BytesIO(body)); txt = z.read(z.namelist()[0]).decode("utf-8-sig")
    return 200, ok, txt


def klines(sym, iv, d):
    st, ok, txt = get_zip_csv("%s%s/%s/%s-%s-%s.zip" % (KPFX, sym, iv, sym, iv, dstr(d)))
    if st != 200:
        return st, ok, None
    rows = [r for r in csv.reader(io.StringIO(txt)) if r and r[0].strip().isdigit()]
    A = np.array([[float(r[0]), float(r[4]), float(r[5]), float(r[7]), float(r[9]), float(r[10])] for r in rows], np.float64)
    return 200, ok, dict(open_ms=A[:, 0].astype(np.int64), close=A[:, 1], vol=A[:, 2], qvol=A[:, 3], tbv=A[:, 4], tbq=A[:, 5])


def one(pair):
    sym, d = pair
    out = dict(sym=sym, day=dstr(d))
    f = N.fetch_day(cli, sym, dstr(d), with_checksum=True); out["metrics_status"] = f["status"]; out["metrics_checksum_ok"] = f["checksum_ok"]
    out["metrics"] = N.parse_day(f["body"], sym, dstr(d)) if f["body"] is not None else None
    k1 = {}
    for dd in (d - 1, d, d + 1):
        st, ok, K = klines(sym, "1m", dd); k1[dd] = K; out["k1m_%s" % dstr(dd)] = (st, ok)
    st, ok, K5 = klines(sym, "5m", d); out["k5m"] = (st, ok)
    out["_k1"] = k1; out["_k5"] = K5
    return out


with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(one, [p for y in YEARS for p in pairs_by_year[y]]))
Zc = np.load(CACHE, allow_pickle=True); ch = [str(x) for x in Zc["ch"]]; assert ch[6] == "tbf", ch
assert [str(x) for x in Zc["symbols"]] == SYM
cts = Zc["ts"].astype(np.int64); assert np.all(np.diff(cts) == 300)
TBF = np.array(Zc["data"][:, :, 6], dtype=np.float32)
OFF_C = list(range(-2, 3)); OFF_M = list(range(-10, 11))
K1n = {c: [0, 0] for c in OFF_C}; K1q = {c: [0, 0] for c in OFF_C}
K2b = {o: [0, 0] for o in OFF_M}; K2q = {o: [0, 0] for o in OFF_M}; K2corr = {o: [0.0, 0.0, 0.0, 0] for o in OFF_M}
K3 = {o: [] for o in OFF_M}
per_pair = []
for r in res:
    sym = r["sym"]; n = SIDX[sym]; row = dict(sym=sym, day=r["day"], metrics=r["metrics_status"], metrics_checksum=r["metrics_checksum_ok"], k5m=r["k5m"])
    K5 = r["_k5"]
    if K5 is not None:
        ok = K5["vol"] > 0; tb_b = np.where(ok, K5["tbv"] / np.where(ok, K5["vol"], 1), np.nan); tb_q = np.where(K5["qvol"] > 0, K5["tbq"] / np.where(K5["qvol"] > 0, K5["qvol"], 1), np.nan)
        for c in OFF_C:
            k = (K5["open_ms"] // 1000 - cts[0]) // 300 + c; inb = (k >= 0) & (k < cts.size)
            cv = np.full(k.size, np.nan); cv[inb] = TBF[k[inb], n]
            for arr, acc in ((tb_b, K1n), (tb_q, K1q)):
                v = np.isfinite(arr) & np.isfinite(cv)
                acc[c][0] += int((np.abs(arr[v] - cv[v]) <= 1.5e-3).sum()); acc[c][1] += int(v.sum())
    M = r["metrics"]; k1 = r["_k1"]; fk2 = {}; fk3 = {}
    if M is not None and M["ts"] is not None and all(k1[dd] is not None for dd in k1):
        ko = np.concatenate([k1[dd]["open_ms"] for dd in sorted(k1)]) // 1000
        kc = np.concatenate([k1[dd]["close"] for dd in sorted(k1)]); kv = np.concatenate([k1[dd]["vol"] for dd in sorted(k1)])
        kq = np.concatenate([k1[dd]["qvol"] for dd in sorted(k1)]); ktb = np.concatenate([k1[dd]["tbv"] for dd in sorted(k1)]); ktq = np.concatenate([k1[dd]["tbq"] for dd in sorted(k1)])
        assert np.all(np.diff(ko) == 60), ("1m klines not contiguous", sym, r["day"])
        pos = {int(t): q for q, t in enumerate(ko)}
        T = M["ts"]; R = M["X"][:, 5]; OIQ = M["X"][:, 0]; OIV = M["X"][:, 1]
        for o in OFF_M:
            st_ = T + o * 60
            idx = np.array([pos.get(int(t), -1) for t in st_])
            good = (idx >= 0) & (idx + 5 <= ko.size) & np.isfinite(R) & (R > 0)
            if good.any():
                g = idx[good]
                sb = np.array([ktb[q:q + 5].sum() for q in g]); vb = np.array([kv[q:q + 5].sum() for q in g])
                sq = np.array([ktq[q:q + 5].sum() for q in g]); vq = np.array([kq[q:q + 5].sum() for q in g])
                with np.errstate(divide="ignore", invalid="ignore"):
                    rb = sb / (vb - sb); rq = sq / (vq - sq)
                Rg = R[good]
                vb_ok = np.isfinite(rb) & (rb > 0); vq_ok = np.isfinite(rq) & (rq > 0)
                K2b[o][0] += int((np.abs(Rg[vb_ok] / rb[vb_ok] - 1) <= 1e-4).sum()); K2b[o][1] += int(vb_ok.sum())
                fk2["base_%d" % o] = float((np.abs(Rg[vb_ok] / rb[vb_ok] - 1) <= 1e-4).mean()) if vb_ok.any() else None
                fk2["quote_%d" % o] = float((np.abs(Rg[vq_ok] / rq[vq_ok] - 1) <= 1e-4).mean()) if vq_ok.any() else None
                K2q[o][0] += int((np.abs(Rg[vq_ok] / rq[vq_ok] - 1) <= 1e-4).sum()); K2q[o][1] += int(vq_ok.sum())
                if vb_ok.sum() > 20:
                    a = np.log(Rg[vb_ok]); b = np.log(rb[vb_ok]); a = a - a.mean(); b = b - b.mean()
                    K2corr[o][0] += float((a * b).sum()); K2corr[o][1] += float((a * a).sum()); K2corr[o][2] += float((b * b).sum()); K2corr[o][3] += int(vb_ok.sum())
            # K3: close of the minute ending at T + o*60 = bar with open T + (o-1)*60
            idx3 = np.array([pos.get(int(t) - 60, -1) for t in st_])
            g3 = (idx3 >= 0) & np.isfinite(OIQ) & np.isfinite(OIV) & (OIQ > 0)
            if g3.any():
                K3[o].extend(list(np.abs((OIV[g3] / OIQ[g3]) / kc[idx3[g3]] - 1)))
                fk3[o] = float(np.median(np.abs((OIV[g3] / OIQ[g3]) / kc[idx3[g3]] - 1)))
    cls = [k for k, v in fk2.items() if v is not None and v >= 0.90]
    row.update(taker_ratio_finite=(float(np.isfinite(M["X"][:, 5]).mean()) if (M is not None and M["ts"] is not None and M["n_rows"]) else None),
               k2_class=(cls[0] if len(cls) == 1 else ("none" if not cls else "multi:" + ",".join(cls))),
               k2_best=(max(fk2, key=lambda k: fk2[k] if fk2[k] is not None else -1) if fk2 else None),
               k2_best_rate=(max((v for v in fk2.values() if v is not None), default=None)),
               k3_best_minute=(min(fk3, key=lambda o: fk3[o]) if fk3 else None), k3_best_median=(min(fk3.values()) if fk3 else None))
    per_pair.append(row)
k1b = {str(c): dict(match=K1n[c][0], n=K1n[c][1], rate=K1n[c][0] / max(K1n[c][1], 1)) for c in OFF_C}
k1q = {str(c): dict(match=K1q[c][0], n=K1q[c][1], rate=K1q[c][0] / max(K1q[c][1], 1)) for c in OFF_C}
k2b = {str(o): dict(match=K2b[o][0], n=K2b[o][1], rate=K2b[o][0] / max(K2b[o][1], 1)) for o in OFF_M}
k2q = {str(o): dict(match=K2q[o][0], n=K2q[o][1], rate=K2q[o][0] / max(K2q[o][1], 1)) for o in OFF_M}
k2c = {str(o): (K2corr[o][0] / np.sqrt(K2corr[o][1] * K2corr[o][2]) if K2corr[o][1] > 0 else None) for o in OFF_M}
k3 = {str(o): dict(n=len(K3[o]), median_abs_rel=float(np.median(K3[o])) if K3[o] else None, share_le_5e4=float(np.mean(np.array(K3[o]) <= 5e-4)) if K3[o] else None) for o in OFF_M}
best = lambda d: max(d, key=lambda k: d[k]["rate"])
rep.update(pairs=per_pair, http=dict(cli.counts), requests=cli.n_requests,
           K1_cache_vs_5m_kline_tbf=dict(base=k1b, quote=k1q, best_base=best(k1b), best_quote=best(k1q),
                                          meaning="offset c: cache row ts = kline open_time + c*300; c=0 => cache labels bars by OPEN time, c=+1 => by CLOSE time"),
           K2_metrics_taker_ratio_window=dict(base=k2b, quote=k2q, corr_log_base=k2c, best_base=best(k2b), best_quote=best(k2q),
                                              meaning="offset o (min): metrics label T equals buy/sell over 1m bars opening in [T+o, T+o+5min)"),
           K3_oi_snapshot_minute=dict(by_offset=k3, best=min((o for o in k3 if k3[o]["median_abs_rel"] is not None), key=lambda o: k3[o]["median_abs_rel"]),
                                      meaning="offset o (min): OI value/qty at label T matches the 1m close at T+o (price level used only to locate the minute)"))
st1 = C.sysstate(); st1["collector_333197"] = N.collector_state(); rep["sys_after"] = st1; rep["wall_s"] = round(time.time() - T_START, 1)
classes = {}
for p in per_pair:
    key = (p["day"][:4], p.get("k2_class"))
    classes["%s|%s" % key] = classes.get("%s|%s" % key, 0) + 1
rep["K2_file_classes_by_year"] = classes
rep["K3_best_minute_by_year"] = {}
for p in per_pair:
    k = "%s|%s" % (p["day"][:4], p.get("k3_best_minute")); rep["K3_best_minute_by_year"][k] = rep["K3_best_minute_by_year"].get(k, 0) + 1
C.jdump(rep, os.path.join(C.L2, "receipts", "RECEIPT_L2_A_semantics2.json"))
for p in per_pair:
    print("FILE %s %s taker_finite=%s class=%s best=%s %.3f k3=%s" % (p["sym"], p["day"], p.get("taker_ratio_finite"), p.get("k2_class"), p.get("k2_best"), p.get("k2_best_rate") or -1, p.get("k3_best_minute")), flush=True)
print("CLASSES %s" % json.dumps(classes, sort_keys=True), flush=True)
print("K3BEST %s" % json.dumps(rep["K3_best_minute_by_year"], sort_keys=True), flush=True)
print("K1 base %s | quote %s" % ({c: round(v["rate"], 4) for c, v in k1b.items()}, {c: round(v["rate"], 4) for c, v in k1q.items()}), flush=True)
print("K2 base %s" % {o: round(v["rate"], 4) for o, v in k2b.items()}, flush=True)
print("K2 quote %s" % {o: round(v["rate"], 4) for o, v in k2q.items()}, flush=True)
print("K2 corr %s" % {o: (round(v, 3) if v is not None else None) for o, v in k2c.items()}, flush=True)
print("K3 %s" % {o: (round(v["median_abs_rel"], 6) if v["median_abs_rel"] is not None else None) for o, v in k3.items()}, flush=True)
g1 = [c for c in k1b if k1b[c]["rate"] >= 0.95] + [c for c in k1q if k1q[c]["rate"] >= 0.95]
g2 = [o for o in k2b if k2b[o]["rate"] >= 0.95] + [o for o in k2q if k2q[o]["rate"] >= 0.95]
assert st1["gpu"].replace(" ", "") == "0%,2MiB", ("GPU not idle after run", st1["gpu"])
assert len(set(g1)) == 1, ("GATE K1: no unique cache offset with match >= 0.95", g1)
print("SUMMARY l2_a_semantics2 OK K1_cache_offset=%s K2_pooled_best_base=%s K2_pooled_best_quote=%s K3_oi_minute=%s requests=%d wall=%.0fs" % (
    g1[0], rep["K2_metrics_taker_ratio_window"]["best_base"], rep["K2_metrics_taker_ratio_window"]["best_quote"], rep["K3_oi_snapshot_minute"]["best"], cli.n_requests, rep["wall_s"]), flush=True)
