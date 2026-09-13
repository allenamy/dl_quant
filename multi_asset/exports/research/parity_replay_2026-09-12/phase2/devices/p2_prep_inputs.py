#!/usr/bin/env python3
"""Phase 2 S0 input preparation (PREREG_producer_parity_phase2_oos_2026-09-12 + lead task S0). READ-ONLY on every source; writes only under
/workspace/uplift_r2_2026-09-13/P2/work. No book-level number. Products (all sha256 in receipts/P2_prep_inputs.json):
  work/ledger_full.npz   per-symbol settlement ledger on the 829 axis: off[830], ft[int64 s], rate[float64], src[int8], zip_iv[float32]
                         sources = Binance data-vision monthly zips (calc_time ms, funding_interval_hours, last_funding_rate) U fund_aug.json.gz (API pull, t ms, rate)
                         union by second = t_ms // 1000 (the producer's own key, shadow_loop_v3.py L338); on a second present in both with unequal rate the API row
                         (fund_aug) is kept (the producer reads the API) and the conflict is counted; src 1 = aug only, 2 = zip only, 3 = both equal, 4 = both unequal (aug kept)
  work/universe.npz      on the research panel axis (umask ts, 10039): pit = umask_UPIT_CRYPTO mask; trading24 = >=1 settlement in (E-24h, E]; pins = live_pins symbols_live (450)
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_prep_inputs.py PATH,HOME,LC_CTYPE"""
import os, sys, json, glob, gzip, hashlib, time, zipfile, io, csv, subprocess
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np
P2 = "/workspace/uplift_r2_2026-09-13/P2"; W = f"{P2}/work"; OUTR = f"{P2}/receipts/P2_prep_inputs.json"
def under(p): assert os.path.realpath(p).startswith(P2 + "/"), p; return p
T0 = time.time()
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def log(*a): print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)
R = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "env": dict(os.environ), "utc_start": iso(T0), "python": sys.version.split()[0], "numpy": np.__version__}
R["nvidia_smi_before"] = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
SRC = {"cache": "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz", "funding_dir": "/workspace/wide_multisrc/funding", "fund_aug": "/workspace/fund_aug.json.gz",
       "umask": "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz", "live_pins": "/workspace/live_pins.json"}
PIN = {"cache": "1d7f459dee434ec49e7714a2a612807f2e38e97f35c6c39471a8a4aaa7452488", "fund_aug": "8a9e771577602dd1875a87fb07f982bc2c255e740966f911469420a44a53a8c2",
       "umask": "47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5", "live_pins": "fd27fe485417d307e5bc41ee382a2db098118bee1fe2a13ebde98c7e7d3caece"}
for k, v in PIN.items():
    got = sha(SRC[k]); assert got == v, (k, got, v)
R["sources"] = {k: {"path": SRC[k], "sha256": PIN.get(k)} for k in SRC}
log("source shas pinned OK")

# ── cache: NO raw extract (attempt 1, 08:02Z, hit the /workspace quota with a 5.7 GB write; see receipts/P2_prep_inputs.attempt1_quota.log).
#    Consumers load the npz member in memory (one parent process, forked workers share pages copy-on-write). Only the symbol axis is read here.
Z = np.load(SRC["cache"], allow_pickle=True)
SYMS = [str(s) for s in Z["symbols"]]; SYM_SHA = hashlib.sha256("\n".join(SYMS).encode()).hexdigest(); assert SYM_SHA == "381b7f01eedcf31b6d6a94116a32855b545bf584b26f3000aa9545c81068c19a"
assert [str(c) for c in Z["ch"]] == ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"]
R["cache"] = {"path": SRC["cache"], "sha256": PIN["cache"], "symbols_sha256": SYM_SHA, "raw_extract": "none (quota)"}
del Z

# ── funding ledger ──
AUG = json.loads(gzip.open(SRC["fund_aug"], "rt").read())["rates"]
off = [0]; FT = []; RT = []; SR = []; ZI = []; stats = {"n_conflict": 0, "n_both_equal": 0, "n_aug_only": 0, "n_zip_only": 0, "near_dup_lt300s": 0, "zip_bad_rows": 0, "zip_same_second_unequal": 0,
                                                       "conflict_examples": [], "near_dup_examples": [], "symbols_no_rows": []}
for j, s in enumerate(SYMS):
    zrows = {}
    for zp in sorted(glob.glob(f"{SRC['funding_dir']}/{s}/*.zip")):
        with zipfile.ZipFile(zp) as zf:
            with zf.open(zf.namelist()[0]) as fh:
                rd = csv.reader(io.TextIOWrapper(fh))
                hdr = next(rd)
                assert [h.strip() for h in hdr] == ["calc_time", "funding_interval_hours", "last_funding_rate"], (zp, hdr)
                for row in rd:
                    if not row: continue
                    try: t = int(row[0]) // 1000; iv = float(row[1]); r = float(row[2])
                    except Exception: stats["zip_bad_rows"] += 1; continue
                    if t in zrows and zrows[t][0] != r: stats["zip_same_second_unequal"] += 1   # same second twice inside the zips with different rates: first kept, counted
                    zrows.setdefault(t, (r, iv))
    arows = {}
    for t_ms, r in AUG.get(s, []):
        arows.setdefault(int(t_ms) // 1000, float(r))
    keys = sorted(set(zrows) | set(arows))
    if not keys: stats["symbols_no_rows"].append(s)
    for t in keys:
        inz, ina = t in zrows, t in arows
        if inz and ina:
            if zrows[t][0] == arows[t]: src = 3; stats["n_both_equal"] += 1
            else:
                src = 4; stats["n_conflict"] += 1
                if len(stats["conflict_examples"]) < 20: stats["conflict_examples"].append([s, iso(t), zrows[t][0], arows[t]])
            r = arows[t]
        elif ina: src = 1; r = arows[t]; stats["n_aug_only"] += 1
        else: src = 2; r = zrows[t][0]; stats["n_zip_only"] += 1
        FT.append(t); RT.append(r); SR.append(src); ZI.append(zrows[t][1] if inz else np.nan)
    d = np.diff(np.array(keys, np.int64)) if len(keys) > 1 else np.array([], np.int64)
    nd = int(((d > 0) & (d < 300)).sum()); stats["near_dup_lt300s"] += nd
    if nd and len(stats["near_dup_examples"]) < 20:
        k = int(np.where((d > 0) & (d < 300))[0][0]); stats["near_dup_examples"].append([s, iso(keys[k]), iso(keys[k + 1])])
    off.append(len(FT))
    if j % 100 == 0: log("ledger", j, s, len(FT))
FT = np.array(FT, np.int64); RT = np.array(RT, np.float64); SR = np.array(SR, np.int8); ZI = np.array(ZI, np.float32); off = np.array(off, np.int64)
for j in range(829):
    seg = FT[off[j]:off[j + 1]]; assert np.all(np.diff(seg) > 0), SYMS[j]
np.savez(under(f"{W}/ledger_full.npz"), off=off, ft=FT, rate=RT, src=SR, zip_iv=ZI, symbols=np.array(SYMS))
R["ledger"] = {"path": f"{W}/ledger_full.npz", "sha256": sha(f"{W}/ledger_full.npz"), "n_rows": int(len(FT)), "ft_first": iso(FT.min()), "ft_last": iso(FT.max()), **stats,
               "rule": "union by second (t_ms//1000); API (fund_aug) rate kept on unequal seconds; zip interval column stored (zip_iv) but NOT used by the producer formula"}
log("ledger done", len(FT), json.dumps({k: stats[k] for k in ("n_conflict", "n_both_equal", "n_aug_only", "n_zip_only", "near_dup_lt300s", "zip_bad_rows", "zip_same_second_unequal")}))

# ── universe arrays on the research panel axis ──
U = np.load(SRC["umask"], allow_pickle=True); UTS = U["ts"].astype(np.int64); assert [str(x) for x in U["symbols"]] == SYMS
PIT = U["mask"].astype(bool)
TR24 = np.zeros((len(UTS), 829), bool)
for j in range(829):
    seg = FT[off[j]:off[j + 1]]
    if len(seg) == 0: continue
    hi = np.searchsorted(seg, UTS, side="right"); lo = np.searchsorted(seg, UTS - 86400, side="right")
    TR24[:, j] = hi > lo
lp = json.load(open(SRC["live_pins"]))["symbols_live"]; col = {s: j for j, s in enumerate(SYMS)}
PINS = np.zeros(829, bool); PINS[[col[s] for s in lp]] = True
np.savez(under(f"{W}/universe.npz"), ts=UTS, pit=PIT, trading24=TR24, pins=PINS, pins_list=np.array(lp), symbols=np.array(SYMS))
yrs = np.array([time.gmtime(int(t)).tm_year for t in UTS])
R["universe"] = {"path": f"{W}/universe.npz", "sha256": sha(f"{W}/universe.npz"), "n_ts": int(len(UTS)), "ts_first": iso(UTS[0]), "ts_last": iso(UTS[-1]), "n_pins": int(PINS.sum()),
                 "per_year_mean": {str(y): {"pit": round(float(PIT[yrs == y].sum(1).mean()), 1), "trading24": round(float(TR24[yrs == y].sum(1).mean()), 1),
                                             "trading24_ge300_share": round(float((TR24[yrs == y].sum(1) >= 300).mean()), 4), "pins_trading24": round(float((TR24[yrs == y] & PINS).sum(1).mean()), 1),
                                             "pit_not_trading24": round(float((PIT[yrs == y] & ~TR24[yrs == y]).sum(1).mean()), 2)} for y in sorted(set(yrs.tolist()))}}
R["nvidia_smi_after"] = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
R["runtime_s"] = round(time.time() - T0, 1); R["utc_end"] = iso(time.time())
json.dump(R, open(under(OUTR), "w"), indent=1)
log("P2_PREP_INPUTS_DONE", OUTR)
