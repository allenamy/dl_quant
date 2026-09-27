#!/usr/bin/env python3
"""t7nc_zero.py — ZERO-RETURN steps of AMENDMENT_T7_NC_2026-09-27 §3 (frozen 21ecc60f5). Committed before it is run.
No return array is ever read: every npz goes through LoggedNpz, which records the keys fetched, and the receipt asserts that no key in
FORBIDDEN was fetched (y4 / Y4 / y24 / ret / LR leg returns). The META file (which holds y4) is never opened here; its sha comes from pod2.

stage A (inputs; light):
  1 inputs pinned: legs / TRD-01 W24H / combo s42, s2027 copied from pod2 to /Users/haosiyu/cc_tmp/t7_nc, sha from the bytes read == the AMENDMENT pins
  2 A0 C0 vs NC TRD-01 eligible overlap per year on common anchors (pairs, shares, Jaccard)
  5 masked seat w_f = WL2 / (WL0 + WL2) per year (quantiles; anchors with WL0 + WL2 <= 1e-12)
  6 META sha (pod2 sha256sum) == the pin; the frozen §11.1 rule resolves A0's meta through r18_drive.py's remap to the same path
  plus: NC evaluation axis per year (combo axis ∩ legs axis, <= 2026-08-30T20Z), every NC anchor present on the A0 grid (candidates are built there),
  legs ready counts in 2022 (why 2022 is not evaluable)
stage B (after the frozen t7_s1_guards.py / t7_s1_build.py; candidates contain no returns):
  3 KRW coverage on NC: valid K1 names / NC eligible names per year; share of NC held gross (s42, s2027) on K1-valid names
  4 valid anchors per year per candidate (|U_K ∩ NC eligible| >= 30) and the EXPECTED_EVAL_YEARS assertion (with its two synthetic controls)
  rev 1 (AMENDMENT-2, frozen 435559a61): stage B's NC eligible set = U_NC (LIVE, t7nc_universe.py) ∩ {KZ, ZFD finite}, not TRD; per-year B-undefined
  exclusions and per-candidate O1 set sizes reported. Stage A unchanged (inputs / overlap / seats do not depend on this row).
usage: /opt/homebrew/bin/python3 t7nc_zero.py A|B
"""
import os, sys, io, json, time, hashlib, calendar
import numpy as np

STAGE = sys.argv[1]; assert STAGE in ("A", "B")
EXPECTED_EVAL_YEARS = (2023, 2024, 2025, 2026)          # AMENDMENT §2, literal
MIN_SUBSET = 30; MIN_ANCHORS = 100                      # frozen §4 / §11.4, §11.7
UB = calendar.timegm((2026, 8, 30, 20, 0, 0))           # META y4 axis end (AMENDMENT §0 row 5)
D = "/Users/haosiyu/cc_tmp/t7_nc"; T7 = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T7"
PIN = {"legs.npz": "9ee5886f37d1727c306d0fb692d2cad1e6400ae13f19d5cd4e280dc59f208f65",
       "member_mask_tradable_AND_live_W24H_cachegrid.npz": "f752d8ae3bf92f001fcb5d6f83a7e4ae286d9f11f7548c2e965305615aa9ae51",
       "combo_s42_scaled_diagnostic.npz": "f4630a20f796bce26590aedeadfc28791be7eeecee8c14789f418b5a08de4388",
       "combo_s2027_scaled_diagnostic.npz": "fe09d81744030e3fc7da3367ed7da8668d390a68d1db66764be4cc74f40b00ce"}
META_PIN = "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3"
A0ELIG = T7 + "/receipts/pod2/T7_universe_elig.npz"; A0ELIG_PREFIX = "a530e123"
UNC = f"{D}/U_NC.npz"; UNC_PIN = "19b9dc35ab86b232f52199ad0d3642bc48dfca78e75d2640a829316da4564625"   # AMENDMENT-2 (frozen 435559a61), t7nc_universe.py receipt 0f055ef4
CAND = "/Users/haosiyu/cc_tmp/krw_pull/s1/T7_S1_CANDIDATES.npz"; CAND_REC = "/Users/haosiyu/cc_tmp/krw_pull/s1/T7_S1_BUILD_RECEIPT.json"
FORBIDDEN = ("y4", "Y4", "y24", "Y24", "ret", "LR", "rA", "rB")
FETCHED = {}


class LoggedNpz:
    def __init__(self, path, pin=None, prefix=None):
        b = open(path, "rb").read(); assert len(b) == os.path.getsize(path) and len(b) > 0, ("short read", path)
        self.sha = hashlib.sha256(b).hexdigest(); self.name = os.path.basename(path)
        if pin: assert self.sha == pin, ("pin", path, self.sha)
        if prefix: assert self.sha.startswith(prefix), ("pin prefix", path, self.sha)
        self.z = np.load(io.BytesIO(b), allow_pickle=False); FETCHED[self.name] = []
    def __getitem__(self, k):
        assert not any(k == f or k.startswith(f + "_") for f in FORBIDDEN), ("FORBIDDEN KEY", self.name, k)
        FETCHED[self.name].append(k); return self.z[k]


def yr(t): return time.gmtime(int(t)).tm_year


def q(x): x = x[np.isfinite(x)]; return None if x.size == 0 else [round(float(v), 4) for v in np.quantile(x, [0.05, 0.25, 0.5, 0.75, 0.95])]


def years_assert(valid_by_year):
    """AMENDMENT §2: the set of years with >= MIN_ANCHORS valid anchors must equal EXPECTED_EVAL_YEARS exactly; no silent skip."""
    got = tuple(sorted(y for y, n in valid_by_year.items() if n >= MIN_ANCHORS))
    if got != EXPECTED_EVAL_YEARS:
        miss = [y for y in EXPECTED_EVAL_YEARS if y not in got]; extra = [y for y in got if y not in EXPECTED_EVAL_YEARS]
        return f"STOP eval-year set {got} != {EXPECTED_EVAL_YEARS}: missing {[(y, valid_by_year.get(y, 0)) for y in miss]} extra {extra}"
    return "OK"


rec = {"device": "t7nc_zero.py", "stage": STAGE, "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
       "amendment_frozen_commit": "21ecc60f5f5d0b67ef15b8fc632e993f075bb2e4", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "zero_returns": True}
L = LoggedNpz(f"{D}/legs.npz", PIN["legs.npz"]); T = LoggedNpz(f"{D}/member_mask_tradable_AND_live_W24H_cachegrid.npz", PIN["member_mask_tradable_AND_live_W24H_cachegrid.npz"])
la = L["E_ts"].astype(np.int64); lsym = [str(s) for s in L["symbols"]]
assert np.array_equal(T["ts"].astype(np.int64), la) and [str(s) for s in T["symbols"]] == lsym, "TRD axis/symbols != legs"
TM = T["mask"].astype(bool)
C = {k: LoggedNpz(f"{D}/combo_s{k}_scaled_diagnostic.npz", PIN[f"combo_s{k}_scaled_diagnostic.npz"]) for k in ("42", "2027")}
ca = C["42"]["E_ts"].astype(np.int64); assert np.array_equal(C["2027"]["E_ts"].astype(np.int64), ca)
for k in C: assert [str(s) for s in C[k]["symbols"]] == lsym, "combo symbols != legs"
EV = ca[ca <= UB]; pos = np.searchsorted(la, EV); assert np.array_equal(la[pos], EV), "NC eval anchor missing on legs axis"
EVY = np.array([yr(t) for t in EV])
A0 = LoggedNpz(A0ELIG, prefix=A0ELIG_PREFIX); ae = A0["E_ts"].astype(np.int64); asym = [str(s) for s in A0["symbols"]]
assert asym == lsym, "A0 panel symbols != legs symbols (candidate columns would misalign)"
apos = np.searchsorted(ae, EV); on_a0 = (apos < ae.size) & (ae[np.minimum(apos, ae.size - 1)] == EV)
rec["inputs"] = {n: z.sha for n, z in [("legs", L), ("trd_w24h", T), ("combo_s42", C["42"]), ("combo_s2027", C["2027"]), ("a0_elig", A0)]}
rec["axis"] = {"nc_eval_first": time.strftime("%FT%H:%MZ", time.gmtime(int(EV[0]))), "nc_eval_last": time.strftime("%FT%H:%MZ", time.gmtime(int(EV[-1]))),
               "nc_eval_anchors_by_year": {int(y): int((EVY == y).sum()) for y in np.unique(EVY)},
               "nc_eval_anchors_missing_on_A0_grid": int((~on_a0).sum()),
               "missing_on_A0_grid_first5": [time.strftime("%FT%H:%MZ", time.gmtime(int(t))) for t in EV[~on_a0][:5]]}
assert on_a0.all(), ("NC eval anchors absent from the A0 candidate grid", rec["axis"])

if STAGE == "A":
    # 6 META
    ps = open(f"{D}/pod2_sha.txt").read().split("\n"); msha = [l.split()[0] for l in ps if l.endswith("meta_newprod_v4.npz")]
    assert len(msha) == 1, ps
    r18 = open("/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r18_foundation/devices/r18_drive.py").read()
    rec["meta"] = {"pod2_sha256": msha[0], "equals_pin": msha[0] == META_PIN,
                   "frozen_rule_resolution": "r18_drive.py remaps wide_fea_hist_meta.npz -> /workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",
                   "r18_remap_line_present": '"/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"' in r18, "opened_here": False}
    assert rec["meta"]["equals_pin"] and rec["meta"]["r18_remap_line_present"]
    # 2 overlap
    ea = A0["elig_C0"].astype(bool)[apos]; en = TM[pos]; ov = {}
    for y in EXPECTED_EVAL_YEARS:
        m = EVY == y; a = ea[m]; n = en[m]; inter = int((a & n).sum()); A_ = int(a.sum()); N_ = int(n.sum()); U = int((a | n).sum())
        ov[y] = {"pairs_A0": A_, "pairs_NC": N_, "inter": inter, "inter_over_A0": round(inter / max(A_, 1), 4), "inter_over_NC": round(inter / max(N_, 1), 4),
                 "jaccard": round(inter / max(U, 1), 4), "mean_names_A0": round(A_ / max(m.sum(), 1), 1), "mean_names_NC": round(N_ / max(m.sum(), 1), 1)}
    rec["overlap_A0_C0_vs_NC_TRD"] = ov
    # 5 seats
    WL = L["WL"].astype(np.float64)[pos]; den = WL[:, 0] + WL[:, 2]; wf = np.where(den > 1e-12, WL[:, 2] / np.where(den > 1e-12, den, 1), np.nan)
    rec["seat_wf"] = {int(y): {"q05_25_50_75_95": q(wf[EVY == y]), "den_le_1e-12": int((den[EVY == y] <= 1e-12).sum())} for y in EXPECTED_EVAL_YEARS}
    rdy = L["ready"].astype(bool); ly = np.array([yr(t) for t in la])
    rec["legs_2022"] = {"anchors": int((ly == 2022).sum()), "ready": int(rdy[ly == 2022].sum()),
                        "first_ready": time.strftime("%FT%H:%MZ", time.gmtime(int(la[rdy][0]))), "seat_look_anchors": 900,
                        "note": "2022 not evaluable on NC (AMENDMENT §2): legs ready from first_ready, seat window fills ~150 days later, NC combo axis starts 2023-01-01"}
else:
    CR = json.load(open(CAND_REC)); Z = LoggedNpz(CAND, CR["candidates_sha256"]); ze = Z["E_ts"].astype(np.int64)
    assert np.array_equal(ze, ae) and [str(s) for s in Z["symbols"]] == lsym, "candidate grid != A0 grid"
    UN = LoggedNpz(UNC, UNC_PIN); assert np.array_equal(UN["E_ts"].astype(np.int64), ca) and [str(s) for s in UN["symbols"]] == lsym, "U_NC axis/symbols"
    U = UN["U"].astype(bool)[: EV.size]; BF = UN["B_finite"].astype(bool)[: EV.size]
    en = U & BF                               # AMENDMENT-2 §1-§2: DeltaIC set = U_NC ∩ {KZ, ZFD finite} (replaces TRD for stage B)
    rec["excluded_cells_B_undefined_by_year"] = {int(y): int((U & ~BF)[EVY == y].sum()) for y in EXPECTED_EVAL_YEARS}
    held = {}
    for k in C:
        W = C[k]["weights"].astype(np.float64); tm = C[k]["trade_mask"].astype(bool); H = np.zeros_like(W); cur = np.zeros(W.shape[1])
        for i in range(len(tm)):
            if tm[i]: cur = W[i]
            H[i] = cur
        held[k] = np.abs(H[: EV.size])
    cand = {"K1": Z["K1"][apos], "K2": Z["K2"][apos], "K3krw": Z["K3krw"][apos]}
    cand["K4"] = cand["K1"]            # K4 = z(K1) x fund-rank indicator: valid exactly where K1 is valid (indicator is defined on eligible names)
    cov = {}; valid = {}; checks = {}
    for nm, a in cand.items():
        v = np.isfinite(a) & en; nv = v.sum(1)
        valid[nm] = {int(y): int(((nv >= MIN_SUBSET) & (EVY == y)).sum()) for y in sorted(set(EVY.tolist()))}
        checks[nm] = years_assert(valid[nm])
        cov[nm] = {int(y): round(float(v[EVY == y].sum() / max(en[EVY == y].sum(), 1)), 4) for y in EXPECTED_EVAL_YEARS}
        rec.setdefault("O1_mean_set_size_by_year", {})[nm] = {int(y): round(float(nv[EVY == y].mean()), 1) for y in EXPECTED_EVAL_YEARS}
    k1v = np.isfinite(cand["K1"]) & en
    gross = {k: {int(y): round(float((held[k][EVY == y] * k1v[EVY == y]).sum() / max(held[k][EVY == y].sum(), 1e-12)), 4) for y in EXPECTED_EVAL_YEARS} for k in held}
    # controls of the assertion itself (AMENDMENT §2 item 5)
    ctl_missing = years_assert({2023: 500, 2024: 500, 2025: 0, 2026: 500}); ctl_full = years_assert({2023: 500, 2024: 500, 2025: 500, 2026: 500})
    rec["controls"] = {"synthetic_missing_2025": ctl_missing, "synthetic_full": ctl_full,
                       "ok": ctl_missing.startswith("STOP") and ctl_full == "OK"}
    assert rec["controls"]["ok"], rec["controls"]
    rec["candidates_sha256"] = Z.sha; rec["valid_anchors_by_year"] = valid; rec["eval_year_assertion"] = checks
    rec["krw_coverage_of_NC_eligible_pairs"] = cov; rec["K1_valid_share_of_NC_held_gross"] = gross
    rec["note_K3_K4"] = "K3 validity = KRW part only (Binance qvk part and the per-anchor median are applied on pod2 at statistic time); K4 validity = K1 validity"
rec["fetched_keys"] = FETCHED
assert not any(k.startswith(f) for ks in FETCHED.values() for k in ks for f in FORBIDDEN), "a forbidden key was fetched"
out = f"{T7}/receipts/nc_2026-09-27/T7NC_ZERO_{STAGE}.json"; os.makedirs(os.path.dirname(out), exist_ok=True)
blob = json.dumps(rec, indent=1).encode(); tmp = out + ".tmp"
with open(tmp, "wb") as f: f.write(blob); f.flush(); os.fsync(f.fileno())
os.replace(tmp, out); assert hashlib.sha256(open(out, "rb").read()).hexdigest() == hashlib.sha256(blob).hexdigest()
print(f"T7NC_ZERO_{STAGE} DONE {hashlib.sha256(blob).hexdigest()[:16]}")
if STAGE == "B":
    bad = {k: v for k, v in rec["eval_year_assertion"].items() if v != "OK"}
    if bad: print("STOP", json.dumps(bad)); sys.exit(2)
