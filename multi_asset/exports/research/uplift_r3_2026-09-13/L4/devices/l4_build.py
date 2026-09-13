#!/usr/bin/env python3
"""l4_build.py -- L4 step 1 (pod2, CPU only). Implements PREREG_L4_carry_sleeve_hysteresis_2026-09-13.md (sha256 ced2f73f...,
frozen 2026-09-13T11:24:12Z, commit deb3af82) section 2 inputs and section 6 gates G-IN, G-ALIGN, G-A0, G-FUND, G-SETT, G-UNITS.
Writes <out>/l4_inputs.npz and <out>/RECEIPT_L4_build.json and prints one SUMMARY line. No sleeve statistic is computed here:
the only return-like arrays read are the T6 A0 columns (for the G-A0 reproduction gate, published numbers) and copied through.
Usage: python3 l4_build.py <env_whitelist_csv> <out_dir>
"""
import os, sys, json, time, math, hashlib, calendar, gzip, glob, io, zipfile
WHITE = set(x for x in sys.argv[1].split(",") if x); assert WHITE, "non-empty env whitelist required"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
OUT = os.path.abspath(sys.argv[2]); assert OUT.startswith("/workspace/uplift_r3_2026-09-13/L4/"), OUT
import numpy as np
from scipy import stats
T_START = time.time()
SELF = os.path.abspath(__file__)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ut(y, m, d, h=0): return calendar.timegm((y, m, d, h, 0, 0))
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
os.makedirs(OUT, exist_ok=True)
probe = os.path.join(OUT, "_write_probe")
with open(probe, "wb") as f: f.write(b"x" * (1 << 20)); f.flush(); os.fsync(f.fileno())
assert os.path.getsize(probe) == 1 << 20; os.remove(probe)

# ---------------------------------------------------------------- inputs (PREREG section 7)
P = dict(
    FUND="/workspace/fund_aug.json.gz",
    SETT="/workspace/review_scratch/allweather_trackC/carry_layers/data/sett_tables.npz",
    T7="/workspace/uplift_r2_2026-09-13/T7/receipts/T7_universe_elig.npz",
    A1="/workspace/review_scratch/allweather_trackA/features/a1_feat_shift0.npz",
    MAP="/workspace/review_scratch/allweather_trackA/spot/perp_to_spot_map.json",
    S3="/workspace/review_scratch/allweather_trackA/spot/s3_spot_symbols.json",
    R5="/workspace/uplift_2026-09-11/r5_basis/basis_panel.npz",
    T6_42="/workspace/uplift_r2_2026-09-13/T6/receipts/T6_SERIES_s42.npz",
    T6_2027="/workspace/uplift_r2_2026-09-13/T6/receipts/T6_SERIES_s2027.npz",
    EXT_CACHE="/workspace/data/dlnative_5m_wide829_f16_ext.npz")
KNOWN = dict(
    FUND="8a9e771577602dd1875a87fb07f982bc2c255e740966f911469420a44a53a8c2",
    SETT="f1c336298fc872997d3f8d9ae3093cc6e123705d11508fe049448082d5fa03cc",
    T7="a530e123a13d172272a1f36c300eccba945ec8d2303f32556db844c65e256bfb",
    A1="8136537f593a65004b2df7ae335a37b093188cf534c02b43b41449703eca307a",
    MAP="b17eb0ba8fb50894bd268cdc79ba382d8c6bf07a43f38886ad8bfab9d0ee717a",
    S3="d2b21f1e8aa1eec8dca45f27911a98d3c6503a482dbe776caf0b230f4b3cdd9d",
    R5="f974317a4988916549cfb0a3a03c2114a69c8370cb9845e8c964fc4dfde08310",
    T6_42="a3120f298395cf03346bbdf038aaca2dcfbed25df28a25207788da940d98351e",
    T6_2027="74d4b88d602a0093d999be1f7c546abda832cb1acf1bd3064b82ca9fd6d3a3ee")
FUNDZIP_DIR = "/workspace/wide_multisrc/funding"
REC = dict(device="l4_build.py", device_sha256=sha(SELF), run_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           prereg_sha256="ced2f73f10b1d32377d469ddd64b4ee6614d0925c9be182bd09ff2f16a52cc8b",
           env_actual={k: os.environ[k] for k in sorted(os.environ)}, python=sys.version.split()[0], numpy=np.__version__,
           affinity=sorted(os.sched_getaffinity(0)), out_dir=OUT, inputs={}, gates={}, counts={})
assert len(REC["affinity"]) <= 8, ("more than 8 cores visible", REC["affinity"])
for k, p in P.items():
    if k == "EXT_CACHE":
        st = os.stat(p); REC["inputs"][k] = dict(path=p, size=st.st_size, mtime_utc=iso(st.st_mtime), sha256="not hashed (5.7 GB; only symbols.npy member read)")
        continue
    h = sha(p); REC["inputs"][k] = dict(path=p, sha256=h, known=KNOWN.get(k), equal=(h == KNOWN.get(k)))
G_IN = all(v.get("equal", True) for v in REC["inputs"].values())
REC["gates"]["G-IN"] = dict(pass_=G_IN, detail={k: v.get("equal") for k, v in REC["inputs"].items()})
print("CONFIG " + json.dumps(dict(self_sha256=REC["device_sha256"], prereg=REC["prereg_sha256"], out=OUT, affinity=REC["affinity"])), flush=True)
print("G-IN %s" % G_IN, flush=True)
assert G_IN, "G-IN FAIL: input sha mismatch"

# ---------------------------------------------------------------- grid and windows (PREREG 2.1)
H4 = 14400
EG0 = ut(2021, 11, 30, 20); EG1 = ut(2026, 8, 31, 0)
EG = np.arange(EG0, EG1 + 1, H4, dtype=np.int64); nG = len(EG); gi = {int(t): i for i, t in enumerate(EG)}
W0 = ut(2022, 1, 31, 0); W1 = ut(2026, 8, 30, 20)
iW0, iW1 = gi[W0], gi[W1]; WMASK = np.zeros(nG, bool); WMASK[iW0:iW1 + 1] = True
assert WMASK.sum() == 10038

# ---------------------------------------------------------------- T7 eligibility, r5 basis, a1 spot, map, ext-cache symbols
T7 = np.load(P["T7"], allow_pickle=True); S7 = [str(s) for s in T7["symbols"]]; NS = len(S7); assert NS == 829
E7 = T7["E_ts"].astype(np.int64); EL7 = T7["elig_NW"].astype(bool)
R5 = np.load(P["R5"], allow_pickle=True); S5 = [str(s) for s in R5["symbols"]]; E5 = R5["ts"].astype(np.int64)
A1 = np.load(P["A1"], allow_pickle=True); EA = A1["E_ts"].astype(np.int64); a1names = [str(x) for x in A1["names"]]
assert a1names[1] == "qvr_24h" and a1names[2] == "basis", a1names
zc = zipfile.ZipFile(P["EXT_CACHE"]); SC = [str(s) for s in np.load(io.BytesIO(zc.read("symbols.npy")), allow_pickle=True)]; zc.close()
MAPJ = json.load(open(P["MAP"])); MAPD = MAPJ["map"]; S3J = json.load(open(P["S3"])); S3SET = set(S3J["symbols"])
T6 = {s: np.load(P["T6_" + s], allow_pickle=True) for s in ("42", "2027")}
fund = json.load(gzip.open(P["FUND"], "rt"))["rates"]
al = dict(
    symbols_T7_eq_R5=(S7 == S5), symbols_T7_eq_EXTCACHE_a1_order=(S7 == SC), fund_keys_subset=all(s in set(S7) for s in fund),
    n_fund_keys=len(fund), fund_missing=[s for s in S7 if s not in fund],
    W_subset_T7=bool(np.isin(EG[WMASK], E7).all()), R5_covers_W_and_next=bool(np.isin(np.append(EG[WMASK], EG[iW1 + 1]), E5).all()),
    A1_covers_W=bool(np.isin(EG[WMASK], EA).all()),
    T6_ts_eq_W={s: bool(np.array_equal(T6[s]["ts"].astype(np.int64), EG[WMASK])) for s in T6},
    map_targets_in_S3=all(v["spot"] in S3SET for v in MAPD.values()), map_keys_in_symbols=all(k in set(S7) for k in MAPD),
    a1_E_contiguous=bool(np.all(np.diff(EA) == H4)), r5_E_contiguous=bool(np.all(np.diff(E5) == H4)))
G_ALIGN = bool(al["symbols_T7_eq_R5"] and al["symbols_T7_eq_EXTCACHE_a1_order"] and al["fund_keys_subset"] and al["W_subset_T7"] and al["R5_covers_W_and_next"]
               and al["A1_covers_W"] and all(al["T6_ts_eq_W"].values()) and al["map_targets_in_S3"] and al["map_keys_in_symbols"])
REC["gates"]["G-ALIGN"] = dict(pass_=G_ALIGN, detail=al)
print("G-ALIGN %s %s" % (G_ALIGN, json.dumps({k: v for k, v in al.items() if k != "fund_missing"})), flush=True)
assert G_ALIGN, "G-ALIGN FAIL"

# ---------------------------------------------------------------- G-A0 (T6 GATE-0 subset)
ANN = math.sqrt(2190.0)
def SR(x): return float(x.mean() / x.std(ddof=1) * ANN)
def a0col(s):
    stem = T6[s]["stem"]; w = np.nonzero(stem == "A0_PWR230k_s%s" % s)[0]; assert len(w) == 1; return T6[s]["G"][:, int(w[0])].astype(np.float64)
g42, g27 = a0col("42"), a0col("2027"); TSW = EG[WMASK]
FR = (TSW >= ut(2025, 3, 1)) & (TSW <= ut(2026, 8, 10, 20)); assert FR.sum() == 3168
ga0 = dict(s42_FROZEN_SR=(SR(g42[FR]), 2.93571303735249, 1e-9), s42_WFULL_SR=(SR(g42), 1.1062, 5e-5), s2027_FROZEN_SR=(SR(g27[FR]), 2.9021, 5e-5))
ga0 = {k: dict(got=v[0], want=v[1], tol=v[2], pass_=bool(abs(v[0] - v[1]) <= v[2])) for k, v in ga0.items()}
G_A0 = all(v["pass_"] for v in ga0.values()) and bool(np.isfinite(g42).all() and np.isfinite(g27).all())
REC["gates"]["G-A0"] = dict(pass_=G_A0, detail=ga0)
print("G-A0 %s %s" % (G_A0, json.dumps({k: round(v["got"], 10) for k, v in ga0.items()})), flush=True)
assert G_A0, "G-A0 FAIL"

# ---------------------------------------------------------------- funding events -> window sums (PREREG 2.2)
kof = {s: k for k, s in enumerate(S7)}
A = np.zeros((nG, NS), np.float64); NEV = np.zeros((nG, NS), np.int16)
DUPCELL = np.zeros((nG, NS), bool); SEC1CELL = np.zeros((nG, NS), bool); SPACE_LAST = np.full((nG, NS), np.nan, np.float32)
EVENTS = {}   # sym -> (S_hour int64, rate float64, spacing_h float64, ms int64)
cnt = dict(records=0, dropped_outside_grid=0, same_hour_dup_records=0, sec1_records=0, spacing_hist={})
for s, rows in fund.items():
    k = kof[s]
    t = np.array([r[0] for r in rows], np.int64); v = np.array([r[1] for r in rows], np.float64)
    o = np.argsort(t, kind="stable"); t = t[o]; v = v[o]
    sec = t // 1000; S = (sec // 3600) * 3600; sec1 = (sec % 3600) != 0
    assert ((sec % 3600) <= 1).all(), (s, "second-of-hour > 1")
    sp = np.full(len(S), np.nan); sp[1:] = (S[1:] - S[:-1]) / 3600.0
    dup = np.zeros(len(S), bool); dup[1:] |= S[1:] == S[:-1]; dup[:-1] |= S[1:] == S[:-1]
    EVENTS[s] = (S, v, sp, t)
    cnt["records"] += len(S); cnt["same_hour_dup_records"] += int(dup.sum()); cnt["sec1_records"] += int(sec1.sum())
    for x in sp[np.isfinite(sp)]:
        key = str(int(x)) if x == int(x) else "%.3f" % x; cnt["spacing_hist"][key] = cnt["spacing_hist"].get(key, 0) + 1
    j = (S - EG0 - 1) // H4          # E_j < S <= E_j + 4h
    ok = (S > EG0) & (j >= 0) & (j < nG)
    cnt["dropped_outside_grid"] += int((~ok).sum())
    j = j[ok]; vv = v[ok]; dd = dup[ok]; s1 = sec1[ok]; spp = sp[ok]
    assert np.all((EG[j] < S[ok]) & (S[ok] <= EG[j] + H4))
    np.add.at(A[:, k], j, vv); np.add.at(NEV[:, k], j, 1)
    DUPCELL[j[dd], k] = True; SEC1CELL[j[s1], k] = True
    SPACE_LAST[j, k] = spp.astype(np.float32)          # later events in the same window overwrite (sorted) => last event's spacing
cnt["spacing_hist"] = dict(sorted(cnt["spacing_hist"].items(), key=lambda x: -x[1])[:20])
has_ev = NEV > 0
first_j = np.where(has_ev.any(0), has_ev.argmax(0), -1).astype(np.int64)
INIT_IDX = np.where(first_j >= 0, first_j + 1, -1).astype(np.int64)   # EMA initialised at the anchor whose trailing window holds the first record
REC["counts"]["funding"] = cnt
print("FUNDING records=%d dropped=%d dup=%d sec1=%d names_with_events=%d" % (cnt["records"], cnt["dropped_outside_grid"], cnt["same_hour_dup_records"], cnt["sec1_records"], int((first_j >= 0).sum())), flush=True)

# ---------------------------------------------------------------- G-FUND (vision monthly zips vs fund_aug)
months = ["%04d-%02d" % (y, m) for y in range(2022, 2027) for m in range(1, 13) if (y, m) <= (2026, 7)]
zsha_lines = []; gf = dict(zips=0, zip_404=0, api_events_in_zip_months=0, matched=0, api_unmatched=0, vision_unmatched=0, rate_eq_1e9=0, max_abs_drate=0.0,
                          interval_compared=0, interval_agree=0, symbols_with_zips=0)
for s in S7:
    if s not in EVENTS: continue
    S, v, sp, _ = EVENTS[s]; any_zip = False
    mon = np.array([time.strftime("%Y-%m", time.gmtime(int(x))) for x in S]) if len(S) else np.array([])
    for mo in months:
        zp = os.path.join(FUNDZIP_DIR, s, mo + ".zip")
        if not os.path.exists(zp):
            if os.path.exists(zp + ".404"): gf["zip_404"] += 1
            continue
        any_zip = True; gf["zips"] += 1; zsha_lines.append("%s  %s" % (sha(zp), zp))
        with zipfile.ZipFile(zp) as z: raw = z.read(z.namelist()[0]).decode()
        vis = {}
        for ln in raw.splitlines():
            p_ = ln.split(",")
            if not p_ or not p_[0].strip() or not p_[0].strip()[0].isdigit(): continue
            ct = int(p_[0]); Sh = (ct // 1000 // 3600) * 3600; vis.setdefault(Sh, []).append((ct, float(p_[2]), float(p_[1])))
        sel = np.nonzero(mon == mo)[0]; api = {}
        for q in sel: api.setdefault(int(S[q]), []).append((float(v[q]), float(sp[q])))
        gf["api_events_in_zip_months"] += len(sel)
        for Sh, lst in api.items():
            vl = sorted(vis.get(Sh, [])); m_ = min(len(lst), len(vl)); gf["matched"] += m_; gf["api_unmatched"] += len(lst) - m_
            for (ra, spa), (_, rv, ivh) in zip(lst[:m_], vl[:m_]):
                d = abs(ra - rv); gf["max_abs_drate"] = max(gf["max_abs_drate"], d); gf["rate_eq_1e9"] += int(d <= 1e-9)
                if np.isfinite(spa): gf["interval_compared"] += 1; gf["interval_agree"] += int(abs(spa - ivh) < 1e-9)
        for Sh, vl in vis.items(): gf["vision_unmatched"] += max(0, len(vl) - len(api.get(Sh, [])))
    gf["symbols_with_zips"] += int(any_zip)
gf["matched_share_of_api"] = gf["matched"] / max(gf["api_events_in_zip_months"], 1)
gf["rate_eq_share_of_matched"] = gf["rate_eq_1e9"] / max(gf["matched"], 1)
gf["interval_agree_share"] = gf["interval_agree"] / max(gf["interval_compared"], 1)
G_FUND = bool(gf["matched_share_of_api"] >= 0.90 and gf["rate_eq_share_of_matched"] >= 0.99)
REC["gates"]["G-FUND"] = dict(pass_=G_FUND, detail=gf)
with open(os.path.join(OUT, "FUNDZIP_SHA256.txt"), "w") as f: f.write("\n".join(zsha_lines) + "\n")
print("G-FUND %s %s" % (G_FUND, json.dumps(gf)), flush=True)
assert G_FUND, "G-FUND FAIL"

# ---------------------------------------------------------------- G-SETT (carry_layers settlement table)
ST = np.load(P["SETT"], allow_pickle=True); ES = ST["E_ts"].astype(np.int64); RS = ST["R"]
assert [str(x) for x in ST["symbols"]] == S7
rows_g = np.array([gi[int(t)] for t in ES], np.int64)
tab_has = np.isfinite(RS).any(2); tab_sum = np.nansum(RS.astype(np.float64), 2)
mine_has = NEV[rows_g] > 0; mine_sum = A[rows_g]
excl = DUPCELL[rows_g] | SEC1CELL[rows_g]
pres_mis = (tab_has != mine_has) & ~excl
both = tab_has & mine_has & ~excl
maxd = float(np.abs(mine_sum[both] - tab_sum[both]).max()) if both.any() else float("nan")
gs = dict(shared_anchors=int(len(ES)), first=iso(ES[0]), last=iso(ES[-1]), excluded_cells=int(excl.sum()), presence_mismatch=int(pres_mis.sum()),
          cells_compared=int(both.sum()), max_abs_diff=maxd, presence_mismatch_in_excluded=int(((tab_has != mine_has) & excl).sum()))
G_SETT = bool(gs["presence_mismatch"] == 0 and np.isfinite(maxd) and maxd <= 1e-7)
REC["gates"]["G-SETT"] = dict(pass_=G_SETT, detail=gs)
print("G-SETT %s %s" % (G_SETT, json.dumps(gs)), flush=True)
del RS, tab_has, tab_sum
assert G_SETT, "G-SETT FAIL"

# ---------------------------------------------------------------- spot, eligibility and basis on the grid (PREREG 2.3-2.5)
ia = np.array([gi.get(int(t), -1) for t in EA], np.int64); okA = ia >= 0
BAS_A1 = np.full((nG, NS), np.nan, np.float64); BAS_A1[ia[okA]] = A1["F"][okA, :, 2].astype(np.float64)
QVR24 = np.full((nG, NS), np.nan, np.float32); QVR24[ia[okA]] = A1["F"][okA, :, 1]
MAPPED = np.array([s in MAPD for s in S7])
TRAD = np.isfinite(BAS_A1) & MAPPED[None, :]
first_trad = np.where(TRAD.any(0), TRAD.argmax(0), -1)
LISTED1D = np.zeros((nG, NS), bool)
for k in range(NS):
    if first_trad[k] >= 0: LISTED1D[:, k] = EG >= EG[first_trad[k]] + 86400
with np.errstate(invalid="ignore"):
    GUARD = np.abs(np.log1p(BAS_A1)) <= math.log(1.25)
SPOT_OK = MAPPED[None, :] & TRAD & LISTED1D & GUARD
GUARD_FAIL = MAPPED[None, :] & TRAD & ~GUARD
with np.errstate(invalid="ignore", divide="ignore"):
    B1 = 1.0 / (1.0 + BAS_A1) - 1.0
i7 = np.array([gi.get(int(t), -1) for t in E7], np.int64); ok7 = i7 >= 0
ELIG = np.zeros((nG, NS), bool); ELIG[i7[ok7]] = EL7[ok7]
i5 = np.array([gi.get(int(t), -1) for t in E5], np.int64); ok5 = i5 >= 0
B2 = np.full((nG, NS), np.nan, np.float64); B2[i5[ok5]] = R5["p_last"][ok5].astype(np.float64)
PTW8 = np.full((nG, NS), np.nan, np.float64); PTW8[i5[ok5]] = R5["p_tw8"][ok5].astype(np.float64)
sc = dict(mapped=int(MAPPED.sum()), guard_fail_cells_W=int(GUARD_FAIL[WMASK].sum()), spot_ok_cells_W=int(SPOT_OK[WMASK].sum()),
          elig_cells_W=int(ELIG[WMASK].sum()), elig_and_spot_ok_cells_W=int((ELIG & SPOT_OK)[WMASK].sum()),
          elig_spot_ok_b2_finite_cells_W=int((ELIG & SPOT_OK & np.isfinite(B2))[WMASK].sum()))
REC["counts"]["spot_elig_basis"] = sc
print("SPOT " + json.dumps(sc), flush=True)

# ---------------------------------------------------------------- G-UNITS
xs = []; sg = []
for s in S7:
    if s not in EVENTS: continue
    k = kof[s]; S, v, sp, _ = EVENTS[s]
    m_ = (sp == 8.0) & (np.abs(v) >= 0.001) & (S >= W0) & (S <= W1 + H4) & (S % H4 == 0)
    for Sh, r in zip(S[m_], v[m_]):
        i = gi.get(int(Sh))
        if i is None: continue
        p = PTW8[i, k]
        if np.isfinite(p): xs.append(r); sg.append(p)
xs = np.array(xs); sg = np.array(sg)
pos = xs > 0; neg = xs < 0
u1 = dict(n_pos=int(pos.sum()), n_neg=int(neg.sum()), agree_pos=float((sg[pos] > 0).mean()) if pos.any() else float("nan"),
          agree_neg=float((sg[neg] < 0).mean()) if neg.any() else float("nan"))
cell = WMASK[:, None] & ELIG & MAPPED[None, :] & np.isfinite(B1) & np.isfinite(B2)
c10 = cell & (np.abs(B2) >= 0.001); c20 = cell & (np.abs(B2) >= 0.002)
rho_s = float(stats.spearmanr(B1[c10], B2[c10]).statistic) if c10.sum() > 10 else float("nan")
ratio_med = float(np.median(B1[c20] / B2[c20])) if c20.sum() > 10 else float("nan")
u2 = dict(n_cells_p10=int(c10.sum()), spearman_b1_p_last=rho_s, n_cells_p20=int(c20.sum()), median_ratio_b1_over_p_last=ratio_med)
G_UNITS = bool(u1["n_pos"] > 0 and u1["n_neg"] > 0 and u1["agree_pos"] >= 0.90 and u1["agree_neg"] >= 0.90 and rho_s >= 0.3 and 0.5 <= ratio_med <= 2.0)
REC["gates"]["G-UNITS"] = dict(pass_=G_UNITS, detail=dict(i_funding_sign_vs_p_tw8=u1, ii_b1_vs_b2=u2))
print("G-UNITS %s %s %s" % (G_UNITS, json.dumps(u1), json.dumps(u2)), flush=True)
assert G_UNITS, "G-UNITS FAIL"

# ---------------------------------------------------------------- write inputs
outp = os.path.join(OUT, "l4_inputs.npz")
np.savez_compressed(outp, EG=EG, SYM=np.array(S7), WMASK=WMASK, iW0=iW0, iW1=iW1, A=A, NEV=NEV, DUPCELL=DUPCELL, SEC1CELL=SEC1CELL,
                    SPACE_LAST=SPACE_LAST, INIT_IDX=INIT_IDX, ELIG=ELIG, TRAD=TRAD, SPOT_OK=SPOT_OK, GUARD_FAIL=GUARD_FAIL,
                    B2=B2, B1=B1, QVR24=QVR24, MAPPED=MAPPED, A0_G42=g42, A0_G2027=g27)
REC["output"] = dict(path=outp, sha256=sha(outp), size=os.path.getsize(outp))
REC["elapsed_s"] = round(time.time() - T_START, 1)
ALL = all(v["pass_"] for v in REC["gates"].values())
REC["all_gates_pass"] = ALL
json.dump(REC, open(os.path.join(OUT, "RECEIPT_L4_build.json"), "w"), indent=1)
print("SUMMARY l4_build G-IN=%s G-ALIGN=%s G-A0=%s G-FUND=%s(match %.4f eq %.4f) G-SETT=%s(maxd %.2e mis %d) G-UNITS=%s ALL=%s out_sha256=%s elapsed=%.0fs self_sha256=%s" % (
    G_IN, G_ALIGN, G_A0, G_FUND, gf["matched_share_of_api"], gf["rate_eq_share_of_matched"], G_SETT, maxd, gs["presence_mismatch"], G_UNITS, ALL,
    REC["output"]["sha256"][:16], REC["elapsed_s"], REC["device_sha256"][:16]), flush=True)
