"""fa_ema_attr.py — fund_replay EMA channel: (1) attribute each divergent cell to the skip gate, (2) is NC's EMA the truth.
Frozen rules: docs/PREREG_ema_channel_attribution_and_truth_2026-09-26.md (committed with this file, before any run).
Read-only on every input. news2's rebuild products are CONSUMED, not recomputed (3e9d72c10 / 611fc1907).

usage: env -i PATH=/usr/bin:/bin HOME=/root python -B fa_ema_attr.py PATH,HOME,LC_CTYPE <out.json>
"""
import os, sys, json, hashlib, time, calendar, collections
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT = sys.argv[2]
PIN = {"replay": ("/dev/shm/news_2026-09-23/work/fund_replay.npz", "8a73588f"),
       "legs_news": ("/dev/shm/news_2026-09-23/work/legs.npz", "18999e169c6b68546271f8194fd74eaa79041d1967ba44df978f4cbea33d6bd5"),
       "legs_nc": ("/dev/shm/news2_2026-09-23/work/legs.npz", "9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65"),
       "nc_feat": ("/dev/shm/news2_2026-09-23/work/NEWS_FEATURES.npz", "3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8"),
       "snap": ("/dev/shm/d10_2026-09-25/ms/rebuilt_features_snap.npz", "209c8f5338d34cf497661256d45fb6532f7e327447b32b54a6f6fa8896a700cd"),
       "d10": ("/dev/shm/d10_2026-09-25/ms/rebuilt_features_d10.npz", "2be2d7c8959894e0e2a59933e99ff410b72b21faf72afc073a6d97d9590c4d8a"),
       "ledger_ms": ("/dev/shm/d10_2026-09-25/ms/ledger_full_ms.npz", "e179071d595521987450f89e1774a95775a2593d76277a9c9dc6d86dcbc31a88"),
       "ledger_replay": ("/workspace/baseline_tables_2026-09-19/funding/ledger_spliced_p2_to_20260901T0200_streamD_after.npz", None)}
RN8CENSUS = {"differing": 404, "with_sig": 360, "nd_sampled": 20000, "nd_with_sig": 0}   # FA_RN8CENSUS.json actual_discriminator
W_END = calendar.timegm(time.strptime("2026-09-01T02:00:00Z", "%Y-%m-%dT%H:%M:%SZ"))
Y2026 = calendar.timegm(time.strptime("2026-01-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ"))
EDGES = [("exact0", None), ("(0,1e-15]", 1e-15), ("(1e-15,1e-12]", 1e-12), ("(1e-12,1e-9]", 1e-9),
         ("(1e-9,1e-7]", 1e-7), ("(1e-7,1e-5]", 1e-5), ("(1e-5,1e-4]", 1e-4), (">1e-4", np.inf)]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def bucket_of(d):
    """d >= 0 finite -> bucket index (0 = exactly zero)"""
    b = np.zeros(d.shape, np.int8)
    lo = 0.0
    for k, (_, hi) in enumerate(EDGES[1:], start=1):
        b[(d > lo) & (d <= hi)] = k; lo = hi
    return b


def compare(x, y, pop):
    """three classes, never merged: both finite bucketed / x finite y NaN / x NaN y finite"""
    xf, yf = np.isfinite(x) & pop, np.isfinite(y) & pop
    both = xf & yf
    d = np.abs(x[both] - y[both])
    bk = bucket_of(d)
    return {"population": int(pop.sum()), "both_finite": int(both.sum()),
            "left_finite_right_nan": int((xf & ~yf).sum()), "left_nan_right_finite": int((~xf & yf).sum()),
            "buckets": {EDGES[k][0]: int((bk == k).sum()) for k in range(len(EDGES))}}, both, d, bk


rec = {"device": "fa_ema_attr.py", "self_sha256": sha(os.path.abspath(__file__)), "argv": sys.argv,
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "prereg": "docs/PREREG_ema_channel_attribution_and_truth_2026-09-26.md", "inputs": {}, "controls": {}}
FAIL = []
for k, (p, want) in PIN.items():
    got = sha(p); rec["inputs"][k] = {"path": p, "sha256": got}
    if want is not None and not got.startswith(want): FAIL.append(f"pin {k}: {got[:12]} != {want[:12]}")
assert not FAIL, FAIL

R = np.load(PIN["replay"][0]); LN = np.load(PIN["legs_news"][0]); LC = np.load(PIN["legs_nc"][0])
NF = np.load(PIN["nc_feat"][0]); SN = np.load(PIN["snap"][0]); DT = np.load(PIN["d10"][0])
A = R["anchors"].astype(np.int64); syms = [str(s) for s in R["symbols"]]; n, NW = len(A), len(syms)
# K3 axes
for nm, z, ka, ks in (("legs_news", LN, "E_ts", "symbols"), ("legs_nc", LC, "E_ts", "symbols"), ("nc_feat", NF, "anchors", "symbols"),
                      ("snap", SN, "anchors", "symbols"), ("d10", DT, "anchors", "symbols")):
    ok = np.array_equal(z[ka].astype(np.int64), A) and [str(s) for s in z[ks]] == syms
    rec["controls"][f"K3_axis_{nm}"] = ok
    if not ok: FAIL.append(f"K3 axis {nm}")
for nm, z in (("snap", SN), ("d10", DT)):
    ok = np.array_equal(z["off"], NF["off"]) and np.array_equal(z["m"], NF["m"])
    rec["controls"][f"K3_member_layout_{nm}_equals_nc"] = ok
    if not ok: FAIL.append(f"K3 member layout {nm}")
assert not FAIL, FAIL


def to2d(z, key):
    out = np.full((n, NW), np.nan)
    off, m = z["off"], z["m"].astype(np.int64)
    rows = np.repeat(np.arange(n), np.diff(off))
    out[rows, m] = z[key]
    return out


fe_nc, fe_sn, fe_d10 = to2d(NF, "fe_v"), to2d(SN, "fe_v"), to2d(DT, "fe_v")
memb_nc = np.zeros((n, NW), bool); memb_nc[np.repeat(np.arange(n), np.diff(NF["off"])), NF["m"].astype(np.int64)] = True
inW = (A <= W_END)[:, None]
P_NC = memb_nc & inW
P_NS = np.isfinite(LN["ZFD"]) & inW
P = P_NS & P_NC
rec["population"] = {"W_end": "2026-09-01T02:00:00Z", "P_NC": int(P_NC.sum()), "P_NS": int(P_NS.sum()),
                     "P_NS_and_P_NC": int(P.sum()), "P_NS_without_truth": int((P_NS & ~P_NC).sum())}

# settlement-present strata from the truth ledger (ft in ms; the rebuild's as-of boundary is anchor*1000+999)
LM = np.load(PIN["ledger_ms"][0]); lsy = [str(s) for s in LM["symbols"]]; loff = LM["off"]; lft = LM["ft_ms"].astype(np.int64)
has_settle = np.zeros((n, NW), bool)
for j, s in enumerate(syms):
    if s not in lsy: continue
    k = lsy.index(s); f = lft[int(loff[k]):int(loff[k + 1])]
    hi = np.searchsorted(f, A * 1000 + 999, side="right"); lo = np.searchsorted(f, A * 1000 - 14400 * 1000 + 999, side="right")
    has_settle[:, j] = hi > lo
is2026 = (A >= Y2026)[:, None] & np.ones((1, NW), bool)
STRATA = {"pre2026_settle": ~is2026 & has_settle, "pre2026_nosettle": ~is2026 & ~has_settle,
          "2026_settle": is2026 & has_settle, "2026_nosettle": is2026 & ~has_settle}

# ---------------------------------------------------------------- K2 known answer (and self-comparisons)
rng = np.random.default_rng(1)
idx = np.flatnonzero((P_NC & np.isfinite(fe_sn)).ravel())
pick = rng.choice(idx, size=100, replace=False)
pert = fe_sn.copy().ravel(); pert[pick] += 1e-6; pert = pert.reshape(fe_sn.shape)
c, _, _, _ = compare(fe_sn, pert, P_NC)
selfc, _, _, _ = compare(fe_sn, fe_sn, P_NC)
k2 = (c["buckets"]["(1e-7,1e-5]"] == 100 and sum(v for k, v in c["buckets"].items() if k != "exact0") == 100
      and sum(v for k, v in selfc["buckets"].items() if k != "exact0") == 0)
rec["controls"]["K2_known_answer"] = {"planted": c["buckets"], "self": selfc["buckets"], "PASS": bool(k2)}
if not k2: FAIL.append("K2")

# ---------------------------------------------------------------- signature (fa_rn8census definition, verbatim semantics)
ZL = np.load(PIN["ledger_replay"][0], allow_pickle=False)
rsy = [str(s) for s in ZL["symbols"]]; roff = ZL["off"]; RFT = ZL["ft"].astype(np.int64)
rows_of = {t: RFT[int(roff[k]):int(roff[k + 1])] for k, t in enumerate(rsy)}
last_ft = R["last_ft"].astype(np.int64); last_iv = R["last_iv"]
age = A[:, None] - last_ft
gate = (last_ft > 0) & np.isfinite(last_iv) & (age < last_iv * 3600 * 0.9)
missed = np.full((n, NW), -1, np.int64)
for j, s in enumerate(syms):
    f = rows_of.get(s)
    if f is None: continue
    ok = last_ft[:, j] > 0
    missed[ok, j] = np.searchsorted(f, A[ok], side="right") - np.searchsorted(f, last_ft[ok, j], side="right")
sig = gate & (missed > 0)
undet = (last_ft <= 0) | ~np.isfinite(last_iv) | (missed < 0)

# K1: reproduce the RN8-channel discriminator exactly
a, b = LN["RN8"], LC["RN8"]
m = np.isfinite(a) & np.isfinite(b); diff = m & (a != b); nd = m & ~diff
_rng = np.random.default_rng(0); _ni, _nj = np.where(nd)
_k = _rng.choice(len(_ni), size=min(20000, len(_ni)), replace=False)
k1 = {"differing": int(diff.sum()), "with_sig": int((diff & (missed > 0)).sum()),
      "with_gate_and_missed": int((diff & sig).sum()), "nd_sampled": int(len(_k)),
      "nd_with_sig": int((missed[_ni[_k], _nj[_k]] > 0).sum())}
k1["PASS"] = all(k1[x] == RN8CENSUS[x] for x in RN8CENSUS)
rec["controls"]["K1_rn8_discriminator_reproduced"] = k1
if not k1["PASS"]: FAIL.append(f"K1 {k1}")

rec["controls_failed"] = FAIL
if FAIL:
    rec["STATUS"] = "UNAVAILABLE"
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
    print("FA_EMA_ATTR UNAVAILABLE", FAIL, flush=True); sys.exit(3)

# ---------------------------------------------------------------- (2) truth
T1, _, _, _ = compare(fe_nc, fe_sn, P_NC)
T1["strata"] = {}
for k, sm in STRATA.items():
    c, _, _, _ = compare(fe_nc, fe_sn, P_NC & sm)
    nonzero = c["left_finite_right_nan"] + c["left_nan_right_finite"] + sum(v for kk, v in c["buckets"].items() if kk != "exact0")
    c["differing_total"] = int(nonzero); T1["strata"][k] = c
T1["VERDICT"] = ("NC_TRUE_UNDER_PRODUCER_RULE" if all(v["differing_total"] == 0 and v["population"] >= 1000
                                                     for v in T1["strata"].values()) else "NOT_ESTABLISHED")
T2, _, _, _ = compare(fe_nc, fe_d10, P_NC)
T2["strata"] = {k: compare(fe_nc, fe_d10, P_NC & sm)[0] for k, sm in STRATA.items()}
T2["note"] = "interval-rule difference (producer snap vs D10 exact spacing); NOT a gate for (1); reported beside it"
rec["T1_nc_vs_rebuild_producer_rule"] = T1
rec["T2_nc_vs_rebuild_d10_rule"] = T2

# ---------------------------------------------------------------- (1) attribution of |ema_acc - truth|
ema = R["ema_acc"]
truth = fe_sn
rec["compare_replay_vs_truth"], both, d, bk = compare(ema, truth, P)
rec["compare_replay_vs_d10"] = compare(ema, fe_d10, P)[0]
pos = np.zeros((n, NW), bool); pos[both] = d > 0
bkfull = np.full((n, NW), -1, np.int8); bkfull[both] = bk
episode = np.zeros((n, NW), bool)
for j in range(NW):
    rows = np.flatnonzero(both[:, j])
    if not len(rows): continue
    pj, sj = pos[rows, j], sig[rows, j]
    seen = False
    for t, r in enumerate(rows):
        if not pj[t]: seen = False; continue
        if sj[t]: seen = True
        elif seen: episode[r, j] = True
cls = np.full((n, NW), "", dtype="U14")
cls[pos & sig] = "GATE_NOW"
cls[pos & ~sig & episode] = "GATE_EPISODE"
cls[pos & ~sig & ~episode] = "NOT_GATE"
cls[pos & undet & ~sig] = "UNDETERMINABLE"
CL = ("GATE_NOW", "GATE_EPISODE", "NOT_GATE", "UNDETERMINABLE")
yr = np.array([time.gmtime(int(t)).tm_year for t in A])[:, None] * np.ones((1, NW), int)
tab = {}
for c in CL:
    sel = cls == c
    tab[c] = {"total": int(sel.sum()),
              "by_bucket": {EDGES[k][0]: int((sel & (bkfull == k)).sum()) for k in range(1, len(EDGES))},
              "by_year": dict(sorted(collections.Counter(yr[sel].tolist()).items())),
              "gt_1e-7": int((sel & (bkfull >= 5)).sum()), "gt_1e-5": int((sel & (bkfull >= 6)).sum())}
rec["attribution"] = tab
mat = {thr: {c: tab[c][key] for c in CL} for thr, key in (("gt_1e-7", "gt_1e-7"), ("gt_1e-5", "gt_1e-5"))}
for thr, v in mat.items():
    tot = sum(v.values())
    v["total"] = tot
    v["attributed_to_gate"] = v["GATE_NOW"] + v["GATE_EPISODE"]
    v["not_attributed"] = v["NOT_GATE"]; v["undeterminable"] = v["UNDETERMINABLE"]
    v["not_gate_share"] = (v["NOT_GATE"] / tot) if tot else None
rec["material"] = mat
rec["second_mechanism_flag"] = bool(mat["gt_1e-5"]["not_gate_share"] is not None and mat["gt_1e-5"]["not_gate_share"] > 0.10)
rec["second_mechanism_candidate"] = "news_fund_replay.py L38-39 keeps the EARLIEST rows at limit 100 (drops newest) -- named, not tested here"
rec["probe_838210c6a_note"] = "the earlier probe compared against NC fund_state EMA (no freshness gate); this device compares against the rebuilt fe_v"
rec["STATUS"] = "OK"
json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=int); os.replace(OUT + ".tmp", OUT)
back = json.load(open(OUT)); assert back["self_sha256"] == rec["self_sha256"] and back["STATUS"] == "OK"
print("FA_EMA_ATTR STATUS=OK receipt_sha256=%s" % sha(OUT), flush=True)
print("  population", json.dumps(rec["population"]))
print("  K1", json.dumps(k1)); print("  K2", rec["controls"]["K2_known_answer"]["PASS"])
print("  T1", T1["VERDICT"], json.dumps({k: (v["population"], v["differing_total"]) for k, v in T1["strata"].items()}))
print("  T2 buckets", json.dumps(T2["buckets"]), "nan-mismatch", T2["left_finite_right_nan"], T2["left_nan_right_finite"])
print("  replay vs truth", json.dumps(rec["compare_replay_vs_truth"]))
print("  replay vs d10  ", json.dumps(rec["compare_replay_vs_d10"]))
for thr, v in mat.items(): print("  material", thr, json.dumps(v))
for c in CL: print("  ", c, json.dumps(tab[c]["by_year"]))
print("  second_mechanism_flag", rec["second_mechanism_flag"])
