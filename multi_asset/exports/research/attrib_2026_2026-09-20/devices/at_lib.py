#!/usr/bin/env python3
"""at_lib.py — shared library for docs/PREREG_attribution_2026_vs_history_2026-09-20.md (174250770, sha 40a72981):
the finest-grained attribution of the CERTIFIED PRODUCTION PATH (object B, arm A0, reading `scaled`) over
2022-06-30 → 2026-08-31 (+ the A0_ext extension to 2026-09-18T20Z, description only).

WHAT THIS MODULE IS. Pinned inputs, deterministic loaders, the executor's own reshape (copied by VALUE from the
mirrored running tree, not re-derived), the frozen characteristic / grouping / condition definitions, an
INDEPENDENT re-implementation of the baseline-table statistics (so the control reproduction is a real control
and not a call into the device being checked), and the moving-block bootstrap of PREREG §3.

WHAT IT IS NOT. It never reads a live directory, never calls an exchange, never touches a GPU. It writes only
under /workspace/attrib_2026_2026-09-20/.

──────────────────────────────── FROZEN DEFINITIONS (written before any number of this stream) ───────────────

UNITS. Every contribution is **bps per anchor per unit of TARGET gross**, the same unit as the published
baseline table (`RESULT_baseline_tables_A0_objB_2026-09-19.md` §2: price / funding_paid / fee / g), whose
denominator is gm·NAV(A) with gm = 2.0. A paper book normalised to Σ|w| = 1 therefore reports in the same unit.

THE TWO LAYERS, NEVER MIXED.
  L1 REALISED — the simulator's own per-anchor cash (32 fill paths, path mean): price_trade, funding, fee,
     turnover, NAV, stops, halts. This is the ONLY layer that produces the per-year table, g, Sharpe, drawdown.
  L2 PAPER — the target book as written by the producer, reshaped exactly as the executor reshapes it, marked
     to the certified price table and the spliced funding ledger. This is the ONLY layer that can be cut per
     name / per leg / per group, because the simulator emits no per-name cash.
  Every table says which layer it is on, and §L2↔L1 reconciliation (device at_attrib, block R) reports the
  per-period residual L2 − L1 in the same unit. The residual is execution (fills, timing offset N+24 min,
  per-name stops, day-stop flattens, halts, dust, clamps, pops) and is NEVER silently absorbed.

PAPER BOOK W(E).  pop(E) = the names the producer wrote a non-zero weight for at anchor E (the `scaled` CSR row
  of TARGETS_A0_*.npz; kind 2 = combo file, kind 1 = king file — whichever was written IS the traded book).
  v = target[pop];  v ← v − mean(v);  v ← v / Σ|v|;  W = v on pop, 0 elsewhere.
  This is `apply_withhold_and_reshape` → `signal/legs.py::reshape_after_withhold(redemean=True, rescale=True)`
  of the mirrored running tree 409ea16 (legs.py 1e655daf, L176–200), with the pop / force_flat / clamp steps
  NOT applied — those depend on the venue state and on the per-name stop chain, i.e. on execution, and they are
  part of the L2 − L1 residual by construction. Σ|W| = 1 by construction (checked per anchor).

LEG BOOKS AND THE TWO ATTRIBUTION ROUTES (PREREG §2-A).
  The producer's P3 vector record stores, per anchor, the two component books that combo_stage mixes:
  `kc` (king component) and `fc` (funding-momentum component), plus `combo` (what it wrote) and `king_file`.
  Seats: `combo_meta.w3_masked` = [φ_king, φ_mid(=0 throughout), φ_fund] of P3.json.
  For an anchor whose written file is the KING file (kind 1) the traded book has no fund component:
  φ_king := 1, φ_fund := 0, kc := king_file, fc := 0. Declared here, before any number.

  a_i = φ_king · (kc_i − mean_pop_mix(kc)),  b_i = φ_fund · (fc_i − mean_pop_mix(fc)),  m_i = a_i + b_i,
  pop_mix = {i : φ_king·kc_i ≠ 0 or φ_fund·fc_i ≠ 0},  L = Σ_pop_mix |m_i|.
  (Demeaning is linear, so the executor's reshape of the mix splits exactly into the two legs; the L1 rescale
   is one common scalar. That is why the split is exact rather than approximate.)

  A1 (seat-weighted leg route):  A1_king = 1e4·Σ (a_i/L)·x_i,  A1_fund = 1e4·Σ (b_i/L)·x_i,
      where x = the per-name 4h price return (or the negative of the funding paid, etc.). A1_king + A1_fund is
      the MIX book's own contribution — the book combo_stage would have written with no FTRIM, no EMA, no band.
  A2 (name-level linear split of the TRADED book, the prereg's literal wording):
      s_i = a_i / m_i when |m_i| ≥ EPS_SHARE, else s_i = φ_king/(φ_king+φ_fund);  EPS_SHARE = 1e-12 (absolute;
      book weights are O(1e-3)). A2_king = 1e4·Σ s_i·W_i·x_i, A2_fund = 1e4·Σ (1−s_i)·W_i·x_i.
      A2_king + A2_fund = the traded book's paper contribution, EXACTLY (no residual).
  A2b (stability cross-read, same frozen moment): A2b_king = A1_king, A2b_fund = A1_fund, and the named
      residual A2b_shape = 1e4·Σ (W_i − m_i/L)·x_i = the FTRIM / EMA / band / re-normalisation reshaping.
      A2b_king + A2b_fund + A2b_shape = the traded book's paper contribution, EXACTLY.
  The prereg asks for A1 and A2 to be reconciled and for every period where they differ by more than 5 % to be
  named. "Differ by more than 5 %" is read as: |A1_leg − A2_leg| > 0.05 · max(|A1_total|, |A2_total|), per leg.

PER-NAME RETURN AND FUNDING.
  RET_i(E) = exp(P[row(E+4h), i] − P[row(E), i]) − 1, P = the certified restored log-price table on the full
  5-minute grid (price_full_raw_x0918r.npy 23af32bd, the table the certified run itself priced with). The table
  is filled outside a name's life, so RET is IDENTICALLY 0 there; a name is IN LIFE at t iff
  meta.first_fin ≤ t ≤ meta.last_fin, and the weight carried on out-of-life names is reported separately.
  FUNDPAID_i(E) = Σ over settlements with ft ∈ (E, E+4h] of rate_i(ft), from the spliced ledger 073088e5
  (P2 ≤ 2026-09-01T02Z, stream D after). POSITIVE = the book pays when it is long.

FEE PER NAME. The simulator emits fee only per anchor. fee_i(E) = L1_fee(E)·|ΔW_i|/Σ_j|ΔW_j|, ΔW against the
  previous anchor of the axis (ΔW = W at the first anchor): the REALISED anchor fee, allocated by the paper
  book's own per-name turnover. Σ_i fee_i = the realised fee exactly (checked). net_i = price_i − fundpd_i −
  fee_i, so Σ_i net_i = paper price − paper funding − realised fee, and realised g − Σ_i net_i = the execution
  residual, which is reported per period and never absorbed.

MARKET vs SELECTION (PREREG §2-C; the C0 frozen split, RESULT_c0_attribution_2026-09-19.md §3):
  ȳ(E) = the equal-weight mean of RET over the anchor's producer member list `pm` restricted to IN-LIFE names.
  market_i = W_i·ȳ, selection_i = W_i·(RET_i − ȳ); price_i = market_i + selection_i identically.

NAME CHARACTERISTICS (PREREG §2-B: the SAME channels and the SAME missing-data handling as c0_chars.py
f4c13d76, recomputed over the longer window on the certified-path sources):
  AGE  = (E − first cache bar with log_cnt finite and > 0) / 86400, cache ch 4; cache starts 2022-01-01 ⇒
         left-censored names are flagged and fall in the top bucket.
  RN8  = f_fund_now · 8 / f_fund_iv (iv NaN or ≤ 0 → 8), 8h-equivalent, panel row of E.
  MOM30= Π(1+y4) − 1 over the 180 preceding 4h intervals. COMPUTED ON THE CERTIFIED PRICE TABLE as
         exp(P[row(E)] − P[row(E−720h)]) − 1 (identically the same quantity: y4 RAW = Π(1+r)−1 per 4h), NaN
         unless the name is in life over the whole 30 days. c0 read it from meta_newprod_v4 y4; that file stops
         at 2026-08-30T20Z and starts after the window's first anchors, the certified price table does not —
         the two are cross-checked in at_build (correlation + max|Δ| on the overlap) and both are reported.
         The first 180 anchors of the price grid have no 30-day history ⇒ NaN (they are inside PARTIAL_RECIPE).
  LIQ  = log( Σ expm1(log_qv) · 288 / n ) over the 288 cache bars closing in (E−24h, E]; n = bars with finite
         log_qv; NaN if n < 144. Cache ch 3.
  TBF  = simple mean of cache ch 6 over the bars of that window with log_cnt > 0 and finite tbf; NaN if < 48.
  Holefix policy = INCL (filled bars are official klines and are used), as c0's primary.

GROUPS (PREREG §2-B; the C0 frozen cohort rules, RESULT_c0_attribution_2026-09-19.md §1.4, reused verbatim):
  AGE   <90d | 90-180d | 180-365d | 365-730d | >=730d                                        (5, fixed, left-closed)
  FUND  <=-10bp | (-10,0)bp | [0,base) | base 1bp | (base,5]bp | >5bp                          (6, fixed)
        edges on RN8 in bp/8h: ≤ −10 | (−10, 0) | [0, 0.999) | [0.999, 1.001] | (1.001, 5] | > 5
  MOM30 L | M | H   — per-anchor terciles INSIDE the member set over finite values:
  LIQ   L | M | H     q = np.quantile(v, [1/3, 2/3]); L: v < q⅓; H: v > q⅔; M: the closed middle
  TBF   L | M | H
  DIR   long | short  — sign(W_i); W_i = 0 contributes nothing
  NA    any characteristic NaN
  ⇒ the group-test count written into the run config BEFORE running is 5+6+3+3+3+2 = 22.

ANCHOR CONDITIONS (PREREG §2-D, 8 of them; the six that coincide with a G0 state variable are TAKEN DIRECTLY
from the frozen G0 output g0_state_vars_x0918.npz / g0_labels_x0918.npz, EXCL primary):
  DISP    = RG-DISP     cross-sectional sd of member 24h returns
  FDISP   = RG-FDISP    cross-sectional sd of member current funding rate
  FLEVEL  = RG-FLEVEL   cross-sectional median of member current 8h-equivalent funding rate
  BREADTH = RG-BREADTH  share of members with positive 7-day return
  VOL     = RG-VOL      BTC 7-day realised volatility of 5-minute returns
  ALT     = RG-ALT      member median 30-day return − BTC 30-day return
  UBAR    = ȳ(E), the equal-weight member-universe 4h return (new here; the prereg's 宇宙平均 4h 收益)
  TURN    = the book's realised turnover per unit target gross (AGG turnover_over_gmnav0_mean; 书的换手)
  RG-TREND (BTC 30-day return) is the seventh G0 variable; it is REPORTED but, because PREREG §3 writes the
  family as "§2-D 的 8 个条件量", it is NOT a member of the multiple-comparison family. Said here, before running.
  The six taken from G0 carry G0's own frozen labels (LAB_EXCL, expanding-window terciles, 1,080-anchor warm-up).
  UBAR and TURN are new, so they are labelled by the SAME rule, re-implemented: at anchor E the tercile
  thresholds are np.quantile of the finite values over anchors ≤ E on this device's axis, no label before
  1,080 anchors of history. Declared here, before the first run.

STATISTICS (PREREG §3). Moving-block bootstrap on calendar UTC days, non-circular: block start uniform on
  0..n−b, ceil(n/b) blocks concatenated and truncated to n; B = 10,000; main block 5 days, sensitivity 1 and 10;
  rng = numpy.random.default_rng([20260920, k]) with k = the test's index in the frozen family list.
  A mean "per anchor" statistic is resampled as Σ(day sums)/Σ(day counts) so that days of unequal length cannot
  be silently equal-weighted. For a two-window contrast the SAME draw index k resamples both windows (they are
  disjoint, so the draws are independent by construction) and Δ* = mean_A* − mean_B*.
  Two-sided centred p = (1 + #{|Δ* − Δ̂| ≥ |Δ̂|}) / (B + 1).
  FAMILY = the 22 group tests of §2-B + the 8 condition tests of §2-D = 30 hypotheses, Holm at 0.05.
    group test  k = 0..21 : H0 mean net contribution per anchor per gross is the same in P_2026 and P_HIST
    cond. test  k = 22..29: H0 the book's mean g in the condition's top tercile equals that in its bottom
                            tercile, over the FULL_RECIPE window
  §2-E / §2-F / §2-G carry no significance marks (prereg §3).

PERIODS (the baseline table's own frozen splits, reused so that L1 numbers are comparable line by line):
  2022H2 · 2023pre · 2023full · 2024 · 2025 · 2026H1 · 2026JA (07-01→08-31) · FULL_RECIPE · PARTIAL_RECIPE,
  plus 2026 = 2026-01-01→2026-08-31 and HIST = 2023-06-30T04Z→2025-12-31T20Z (the prereg's contrast windows).
"""
import calendar, hashlib, json, math, os, sys, time

import numpy as np

W_ = "/workspace"
ROOT = f"{W_}/attrib_2026_2026-09-20"
NW = 829
H4 = 14400
DAY = 86400
GM = 2.0
B_BOOT = 10000
BLOCK_MAIN = 5
BLOCK_SENS = (1, 10)
RNG_BASE = 20260920
EPS_SHARE = 1e-12

RUN_A0 = f"{W_}/baseline_tables_2026-09-19/runs/OBJB_A0_scaled_rule_raw_UAFE"
RUN_TAG = "OBJB_A0_scaled_rule_raw_UAFE"

PINS = {
    # object B — the certified production path's targets and producer records
    "TARGETS_A0_MAIN": (f"{W_}/object_b_2026-09-19/work/A0_main/TARGETS_A0_main.npz",
                        "b9f0dc9f2011f9defaac80b116415de3f4d75ffb497cbb9533cd995879036c41"),
    "TARGETS_A0_EXT": (f"{W_}/object_b_2026-09-19/work/A0_ext/TARGETS_A0_ext.npz",
                       "085d88585244190dde4ec71cddbea1a6ff22f8c0bcf5bc583f54dc3cb5d7de04"),
    "P3VEC_A0_MAIN": (f"{W_}/object_b_2026-09-19/work/A0_main/P3.vec.npz",
                      "dae0107140673c98f346073733a99b48aea33b002a51ea6c660bb75aac554d92"),
    "P3JSON_A0_MAIN": (f"{W_}/object_b_2026-09-19/work/A0_main/P3.json",
                       "cff3e160f4a4961e97043cdcdb93a105c24694f83931509dc5539bac72826bcd"),
    "P3JSON_A0_EXT": (f"{W_}/object_b_2026-09-19/work/A0_ext/P3.json",
                      "ac70210ad1519e9989cfae640be88bc3d360ae00d043fa7d08362c31a615546e"),
    "P3VEC_A0_EXT": (f"{W_}/object_b_2026-09-19/work/A0_ext/P3.vec.npz",
                     "4295b64053d493100a5609c920dceb7e5fe3896d37cb43b08be60f291d49d190"),
    "UNIVERSE_EXT": (f"{W_}/object_b_2026-09-19/work/ext_inputs/universe_ext.npz",
                     "3ee838cfc4ee4b90cef9202716af8645ff601b69137346d518ea706a5f4d598f"),
    # the certified run's own price / funding / regime inputs (the frozen RUN_CONFIG's pins)
    "PRICE_FULL": (f"{W_}/baseline_tables_2026-09-19/work/price_full_raw_x0918r.npy",
                   "23af32bd97c267d126c2109641815b92082b8688e35bcfbaaa1e88c2dc5bb5d8"),
    "PRICE_META": (f"{W_}/baseline_tables_2026-09-19/work/price_full_raw_x0918r_meta.npz",
                   "d1e49cc9f0a7ddc4104feb52a42da3024ba1e66ad5891a26c96f00cff7ce5d90"),
    "LEDGER_SPLICED": (f"{W_}/baseline_tables_2026-09-19/funding/ledger_spliced_p2_to_20260901T0200_streamD_after.npz",
                       "073088e503c026d6071c76764426503616d53570e5f3763807df27ea7cc80362"),
    "G0_LABELS": (f"{W_}/baseline_tables_2026-09-19/g0x/g0_labels_x0918.npz",
                  "c3832939e1b0133369af96ea2866e3cfb226274aeda98c81b82e531654b185b6"),
    "G0_STATE": (f"{W_}/baseline_tables_2026-09-19/g0x/g0_state_vars_x0918.npz",
                 "79753acde3c13d217dd524e15627674774cf915f6a505a2740466bbf3dc7a40f"),
    # feature channels
    "PANEL_X0918": (f"{W_}/axis_0919/panels/wide_panel_4h_v2ext_x0918.npz",
                    "e5fcb4198ddebb52fe6e92438c5111ed22f41dbacbd9ec9af459c9ac6c40b47c"),
    "CACHE_X0918R": (f"{W_}/axis_0919/x0918r/data/dlnative_5m_wide829_f16_holefix2_x0918r.npz",
                     "08bb295745e6df84cb42574ef073dc54817a19ad7754bf6319cfcb30bd9baa75"),
    "META_V4": (f"{W_}/fp2_2026-09/refute_C6_2/altrun/meta_newprod_v4.npz",
                "e1cf515eca46b0a1a7afe2bd6e89039cb68f4eea1a0428353e2f3aac989890a7"),
    # the published control and the frozen run config that produced it
    "BT_MAIN_A0": (f"{W_}/baseline_tables_2026-09-19/receipts/BT_MAIN_A0.json",
                   "fa3c2ce7c20e6b997a6c88e75ba532e758c0a80eaa900774338fb7ede24eaf94"),
    "BT_RUN_CONFIG": (f"{W_}/baseline_tables_2026-09-19/RUN_CONFIG_main_A0_2026-09-19.json",
                      "7b6dca2c48feda294676ab5ce46b748c71ab87103cc64ead5be7957fe5bbfe93"),
    "AGG_A0": (f"{RUN_A0}/AGG_{RUN_TAG}.npz",
               "d01eebe3f6a05b6af474dbdbae6b99ff0e03198a507f8f53ab3170df7888aa1a"),
    # provenance of the reshape this module copies by value
    "MIRROR_LEGS": (f"{W_}/replay_exec_mirror_59875e5a/exec_tree_409ea16/signal/legs.py",
                    "1e655daf64b2b563841a95326be19a83bb9e0a6b158e77f346abdf90f9c2ff63"),
    # provenance of the frozen characteristic definitions this module re-implements
    "C0_CHARS": (f"{ROOT}/devices/c0_chars_f4c13d76_REFERENCE.py",
                 "f4c13d76ebffcd1339b8d6615e5083e3f1b39a1fe6850aaf42b5514823c399d9"),
}

PERIODS = [
    ("2022H2", "2022-06-30T00:00:00Z", "2022-12-31T20:00:00Z", True),
    ("2023pre", "2023-01-01T00:00:00Z", "2023-06-30T00:00:00Z", True),
    ("2023full", "2023-06-30T04:00:00Z", "2023-12-31T20:00:00Z", False),
    ("2024", "2024-01-01T00:00:00Z", "2024-12-31T20:00:00Z", False),
    ("2025", "2025-01-01T00:00:00Z", "2025-12-31T20:00:00Z", False),
    ("2026H1", "2026-01-01T00:00:00Z", "2026-06-30T20:00:00Z", False),
    ("2026JA", "2026-07-01T00:00:00Z", "2026-08-31T00:00:00Z", False),
    ("2026", "2026-01-01T00:00:00Z", "2026-08-31T00:00:00Z", False),
    ("HIST", "2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z", False),
    ("FULL_RECIPE", "2023-06-30T04:00:00Z", "2026-08-31T00:00:00Z", False),
    ("PARTIAL_RECIPE", "2022-06-30T00:00:00Z", "2023-06-30T00:00:00Z", True),
    ("WHOLE_WINDOW", "2022-06-30T00:00:00Z", "2026-08-31T00:00:00Z", True),
]

AGE_BINS = ("<90d", "90-180d", "180-365d", "365-730d", ">=730d")
FUND_BINS = ("<=-10bp", "(-10,0)bp", "[0,base)", "base 1bp", "(base,5]bp", ">5bp")
TER_BINS = ("L", "M", "H")
DIR_BINS = ("long", "short")
GROUP_SPECS = (("AGE", AGE_BINS), ("FUND", FUND_BINS), ("MOM30", TER_BINS), ("LIQ", TER_BINS),
               ("TBF", TER_BINS), ("DIR", DIR_BINS))
N_GROUP_TESTS = sum(len(b) for _, b in GROUP_SPECS)          # 22, frozen before running
COND_NAMES = ("DISP", "FDISP", "FLEVEL", "BREADTH", "VOL", "ALT", "UBAR", "TURN")   # 8, frozen
COND_EXTRA = ("TREND",)                                       # reported, not in the family
G0_VARS = ("RG-TREND", "RG-BREADTH", "RG-DISP", "RG-FLEVEL", "RG-FDISP", "RG-VOL", "RG-ALT")
COND_FROM_G0 = {"DISP": "RG-DISP", "FDISP": "RG-FDISP", "FLEVEL": "RG-FLEVEL", "BREADTH": "RG-BREADTH",
                "VOL": "RG-VOL", "ALT": "RG-ALT", "TREND": "RG-TREND"}


# ───────────────────────────── plumbing ─────────────────────────────
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def utc(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def ts(s):
    return int(calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")))


class Checks:
    def __init__(self, t0=None):
        self.rows = []
        self.fails = []
        self.t0 = t0 or time.time()

    def log(self, *a):
        print("[%7.0fs]" % (time.time() - self.t0), *a, flush=True)

    def __call__(self, name, ok, detail=None):
        ok = bool(ok)
        self.rows.append({"check": name, "ok": ok, **({"detail": detail} if detail is not None else {})})
        if not ok:
            self.fails.append(name)
        self.log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:400] if detail is not None else "")
        return ok


def verify_pins(chk, keys=None):
    out = {}
    for k in (keys or PINS):
        p, s = PINS[k]
        if not os.path.exists(p):
            chk(f"input_sha.{k}", False, {"path": p, "why": "missing"})
            continue
        got = sha(p)
        out[k] = {"path": p, "sha256": got}
        chk(f"input_sha.{k}", got == s, {"expected": s[:16], "got": got[:16]})
    return out


def rec_head(device, argv):
    return {"device": device, "self_sha256": sha(os.path.abspath(sys.argv[0])), "lib_sha256": sha(os.path.abspath(__file__)),
            "argv": list(argv), "env": {k: os.environ[k] for k in sorted(os.environ)},
            "numpy": np.__version__, "python": sys.version.split()[0], "utc_start": utc(time.time()),
            "pid": os.getpid(), "pgid": os.getpgid(0)}


def write_receipt(rec, chk, path, extra=None):
    rec.update(extra or {})
    rec.update({"checks": chk.rows, "n_checks": len(chk.rows), "failed": chk.fails,
                "VERDICT": "PASS" if not chk.fails else "FAIL", "utc_end": utc(time.time())})
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=1, default=str)
    os.replace(tmp, path)
    return rec["VERDICT"]


def rss_gb():
    try:
        with open("/proc/self/status") as f:
            for ln in f:
                if ln.startswith("VmHWM:"):
                    return float(ln.split()[1]) / 1048576.0
    except Exception:
        pass
    return float("nan")


# ───────────────────────────── book algebra ─────────────────────────────
def reshape_pop(vals):
    """signal/legs.py::reshape_after_withhold(redemean=True, rescale=True) on the population `vals`
    (1-D, the names the producer wrote). Returns the unit-gross book on the same population."""
    v = np.asarray(vals, np.float64).copy()
    v = v - v.mean()
    s = np.abs(v).sum()
    if s > 0:
        v = v / s
    return v


def csr_dense(z, pref, a, nw=NW, dtype=np.float64):
    off = z[pref + "_off"]
    i0, i1 = int(off[a]), int(off[a + 1])
    out = np.zeros(nw, dtype)
    if i1 > i0:
        out[z[pref + "_idx"][i0:i1]] = z[pref + "_val"][i0:i1]
    return out


def csr_idx(z, pref, a):
    off = z[pref + "_off"]
    return z[pref + "_idx"][int(off[a]):int(off[a + 1])]


# ───────────────────────────── statistics (independent re-implementation) ─────────────────────────────
def daily_returns(A, r):
    """UTC day d: Π over the 4h windows whose anchor is in d of (1 + r) − 1."""
    d = (np.asarray(A, np.int64) // DAY) * DAY
    ud, inv = np.unique(d, return_inverse=True)
    acc = np.ones(len(ud))
    np.multiply.at(acc, inv, 1.0 + np.asarray(r, float))
    return ud, acc - 1.0


def cagr_of(rd):
    rd = np.asarray(rd, float)
    n = len(rd)
    if n == 0:
        return None
    nav = np.cumprod(1.0 + rd)
    if np.any(nav <= 0):
        return -1.0
    return float(nav[-1] ** (365.0 / n) - 1.0)


def sharpe_of(rd):
    rd = np.asarray(rd, float)
    if len(rd) < 2:
        return None
    s = rd.std(ddof=1)
    if s == 0:
        return None
    return float(rd.mean() / s * math.sqrt(365.0))


def maxdd_of(nav_rel):
    """min over the sampled NAV of NAV/cummax − 1, with 1.0 prepended as the starting point."""
    x = np.concatenate([[1.0], np.asarray(nav_rel, float)])
    return float((x / np.maximum.accumulate(x) - 1.0).min())


def maxdd_from_returns(r):
    return maxdd_of(np.cumprod(1.0 + np.asarray(r, float)))


def worst30_of(rd):
    rd = np.asarray(rd, float)
    if len(rd) < 30:
        return None
    c = np.concatenate([[1.0], np.cumprod(1.0 + rd)])
    return float((c[30:] / c[:-30] - 1.0).min())


def cvar5_of(rd):
    rd = np.asarray(rd, float)
    if len(rd) == 0:
        return None
    k = int(math.ceil(0.05 * len(rd)))
    return float(np.sort(rd)[:k].mean())


# ───────────────────────────── bootstrap ─────────────────────────────
def _block_index(rng, n, b, B):
    """B × n index matrices of the non-circular moving-block bootstrap on 0..n-1."""
    nb = int(math.ceil(n / b))
    starts = rng.integers(0, max(n - b, 0) + 1, size=(B, nb))
    off = np.arange(b)[None, None, :]
    idx = (starts[:, :, None] + off).reshape(B, nb * b)[:, :n]
    return idx


def boot_mean_ratio(day_num, day_den, b=BLOCK_MAIN, B=B_BOOT, seed_k=0):
    """bootstrap of Σ(day numerators)/Σ(day denominators) — the per-anchor mean, resampled by day block."""
    num = np.asarray(day_num, float)
    den = np.asarray(day_den, float)
    n = len(num)
    if n == 0:
        return None
    rng = np.random.default_rng([RNG_BASE, int(seed_k)])
    idx = _block_index(rng, n, b, B)
    s_num = num[idx].sum(1)
    s_den = den[idx].sum(1)
    with np.errstate(all="ignore"):
        draws = np.where(s_den > 0, s_num / np.maximum(s_den, 1e-300), np.nan)
    return draws


def boot_two_window(numA, denA, numB, denB, b=BLOCK_MAIN, B=B_BOOT, seed_k=0):
    """paired draw index k resamples BOTH disjoint windows; returns (Δ̂, Δ* draws)."""
    numA, denA, numB, denB = (np.asarray(x, float) for x in (numA, denA, numB, denB))
    hat = (numA.sum() / denA.sum() if denA.sum() > 0 else np.nan) - (numB.sum() / denB.sum() if denB.sum() > 0 else np.nan)
    rng = np.random.default_rng([RNG_BASE, int(seed_k)])
    ia = _block_index(rng, len(numA), b, B)
    ib = _block_index(rng, len(numB), b, B)
    with np.errstate(all="ignore"):
        da = numA[ia].sum(1) / np.maximum(denA[ia].sum(1), 1e-300)
        db = numB[ib].sum(1) / np.maximum(denB[ib].sum(1), 1e-300)
    return float(hat), da - db


def ci_p(hat, draws, two_sided=True):
    d = np.asarray(draws, float)
    d = d[np.isfinite(d)]
    if d.size == 0:
        return {"point": hat, "ci95": [None, None], "p": None, "B_used": 0}
    lo, hi = np.percentile(d, [2.5, 97.5])
    c = d - hat
    if two_sided:
        p = (1.0 + int((np.abs(c) >= abs(hat)).sum())) / (len(d) + 1.0)
    else:
        p = (1.0 + int((c <= hat).sum())) / (len(d) + 1.0)
    return {"point": float(hat), "ci95": [float(lo), float(hi)], "p": float(p), "B_used": int(len(d))}


def holm(pvals, alpha=0.05):
    """Holm–Bonferroni; returns the rejection flags and the adjusted thresholds in the input order."""
    items = [(p if p is not None else 1.0, i) for i, p in enumerate(pvals)]
    items.sort()
    m = len(items)
    rej = [False] * m
    thr = [None] * m
    stop = False
    for r, (p, i) in enumerate(items):
        t = alpha / (m - r)
        thr[i] = t
        if not stop and p <= t:
            rej[i] = True
        else:
            stop = True
    return rej, thr


# ───────────────────────────── period helpers ─────────────────────────────
def period_mask(A, lo, hi):
    A = np.asarray(A, np.int64)
    return (A >= ts(lo)) & (A <= ts(hi))


def day_aggregate(A, x, mask=None):
    """per-UTC-day (sum of x, count of anchors) over the masked anchors, in day order."""
    A = np.asarray(A, np.int64)
    x = np.asarray(x, float)
    if mask is not None:
        A = A[mask]
        x = x[mask]
    d = (A // DAY) * DAY
    ud, inv = np.unique(d, return_inverse=True)
    s = np.zeros(len(ud))
    c = np.zeros(len(ud))
    np.add.at(s, inv, x)
    np.add.at(c, inv, 1.0)
    return ud, s, c
