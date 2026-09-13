"""l2_a_archive.py — L2 Stage A part 2 (pod2; public data.binance.vision archive only; DATA FACTS ONLY, no return number).
(1) listing: S3 ListObjectsV2 of futures/um/daily/metrics for every symbol in the Stage A population request set, two independent
    passes; per-symbol key sets must be identical and every listing must complete (a failed page is never read as 'no data');
(2) coverage of the A0 fund-leg short population by the archive listing, per seed and year, by row count and by short gross |smr|:
    P_all (member ∧ smr<0 ∧ fund component<0) and P_neg (P_all ∧ device rn8<0). Row (i,n) is covered iff every UTC day touched by the
    feature window [E_i − 24h − 10min, E_i − 10min] is listed;
(3) stratified sample: per year 200 population (symbol, day d) pairs + their day d−1, zip + CHECKSUM → hit rates: create_time on the
    5-min grid; rows per day; day-window labelling (00:00..23:55 vs 00:05..24:00); per-column finite / positive shares; CHECKSUM match;
    anchor hits (stamp E−10min and E−5min present) for the sampled population anchors;
(4) alignment spectra on NON-RETURN relations. RUN 2 convention (run 1 failed its S1 gate because I took cache ts as bar OPEN time;
    l2_a_semantics/semantics2/switch receipts then pinned, with explicit-open_time public klines: cache ts = bar CLOSE time (K1 0.9999/1.0);
    archive labels = window END up to 2024-03-03 and window START from 2024-03-04 (BTC and ETH switch the same UTC day; OI snapshot at T
    vs T+5min flips the same day)). Window lag ℓ = cache offset s − s0, s0 = 0 before 2024-03-04 (cache bar closing at T = [T−5m,T)),
    s0 = +1 from 2024-03-04 (bar closing at T+5m = [T,T+5m)); ℓ = 0 ≡ the 5-minute window the label denotes.
    S1: pooled within-file Pearson of log(taker buy/sell vol ratio) vs logit(cache tbf) at ℓ ∈ {−3..+3} (identical pair set), per regime and per year;
    S2: pooled within-(symbol,day) Pearson of the metrics 24h taker buy share over labels [E−24h, E) vs panel f_tbf_24h at row j(E)+a,
        a ∈ {−3..+3} (identical anchor set). Gates (asserted after the receipt is written): argmax_ℓ S1 == 0 in BOTH regimes;
        argmax S2 == 0; grid hit rate ≥ 0.99;
(5) the empty-population anchors explained from rec (w3_fund, gross_total, nsel) and the T1SMR fund component.
Never reads META y4, PANEL Y4/Y24/f_rev*/f_mom*, or cache channel ret5 (only channel 'tbf' is kept; asserted by name)."""
import os, sys, time, json, calendar
import numpy as np
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import l2_common as C
import l2_net as N

T_START = time.time()
envrep = C.check_env(sys.argv)
st0 = C.sysstate(); st0["collector_333197"] = N.collector_state()
assert st0["gpu"].replace(" ", "") == "0%,2MiB", ("GPU not idle before run", st0["gpu"])
DEV = ("l2_common.py", "l2_net.py", "l2_a_archive.py", "run_l2.sh")
SEM2 = os.path.join(C.L2, "receipts", "RECEIPT_L2_A_semantics2.json"); SEM2_SHA = "7e006bc70d732a65d1a92f1c98dadacc38a70084b71217e12f31d55ed39c3bb8"
SWITCH = os.path.join(C.L2, "receipts", "RECEIPT_L2_A_switch.json"); SWITCH_SHA = "ea9f0230e819b2d17787a682eb86e0d1e73344149129b1508d1886c8ae5f641c"
assert C.sha256(SEM2) == SEM2_SHA and C.sha256(SWITCH) == SWITCH_SHA, "semantics receipts changed"
SWITCH_DAY = calendar.timegm((2024, 3, 4, 0, 0, 0)) // 86400   # first UTC day with window-START labels (RECEIPT_L2_A_switch days rows)
dev_sha = {f: C.sha256(os.path.join(C.L2, "devices", f)) for f in DEV}
inputs = C.input_shas(check=True)
POP_RECEIPT = os.path.join(C.L2, "receipts", "RECEIPT_L2_A_population.json")
POP_SHA = "5696948998072f6bee0e98e8832fe9b45e56d5e45b2cc5736086299f469bfc0e"   # RECEIPT_L2_A_population.json (run aee26103, 11:14:47Z)
CACHE = "/workspace/data/dlnative_5m_wide829_f16_ext.npz"
assert C.sha256(POP_RECEIPT) == POP_SHA, "population receipt sha changed"
pr = json.load(open(POP_RECEIPT))
pop_files = {s: pr["per_seed"][s]["out"] for s in C.SEEDS}
for s in C.SEEDS:
    assert C.sha256(pop_files[s]) == pr["per_seed"][s]["out_sha256"], ("population npz sha changed", s)
SYMS = list(pr["metrics_request_scope_union_seeds"]["symbols_total"]); assert len(SYMS) == 618, len(SYMS)
D, readers = C.load_axis_and_masks()
SIDX = {s: k for k, s in enumerate(D["SYM"])}
YEARS = (2022, 2023, 2024, 2025, 2026); DAY = 86400
rep = dict(device="l2_a_archive.py", device_sha256=dev_sha, env=envrep, sys_before=st0, inputs=inputs,
           population_receipt=dict(path=POP_RECEIPT, sha256=C.sha256(POP_RECEIPT)), cache=dict(path=CACHE),
           semantics_receipts=dict(semantics2=SEM2_SHA, switch=SWITCH_SHA, switch_day="2024-03-04"),
           rate_rule="<=20 req/s global, 10 req/s while PID 333197 not stopped (lead AMENDMENT 1); hosts " + ",".join(sorted(N.HOSTS)))
lim = N.Limiter(); cli = N.Client(lim)


def dstr(d):
    return time.strftime("%Y-%m-%d", time.gmtime(d * DAY))


# ---------------------------------------------------------------- (1) listing, two passes
def run_listing():
    with ThreadPoolExecutor(8) as ex:
        return dict(zip(SYMS, ex.map(lambda s: N.list_symbol(cli, s), SYMS)))
LA = run_listing(); LB = run_listing()
RETRIES = {}
for _pass in (LA, LB):   # a failed page is retried (fresh listing of that symbol, up to 3 times); never read as 'no data'
    for _s in SYMS:
        _k = 0
        while not _pass[_s]["ok"] and _k < 3:
            time.sleep(5.0); _pass[_s] = N.list_symbol(cli, _s); _k += 1
        if _k:
            RETRIES[_s] = RETRIES.get(_s, 0) + _k
lst_fail = sorted(s for s in SYMS if not (LA[s]["ok"] and LB[s]["ok"]))
lst_mismatch = sorted(s for s in SYMS if LA[s]["ok"] and LB[s]["ok"] and (LA[s]["zip_dates"] != LB[s]["zip_dates"] or LA[s]["checksum_dates"] != LB[s]["checksum_dates"]))
assert not lst_fail, ("listing incomplete for", lst_fail[:20], len(lst_fail))
assert not lst_mismatch, ("two listing passes disagree for", lst_mismatch[:20], len(lst_mismatch))
listed = {s: set(calendar.timegm(time.strptime(d, "%Y-%m-%d")) // DAY for d in LA[s]["zip_dates"]) for s in SYMS}
chk_missing = {s: sorted(set(LA[s]["zip_dates"]) - set(LA[s]["checksum_dates"]))[:5] for s in SYMS if set(LA[s]["zip_dates"]) - set(LA[s]["checksum_dates"])}
lp = os.path.join(C.L2, "out", "L2_A_listing.json")
C.jdump({s: dict(zip_dates=LA[s]["zip_dates"], checksum_dates=LA[s]["checksum_dates"], pages=LA[s]["pages"]) for s in SYMS}, lp)
first_dates = [LA[s]["zip_dates"][0] for s in SYMS if LA[s]["zip_dates"]]
rep["listing"] = dict(symbols=len(SYMS), passes_identical=True, listing_retries=RETRIES, symbols_with_no_keys=sorted(s for s in SYMS if not LA[s]["zip_dates"]),
                      zip_keys_total=int(sum(len(LA[s]["zip_dates"]) for s in SYMS)), symbols_zip_without_checksum=len(chk_missing),
                      zip_without_checksum_examples=dict(list(chk_missing.items())[:10]), pages_total=int(sum(LA[s]["pages"] + LB[s]["pages"] for s in SYMS)),
                      earliest_date=min(first_dates) if first_dates else None, out=lp, out_sha256=C.sha256(lp))
print("listing ok: %d symbols, %d zip keys, %d with no keys" % (len(SYMS), rep["listing"]["zip_keys_total"], len(rep["listing"]["symbols_with_no_keys"])), flush=True)

# ---------------------------------------------------------------- (2) coverage of the population by the listing
yr = C.year_of(D["PTS"][:C.N_FULL])
cov = {}
for s in C.SEEDS:
    Z = np.load(pop_files[s]); P = Z["P"]; SMR = Z["smr"].astype(np.float64); RN8 = Z["rn8_device"].astype(np.float64); ts = Z["ts"]
    assert np.array_equal(ts, D["PTS"][:C.N_FULL]) and [str(x) for x in Z["symbols"]] == D["SYM"]
    PN = P & (RN8 < 0.0)
    cov_mask = np.zeros_like(P)
    for n in np.nonzero(P.any(axis=0))[0]:
        sym = D["SYM"][n]
        L = listed.get(sym, set())
        rows = np.nonzero(P[:, n])[0]
        d_lo = (ts[rows] - DAY - 600) // DAY; d_hi = (ts[rows] - 600) // DAY
        ok = np.array([all(d in L for d in range(int(a), int(b) + 1)) for a, b in zip(d_lo, d_hi)], bool)
        cov_mask[rows[ok], n] = True
    tab = {}
    for y in YEARS:
        r = yr == y
        for nm, M in (("P_all", P), ("P_neg", PN)):
            m = M[r]; g = np.abs(SMR[r]) * m; c = cov_mask[r] & m
            tab.setdefault(str(y), {})[nm] = dict(rows=int(m.sum()), covered_rows=int(c.sum()), share_rows=float(c.sum() / max(m.sum(), 1)),
                                                  gross=float(g.sum()), covered_gross=float((np.abs(SMR[r]) * c).sum()),
                                                  share_gross=float((np.abs(SMR[r]) * c).sum() / max(g.sum(), 1e-300)))
    years_ge50 = [y for y in YEARS if tab[str(y)]["P_all"]["share_gross"] >= 0.5]
    cov[s] = dict(by_year=tab, years_share_gross_ge_0p5_P_all=years_ge50,
                  years_share_gross_ge_0p5_P_neg=[y for y in YEARS if tab[str(y)]["P_neg"]["share_gross"] >= 0.5])
    np.savez_compressed(os.path.join(C.L2, "out", "L2_A_listing_cover_s%s.npz" % s), covered=cov_mask)
    print("seed %s coverage by listing (P_all share of short gross): %s" % (s, {y: round(tab[str(y)]["P_all"]["share_gross"], 3) for y in YEARS}), flush=True)
rep["coverage_by_listing"] = cov

# ---------------------------------------------------------------- (5) empty population rows
emp = {}
for s in C.SEEDS:
    A = C.load_arm(s, D); P = np.load(pop_files[s])["P"]
    e = np.nonzero(P.sum(axis=1) == 0)[0]; c = A["cols"]; rec = A["rec"]
    fund_abs = np.abs(A["SMRC"][e, C.FUND, :].astype(np.float64)).sum(axis=1) if e.size else np.zeros(0)
    runs = []
    if e.size:
        a = e[0]; b = e[0]
        for x in e[1:]:
            if x != b + 1:
                runs.append((a, b)); a = x
            b = x
        runs.append((a, b))
    emp[s] = dict(n=int(e.size), by_year={str(y): int((yr[e] == y).sum()) for y in YEARS},
                  runs=[[C.utc(A["ts"][a]), C.utc(A["ts"][b]), int(b - a + 1)] for a, b in runs],
                  w3_fund_zero=int((rec[e, c.index("w3_fund")] == 0).sum()), gross_total_positive=int((rec[e, c.index("gross_total")] > 0).sum()),
                  fund_component_identically_zero=int((fund_abs == 0).sum()), nsel_min=float(rec[e, c.index("nsel")].min()) if e.size else None,
                  rows_all_fund_component_below_dust=int((np.abs(A["SMRC"][e, C.FUND, :].astype(np.float64)).max(axis=1) <= C.DUST).sum()) if e.size else 0,
                  max_abs_fund_component=float(np.abs(A["SMRC"][e, C.FUND, :].astype(np.float64)).max()) if e.size else None)
    del A
rep["empty_population_rows"] = emp
print("empty population rows: %s" % json.dumps({s: {k: emp[s][k] for k in ("n", "w3_fund_zero", "gross_total_positive", "fund_component_identically_zero", "rows_all_fund_component_below_dust", "max_abs_fund_component")} for s in C.SEEDS}), flush=True)

# ---------------------------------------------------------------- (3) stratified sample + hit rates
Z42 = np.load(pop_files["42"]); P42 = Z42["P"]; ts42 = Z42["ts"]
sample = {}
for y in YEARS:
    rows = np.nonzero(yr == y)[0]
    pairs = set()
    for i in rows:
        d = int(ts42[i]) // DAY
        for n in np.nonzero(P42[i])[0]:
            pairs.add((D["SYM"][n], d))
    pairs = sorted(p for p in pairs if (p[1] in listed[p[0]] and (p[1] - 1) in listed[p[0]]))
    rng = np.random.default_rng([20260913, y])
    pick = rng.choice(len(pairs), size=min(200, len(pairs)), replace=False)
    sample[y] = [pairs[k] for k in sorted(pick)]
jobs = sorted(set((sym, dd) for y in YEARS for (sym, d) in sample[y] for dd in (d - 1, d)))
def fetch(job):
    sym, d = job
    f = N.fetch_day(cli, sym, dstr(d), with_checksum=True)
    out = dict(sym=sym, day=d, status=f["status"], zip_sha256=f["zip_sha256"], checksum_ok=f["checksum_ok"])
    if f["body"] is not None:
        p = N.parse_day(f["body"], sym, dstr(d)); out.update(parsed=p, zip_bytes=len(f["body"]))
    return out
with ThreadPoolExecutor(8) as ex:
    got = list(ex.map(fetch, jobs))
G = {(g["sym"], g["day"]): g for g in got}
hr = {}
for y in YEARS:
    files = [G[(sym, dd)] for (sym, d) in sample[y] for dd in (d - 1, d)]
    ok = [f for f in files if f["status"] == 200 and f["parsed"]["ts"] is not None]
    nrow = sum(f["parsed"]["n_rows"] for f in ok)
    grid = sum(int((f["parsed"]["ts"] % 300 == 0).sum()) for f in ok)
    same_day = sum(int((f["parsed"]["ts"] // DAY == f["day"]).sum()) for f in ok)
    labA = sum(int(np.array_equal(np.unique(f["parsed"]["ts"]), f["day"] * DAY + 300 * np.arange(288))) for f in ok)
    labB = sum(int(np.array_equal(np.unique(f["parsed"]["ts"]), f["day"] * DAY + 300 * np.arange(1, 289))) for f in ok)
    dup = sum(int(f["parsed"]["n_rows"] - np.unique(f["parsed"]["ts"]).size) for f in ok)
    first_off = {}; last_off = {}
    for f in ok:
        if f["parsed"]["n_rows"]:
            a = int(f["parsed"]["ts"].min() - f["day"] * DAY); b = int(f["parsed"]["ts"].max() - f["day"] * DAY)
            first_off[a] = first_off.get(a, 0) + 1; last_off[b] = last_off.get(b, 0) + 1
    X = np.concatenate([f["parsed"]["X"] for f in ok]) if ok else np.zeros((0, 6))
    colstat = {c: dict(finite=float(np.isfinite(X[:, q]).mean()) if len(X) else None, positive=float((X[:, q] > 0).mean()) if len(X) else None)
               for q, c in enumerate(N.COLS)}
    anc_hit10 = anc_hit5 = anc_hit15 = anc_datatime10 = anc_n = 0
    for (sym, d) in sample[y]:
        f = G[(sym, d)]
        if f["status"] != 200 or f["parsed"]["ts"] is None:
            continue
        S = set(int(t) for t in f["parsed"]["ts"]); fp = G[(sym, d - 1)]
        if fp["status"] == 200 and fp["parsed"]["ts"] is not None:
            S |= set(int(t) for t in fp["parsed"]["ts"])
        n = SIDX[sym]
        for i in np.nonzero((ts42 // DAY) == d)[0]:
            if P42[i, n]:
                anc_n += 1; anc_hit10 += int(int(ts42[i]) - 600 in S); anc_hit5 += int(int(ts42[i]) - 300 in S); anc_hit15 += int(int(ts42[i]) - 900 in S)
                anc_datatime10 += int((int(ts42[i]) - (600 if d < SWITCH_DAY else 900)) in S)   # label whose data time is E-10min under its regime
    hr[str(y)] = dict(pairs=len(sample[y]), files=len(files), status={str(k): sum(1 for f in files if f["status"] == k) for k in set(f["status"] for f in files)},
                      checksum_ok=sum(1 for f in files if f["checksum_ok"] is True), checksum_bad=[(f["sym"], dstr(f["day"]), f["checksum_ok"]) for f in files if f["status"] == 200 and f["checksum_ok"] is not True][:10],
                      member_ok=sum(1 for f in ok if f["parsed"]["member_ok"]), crc_ok=sum(1 for f in ok if f["parsed"]["crc_ok"]),
                      parse_errors={k: sum(f["parsed"]["errors"].get(k, 0) for f in ok) for k in set(k for f in ok for k in f["parsed"]["errors"])},
                      rows=nrow, grid_hit_rate=float(grid / max(nrow, 1)), same_day_rate=float(same_day / max(nrow, 1)), duplicate_rows=dup,
                      complete_days_label_0000_2355=labA, complete_days_label_0005_2400=labB, first_label_offset_s=first_off, last_label_offset_s=last_off,
                      columns=colstat, anchor_rows=anc_n, anchor_hit_rate_Eminus10min=float(anc_hit10 / max(anc_n, 1)),
                      anchor_hit_rate_Eminus5min=float(anc_hit5 / max(anc_n, 1)), anchor_hit_rate_Eminus15min=float(anc_hit15 / max(anc_n, 1)),
                      anchor_hit_rate_datatime_Eminus10min=float(anc_datatime10 / max(anc_n, 1)))
    print("sample %d: files %d grid %.5f labA %d labB %d anchor_hit10 %.4f" % (y, len(files), hr[str(y)]["grid_hit_rate"], labA, labB, hr[str(y)]["anchor_hit_rate_Eminus10min"]), flush=True)
all_rows = sum(hr[str(y)]["rows"] for y in YEARS)
grid_all = sum(hr[str(y)]["grid_hit_rate"] * hr[str(y)]["rows"] for y in YEARS) / max(all_rows, 1)
rep["sample_hit_rates"] = dict(by_year=hr, grid_hit_rate_all=grid_all, http=dict(cli.counts), requests=cli.n_requests, bytes=cli.bytes)
GATES = dict(hit_grid_ge_0p99=bool(grid_all >= 0.99))

# ---------------------------------------------------------------- (4) spectra
t0 = time.time()
Zc = np.load(CACHE, allow_pickle=True)
ch = [str(x) for x in Zc["ch"]]; assert ch[6] == "tbf", ch
csym = [str(x) for x in Zc["symbols"]]; assert csym == D["SYM"], "cache symbols vs panel"
cts = Zc["ts"].astype(np.int64); assert np.all(np.diff(cts) == 300), "cache ts not contiguous 5-min"
TBF = np.array(Zc["data"][:, :, 6], dtype=np.float32)
rep["cache"].update(sha256=C.sha256(CACHE), channels=ch, used_channel="tbf", rows=int(cts.size), first=C.utc(cts[0]), last=C.utc(cts[-1]),
                    load_s=round(time.time() - t0, 1))
SH = list(range(-3, 4))
REG = ("END_pre_2024-03-04", "START_from_2024-03-04")
acc1 = {g: {s: [0.0, 0.0, 0.0] for s in SH} for g in REG}; npair = {g: 0 for g in REG}; nfile = {g: 0 for g in REG}
s1_year = {str(y): {s: [0.0, 0.0, 0.0] for s in SH} for y in YEARS}
for y in YEARS:
    for (sym, d) in sample[y]:
        f = G[(sym, d)]
        if f["status"] != 200 or f["parsed"]["ts"] is None or f["parsed"]["n_rows"] < 50:
            continue
        T = f["parsed"]["ts"]; r = f["parsed"]["X"][:, 5]; n = SIDX[sym]
        g = REG[0] if d < SWITCH_DAY else REG[1]; s0 = 0 if d < SWITCH_DAY else 1
        idx0 = (T - cts[0]) // 300 + s0
        valid = np.isfinite(r) & (r > 0) & (T % 300 == 0)
        ys = {}
        for s in SH:
            k = idx0 + s; inb = (k >= 0) & (k < cts.size)
            v = np.full(T.size, np.nan); v[inb] = TBF[k[inb], n].astype(np.float64)
            ys[s] = v; valid &= np.isfinite(v) & (v > 0) & (v < 1)
        if valid.sum() < 50:
            continue
        x = np.log(r[valid]); x = (x - x.mean()) / (x.std() + 1e-300)
        nfile[g] += 1; npair[g] += int(valid.sum())
        for s in SH:
            v = ys[s][valid]; v = np.log(v / (1 - v)); v = (v - v.mean()) / (v.std() + 1e-300)
            q = acc1[g][s]; q[0] += float((x * v).sum()); q[1] += float((x * x).sum()); q[2] += float((v * v).sum())
            q = s1_year[str(y)][s]; q[0] += float((x * v).sum()); q[1] += float((x * x).sum()); q[2] += float((v * v).sum())
S1 = {g: {s: (acc1[g][s][0] / np.sqrt(acc1[g][s][1] * acc1[g][s][2]) if acc1[g][s][1] > 0 else float("nan")) for s in SH} for g in REG}
s1_peak = {g: max(SH, key=lambda s: S1[g][s] if np.isfinite(S1[g][s]) else -9) for g in REG}
S1y = {y: {s: (q[0] / np.sqrt(q[1] * q[2]) if q[1] > 0 else None) for s, q in v.items()} for y, v in s1_year.items()}
# S2 anchor-level vs panel f_tbf_24h
P = readers["PANEL"]; TB24 = np.asarray(P["f_tbf_24h"], np.float64); prow = {int(t): j for j, t in enumerate(D["PTS"])}
num2 = {a: 0.0 for a in SH}; dx2 = {a: 0.0 for a in SH}; dy2 = {a: 0.0 for a in SH}; n2 = 0; groups2 = 0
for y in YEARS:
    for (sym, d) in sample[y]:
        f = G[(sym, d)]; fp = G[(sym, d - 1)]
        if f["status"] != 200 or fp["status"] != 200 or f["parsed"]["ts"] is None or fp["parsed"]["ts"] is None:
            continue
        T = np.concatenate([fp["parsed"]["ts"], f["parsed"]["ts"]]); r = np.concatenate([fp["parsed"]["X"][:, 5], f["parsed"]["X"][:, 5]])
        n = SIDX[sym]; Ms = []; Fs = {a: [] for a in SH}
        for h in range(6):
            E = d * DAY + h * 14400; j = prow.get(E)
            if j is None or j - 3 < 0 or j + 3 >= C.N_REC:
                continue
            w = (T >= E - DAY) & (T < E) & np.isfinite(r) & (r > 0)
            if w.sum() < 280:
                continue
            fv = [TB24[j + a, n] for a in SH]
            if not all(np.isfinite(fv)):
                continue
            Ms.append(float(np.mean(r[w] / (1 + r[w]))))
            for a, v in zip(SH, fv):
                Fs[a].append(float(v))
        if len(Ms) < 3:
            continue
        m = np.array(Ms); m -= m.mean(); groups2 += 1; n2 += len(Ms)
        for a in SH:
            v = np.array(Fs[a]); v -= v.mean()
            num2[a] += float((m * v).sum()); dx2[a] += float((m * m).sum()); dy2[a] += float((v * v).sum())
S2 = {a: (num2[a] / np.sqrt(dx2[a] * dy2[a]) if dx2[a] > 0 and dy2[a] > 0 else float("nan")) for a in SH}
s2_peak = max(SH, key=lambda a: S2[a] if np.isfinite(S2[a]) else -9)
rep["spectra"] = dict(lag_convention="window lag l = cache offset - s0; s0 = 0 before 2024-03-04 (label = window END), s0 = +1 from 2024-03-04 (label = window START); cache ts = bar CLOSE",
                      S1=dict(pairs=npair, files=nfile, corr_by_lag={g: {str(s): S1[g][s] for s in SH} for g in REG}, peak=s1_peak, by_year_lag=S1y),
                      S2=dict(anchors=n2, symbol_days=groups2, corr_by_shift={str(a): S2[a] for a in SH}, peak=s2_peak))
for g in REG:
    print("S1 %s lag corr %s peak %d (files %d pairs %d)" % (g, {s: round(S1[g][s], 4) for s in SH}, s1_peak[g], nfile[g], npair[g]), flush=True)
print("S1 by year (window lag): %s" % json.dumps({y: {s: (round(v, 4) if v is not None else None) for s, v in d.items()} for y, d in S1y.items()}), flush=True)
print("S2 %s peak %d" % ({a: round(S2[a], 4) for a in SH}, s2_peak), flush=True)
rep["arrays_read"] = C.assert_no_returns_read(readers)
GATES.update(S1_peak_lag0_END=bool(s1_peak[REG[0]] == 0), S1_peak_lag0_START=bool(s1_peak[REG[1]] == 0), S2_peak_0=bool(s2_peak == 0))
st1 = C.sysstate(); st1["collector_333197"] = N.collector_state()
GATES["gpu_idle_after"] = bool(st1["gpu"].replace(" ", "") == "0%,2MiB")
rep["gates"] = GATES; rep["limiter_collector_states"] = lim.states; rep["sys_after"] = st1; rep["wall_s"] = round(time.time() - T_START, 1)
rep["http_final"] = dict(counts=dict(cli.counts), requests=cli.n_requests, bytes=cli.bytes)
C.jdump(rep, os.path.join(C.L2, "receipts", "RECEIPT_L2_A_archive.json"))
assert all(GATES.values()), ("STAGE A GATE FAILED", GATES)
print("SUMMARY l2_a_archive OK gates=%s listing=%d syms grid=%.5f cov_years_ge50(s42)=%s requests=%d wall=%.0fs" % (
    json.dumps(GATES), len(SYMS), grid_all, cov["42"]["years_share_gross_ge_0p5_P_all"], cli.n_requests, rep["wall_s"]), flush=True)
