"""0C — REGRESSION ASSERTION for the funding settlement-interval dimension bug. RUN AT EVERY PANEL REBUILD.

> created 2026-07-25 | Session: 0C | 状态: permanent guard | 作废条件: 从不 (面板重建流程的常驻检查)

WHY THIS EXISTS
---------------
`FUND_EMA` / `funding_ema` stored the EMA of the PER-SETTLEMENT-PERIOD funding rate, while 4h-settled
and 8h-settled coins coexist in the panel. A 4h coin with identical annualised carry shows HALF the
per-period rate. Cross-sectional rank-centring -- which the engine's funding leg uses -- removes
INDIVIDUAL scale but NOT a GROUP-level location shift, so the 4h cohort was pushed systematically to
one side (measured: -0.3745 rank units on a [-1,1] scale, ~19% of full range).

TWO CHANNELS CARRY IT, NOT ONE
------------------------------
  ch  0  funding_ema   -- the raw factor
  ch 28  xsr_fund      -- centered pct-rank OF funding_ema (build_wide_dl.py L80-91)
A rank transform is EXACTLY the operation that preserves a group shift, so xsr_fund carries the same
artifact in a purer form. xsr_fund is derived from funding_ema in the same script, so fixing the
source fixes both -- but that is an assumption about the build graph, and assumptions rot. This
script VERIFIES it instead of trusting it.

WHAT IT CHECKS
--------------
For each channel, per anchor, over the member cross-section:
    gap = mean(rank_centred(x) | 4h-settled) - mean(rank_centred(x) | 8h-settled)
A correctly-dimensioned factor has |mean gap| small. The control is gap(Y4): the 4h cohort genuinely
underperforms (measured -0.033), so a SMALL residual gap is expected and legitimate -- the fail
threshold is set well above it and well below the broken value.

  PASS  |mean gap| <= 0.20 for BOTH channels
  FAIL  otherwise   (broken shipped value was -0.3745; corrected value +0.1463)

★★ TWO CALIBERS EXIST ON PURPOSE — AND THAT IS WHY THIS GATE IS PER-ARTIFACT (0C 2026-07-27)
--------------------------------------------------------------------------------------------
This gate was armed on 2026-07-25 asserting the CORRECTED signature on every panel it was pointed
at. That was wrong, and it stopped the whole shadow pipeline on its first armed daily run
(2026-07-26 09:02Z, `run_daily` exit 1, report frozen 28h -> factor_health STALE).

The pipeline carries two funding calibers **deliberately**:

  exports/wide_dl_full.npz        the FROZEN model-input panel. Built 2026-07-11, i.e. BEFORE the
                                  2026-07-25 source fix, and never rebuilt since -> AS-TRAINED
                                  (un-normalised). The frozen king/s2 heads were trained on it and
                                  were NOT retrained when the factor was fixed.
  exports/live/wide_dl_live.npz   the daily splice (engine/live/build_tail.py ->
                                  funding_derive.real_funding_ema). It reproduces the AS-TRAINED
                                  caliber ON PURPOSE so the live panel matches the training panel
                                  -- see funding_derive.py:110 ("does NOT normalise the rate; this
                                  path emits the AS-TRAINED caliber on purpose").

⇒ Normalising the live splice would put the model's INPUT distribution out of step with the panel
  its frozen weights were fitted on, without retraining -- and this gate would go GREEN for it.
  A stale report is a VISIBLE ABSENCE; that would be an INVISIBLE DRIFT. So the gate asserts the
  caliber each artifact IS SUPPOSED TO HAVE, rather than asserting one caliber for all of them.

⇒ FORWARD NOTE: **if the heads are ever retrained on the normalised caliber, the live-side
  assertion must flip with the model version.** The two are one decision, not two -- registered
  against the model version in docs/OPEN_ITEMS.md, not enforced mechanically here.

⇒ ★ THE BANDS ARE CALIBRATED ON HISTORY-SPANNING SAMPLING, AND THAT IS LOAD-BEARING (0C, measured
  while building the red test). The 4h/8h cohort separation is NOT stationary: the last 4000
  anchors of the live panel read -0.0485, while the same panel sampled across its full history
  reads -0.3761 (full-panel value -0.3767). ⇒ Pointed at a short/recent window this gate would call
  a perfectly good as-trained panel "corrected" and fail it. It is a guard for FULL-HISTORY panel
  rebuilds; do not repurpose it for a rolling window without re-measuring both references on that
  window.

⇒ THE MIDDLE IS FORBIDDEN. A reading that sits near NEITHER reference means someone changed the
  funding dimension without declaring which caliber they intended. That is the case this gate most
  needs to catch, and a single two-sided threshold cannot express it.

⇒ WHICH CALIBER AN ARTIFACT IS SUPPOSED TO HAVE COMES FROM THE ARTIFACT (0C 2026-07-29). A stamp
  written into the npz by its builder (`exports/eda/panel_caliber_stamp.py`), or — for the frozen
  training panel, which must not be rewritten — a declaration keyed to its SHA-256. Never from the
  filename, never from the path: a path key is inherited by whatever file is written there next.

Usage:  python multi_asset/exports/eda/assert_funding_dim.py [--panel <panel.npz>] [--caliber auto|corrected|as_trained]
Exit codes (wire into the panel-rebuild pipeline so a regression breaks the build):
    0  the artifact carries the caliber it is supposed to have
    1  it carries the OTHER caliber, or lands in the forbidden middle — a judged verdict
    2  CANNOT JUDGE: the channels or the 4h/8h cohorts needed to measure anything are absent.
       Kept distinct from 1 because "I measured it and it is wrong" and "there was nothing to
       measure" are different facts, and a caller that cannot tell them apart will eventually
       report the first when the second is true.
"""
import os
import sys, json, argparse
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
EDA = MA + "/exports/eda/"
WIDE = os.path.join(os.path.dirname(MA), "data", "wide")
# ★ BOTH BANDS ARE BUILT FROM THE TWO MEASURED REFERENCE VALUES ALREADY DOCUMENTED ABOVE.
# Nothing here is a fresh magic number: a constant that carries a verdict must trace back to the
# artifact it came from. Provenance for both: the 2026-07-25 reproduction recorded in this file's
# header and in exports/eda/funding_dim_fix.py.
REF_AS_TRAINED = -0.3745   # measured gap of the un-normalised (as-shipped/as-trained) caliber
REF_CORRECTED  = +0.1463   # measured gap after rate*(8/interval_h) applied BEFORE the EMA
FAIL_ABS = 0.20            # unchanged tolerance; legitimate return-driven gap is 0.033 (Y4 control)
# Disjointness is a property of these three numbers, not an assumption — asserted at import:
#   |REF_CORRECTED - REF_AS_TRAINED| / 2 = 0.2604 > FAIL_ABS = 0.20
# so the two bands cannot overlap and the gap between them is the forbidden middle.
assert abs(REF_CORRECTED - REF_AS_TRAINED) / 2.0 > FAIL_ABS, \
    "bands would overlap: the forbidden middle would vanish and a mid reading would silently pass"
CHANNELS = ["funding_ema", "xsr_fund"]


def classify_gap(mg):
    """Which caliber does this reading claim to be? 'corrected' / 'as_trained' / 'MIDDLE'."""
    if abs(mg - REF_CORRECTED) <= FAIL_ABS:
        return "corrected"
    if abs(mg - REF_AS_TRAINED) <= FAIL_ABS:
        return "as_trained"
    return "MIDDLE"


def expected_caliber(panel_path, override=None):
    """Which caliber THIS artifact is supposed to have RIGHT NOW.

    ★ MEASURED, NOT ASSUMED (0C 2026-07-27). My first version routed by filename —
    wide_dl_full -> corrected, wide_dl_live -> as_trained — on the reasoning that the full panel is
    "the fixed one". Running it proved otherwise: `exports/wide_dl_full.npz` measures -0.3837, i.e.
    AS-TRAINED. It was built 2026-07-11 and has never been rebuilt with the 07-25 fix. So the
    filename rule would have failed a second artifact that is doing exactly what it should.

    ⇒ Both DL panels are AS-TRAINED today, and that is correct: the frozen king/s2 heads were fitted
      on the un-normalised panel and were not retrained. The CORRECTED caliber currently belongs to
      the FACTOR LEG (the engine's funding leg), not to either DL input panel.
    ⇒ So the default for a DL panel is `as_trained`, and `corrected` must be asked for explicitly —
      which is the state that changes on the day the heads are retrained. See the FORWARD NOTE in
      the header: that flip and the model version are ONE decision.

    ★★ AND IT COMES FROM THE DECLARATION, NOT FROM THE FILENAME (0C 2026-07-27, THIRD correction —
      team-lead ruling: "routing the caliber expectation by filename is today's accident repeated
      with a different file; the expectation must come from the DECLARED state — which generation
      holds this artifact — never from a naming convention").
      My second version routed `*_fundfix.npz -> corrected`. Measurement agreed with it
      (`wide_dl_full_fundfix` +0.1418/+0.1429, `wide_dl_live_fundfix` +0.1461/+0.1471, against the
      corrected reference +0.1463), so it was not wrong TODAY — it was wrong in KIND. A convention
      holds until someone writes a file that does not follow it, and then the gate asserts a caliber
      the artifact was never supposed to have. That is precisely the 07-25 defect.
      ⇒ The declaration already exists: `engine/live/factor_version_registry.py` names, per factor
        version, both panels and the caliber they carry. This function now READS it.
      ⇒ An artifact that is not declared there yields **None**, and the caller must report CANNOT
        JUDGE (exit 2) — never a default. "I do not know what this is supposed to be" is not a pass
        and not a violation, and inventing an answer for it is how a filename rule gets born.
      ⇒ The authoritative caliber map, per the same ruling:
        **the corrected caliber currently belongs to the FACTOR LEG and to NO DL input panel.**
        Every live `wide_dl_*` panel the frozen heads consume is `as_trained`.

    ★★★ AND NOW FROM THE ARTIFACT ITSELF, NOT FROM ITS PATH (0C 2026-07-29, FOURTH correction —
      team-lead ruling: "闸门的选择依据必须是产物自己携带的口径戳(caliber stamp), 不是文件名或路径 ——
      后者会在下一次重命名时静默失效").
      The registry declaration above was keyed by the panel's PATH. That is a declaration, so it was
      not the filename-convention defect — but it fails under `cp`/`mv`/a changed `--out` flag, and
      it fails SILENTLY in the worse direction: the file that inherits the path inherits an
      expectation it was never built to satisfy. Same shape as 07-25, different mechanism.
      ⇒ The caliber now comes from a stamp the builder writes INSIDE the artifact
        (`exports/eda/panel_caliber_stamp.py`), falling back — for artifacts that cannot be
        rewritten, i.e. the frozen training panel — to a declaration keyed by the file's SHA-256.
        Both keys are properties of the CONTENTS. A path is used only to open the file.
      ⇒ See `declared_caliber` below for the resolution order and what each step guarantees.
    """
    if override and override != "auto":
        return override
    return declared_caliber(panel_path)


def _registry():
    """factor_version_registry, or None if unreachable. Never faked: an unreachable registry means
    the declaration cannot be read, which is a CANNOT-JUDGE, not a default."""
    live = os.path.join(MA, "engine", "live")
    if live not in sys.path:
        sys.path.insert(0, live)
    try:
        import factor_version_registry as FVR
        return FVR
    except Exception:
        return None


def declared_caliber(panel_path, with_basis=False):
    """The caliber THIS artifact is DECLARED to carry — read from the artifact, never from its name.

    Resolution order (each step keyed to CONTENTS; the path only opens the file):
      1. the STAMP the builder wrote inside the npz  — rebuilt artifacts. Survives any rename, and
         cannot be inherited by a different file written to the same path.
      2. a SHA-256 declaration in `factor_version_registry.UNSTAMPED_ARTIFACT_CALIBER` — for
         artifacts that predate stamping and must not be rewritten (the frozen training panel:
         rewriting it to add a stamp would break the bit-identity another guard asserts).
      3. nothing -> None. The caller reports CANNOT JUDGE (exit 2). Never a default.

    A malformed stamp raises through as `StampError` and the caller reports CANNOT JUDGE with the
    reason: "somebody declared something and it is broken" is not the same fact as "nobody declared
    anything", and a resolver that flattens the two loses the only one that names a defect.

    Returns the caliber string (or None); with_basis=True returns (caliber, basis-sentence).
    """
    basis = "no declaration found"
    cal = None
    stamp = _stamp_mod()
    if stamp is not None and os.path.exists(panel_path):
        d = stamp.read(panel_path)                    # raises StampError on a broken stamp
        if d is not None:
            cal = d["funding_caliber"]
            basis = (f"stamp carried by the artifact (declared by {d.get('declared_by')} at "
                     f"{d.get('written_utc')})")
    if cal is None:
        FVR = _registry()
        if FVR is not None and os.path.exists(panel_path):
            declared = getattr(FVR, "UNSTAMPED_ARTIFACT_CALIBER", {})
            if declared:
                h = stamp.sha256_16(panel_path) if stamp is not None else None
                if h in declared:
                    cal = declared[h]["caliber"]
                    basis = (f"content sha256_16 {h} declared in factor_version_registry "
                            f"({declared[h].get('artifact')})")
    return (cal, basis) if with_basis else cal


def _stamp_mod():
    """panel_caliber_stamp, or None if unreachable (same rule as the registry: unreachable means
    the declaration cannot be read, which is a CANNOT-JUDGE, not a default)."""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        import panel_caliber_stamp as PCS
        return PCS
    except Exception:
        return None


def rank_centred(x):
    r = rankdata(x); k = len(r)
    return 2.0 * (r - 1) / (k - 1) - 1.0 if k > 1 else np.zeros_like(x)


def measure_gaps(panel, stride=4):
    """THE measurement, extracted so there is exactly ONE implementation of it.

    Returns (gaps, missing) where gaps = {channel: {"mean_gap": float, "n": int}} over CHANNELS+["Y4"],
    and missing = channels absent from the panel. `assert_panel_caliber_manifest.py` calls this rather
    than re-deriving the same quantity: three implementations of one rule is how a rule comes to mean
    three slightly different things (same reasoning as the merged episode logic in the live stack).

    ⇒ `stride` samples every k-th member anchor ACROSS THE WHOLE PANEL. Do not replace it with a tail
      window — see the history-spanning note in the header; the 4h/8h cohort mix is not stationary.
    """
    W = np.load(panel, allow_pickle=True)
    ts = W["ts"].astype(np.int64); symbols = [str(s) for s in W["symbols"]]
    ch = [str(c) for c in W["ch_names"]]; CH = W["CH"]; mem = W["MEMBER110"]
    Y4 = W["Y4"].astype(np.float64)
    T, N = mem.shape

    # settlement interval in force, from the raw archive
    IH = np.full((T, N), np.nan)
    for j, s in enumerate(symbols):
        try:
            d = pd.read_csv(f"{WIDE}/{s}_funding.csv").sort_values("fundingTime_ms")
        except FileNotFoundError:
            continue
        iv = pd.to_numeric(d["funding_interval_h"], errors="coerce").to_numpy()
        fts = d["fundingTime_ms"].to_numpy().astype(np.int64)
        ok = np.isfinite(iv) & (iv > 0)
        if ok.sum() < 3:
            continue
        idx = np.searchsorted(fts[ok], ts, side="right") - 1
        g = idx >= 0
        IH[g, j] = iv[ok][idx[g]]

    missing = [c for c in CHANNELS if c not in ch]
    if missing:
        return {}, missing

    acc = {c: [] for c in CHANNELS}; acc["Y4"] = []
    rows = np.where(mem.any(1))[0]
    for t in rows[::stride]:
        v = np.where(mem[t] & np.isfinite(IH[t]))[0]
        if v.size < 20:
            continue
        is4 = IH[t, v] <= 4.0
        if is4.sum() < 3 or (~is4).sum() < 3:
            continue
        for c in CHANNELS + ["Y4"]:
            x = Y4[t, v] if c == "Y4" else CH[t, v, ch.index(c)].astype(np.float64)
            f = np.isfinite(x)
            if (f & is4).sum() < 3 or (f & ~is4).sum() < 3:
                continue
            z = np.full(len(x), np.nan); z[f] = rank_centred(x[f])
            acc[c].append(float(np.nanmean(z[is4]) - np.nanmean(z[~is4])))

    gaps = {}
    for c in CHANNELS + ["Y4"]:
        a = np.array(acc[c], float); a = a[np.isfinite(a)]
        # NO DATA stays absent from the dict rather than becoming 0.0 — a gap of zero is the
        # signature of a PERFECTLY dimensioned factor, i.e. exactly the benign value. Callers must
        # see the absence.
        if a.size:
            gaps[c] = dict(mean_gap=round(float(a.mean()), 4), n=int(a.size))
    return gaps, []


def main(panel, caliber="auto"):
    if caliber and caliber != "auto":
        WANT, BASIS = caliber, "--caliber override (one-off inspection / red test)"
    else:
        stamp = _stamp_mod()
        try:
            WANT, BASIS = declared_caliber(panel, with_basis=True)
        except (stamp.StampError if stamp else Exception) as e:
            print(f"CANNOT JUDGE: {panel} carries a BROKEN caliber stamp — {e} (exit 2).\n"
                  f"  ⇒ A broken declaration is not an absent one. Something wrote a stamp and it "
                  f"cannot be read; find that writer rather than removing the stamp.", flush=True)
            return 2
    if WANT is None:
        print(f"CANNOT JUDGE: {panel} carries no caliber stamp, and its contents "
              f"(sha256_16) are not declared in engine/live/factor_version_registry.py — so there "
              f"is no statement of which caliber it is supposed to carry (exit 2).\n"
              f"  ⇒ Stamp it AT THE BUILDER (exports/eda/panel_caliber_stamp.py::make, splatted "
              f"into np.savez), so the declaration travels inside the artifact and survives a "
              f"rename. Do NOT teach this gate a path or filename rule: a path key is inherited by "
              f"whatever file is written there next, which is the 2026-07-25 defect with a "
              f"different mechanism.\n"
              f"  ⇒ For an artifact that must not be rewritten (the frozen training panel), declare "
              f"its sha256_16 in factor_version_registry.UNSTAMPED_ARTIFACT_CALIBER.\n"
              f"  ⇒ Or pass --caliber explicitly for a one-off inspection.", flush=True)
        return 2
    print(f"[caliber] this artifact must be **{WANT}**  (basis: {BASIS})", flush=True)
    # ★ EXIT 2 = "CANNOT JUDGE", DISTINCT FROM EXIT 1 = "JUDGED, WRONG CALIBER" (0C 2026-07-27).
    # Both used to be 1. They are different states and callers need to tell them apart: a panel
    # missing the funding channels, or with no anchor where both settlement cohorts are populated,
    # gives this gate NOTHING TO MEASURE — reporting that as a caliber violation names a defect that
    # was never observed. Production still refuses either way (a malformed panel is not fit for use);
    # what changes is that a caller can say WHICH.
    res, missing = measure_gaps(panel)
    if missing:
        print(f"CANNOT JUDGE: channels not present in panel: {missing} (exit 2, not a caliber "
              f"verdict — nothing was measured)", flush=True)
        return 2

    print(f"panel: {panel}\nanchors sampled: {res.get('Y4', {}).get('n', 0)}\n", flush=True)
    if not any(c in res for c in CHANNELS):
        print("CANNOT JUDGE: no anchor had both a 4h and an 8h cohort populated — nothing was "
              "measured (exit 2, not a caliber verdict)", flush=True)
        return 2
    failed = []
    for c in CHANNELS + ["Y4"]:
        if c not in res:
            print(f"  {c:14s}  NO DATA -> FAIL"); failed.append(c); continue
        mg = res[c]["mean_gap"]
        if c == "Y4":
            print(f"  {c:14s}  mean gap {mg:+.4f}   (CONTROL: real 4h-cohort return gap, "
                  f"a small factor gap of this order is legitimate)", flush=True)
        else:
            got = classify_gap(mg)
            ok = (got == WANT)
            print(f"  {c:14s}  mean gap {mg:+.4f}   -> {got:10s} {'PASS' if ok else 'FAIL'} "
                  f"(this artifact must be {WANT}; bands ±{FAIL_ABS} around "
                  f"as_trained {REF_AS_TRAINED:+.4f} / corrected {REF_CORRECTED:+.4f}; "
                  f"the middle is forbidden)", flush=True)
            res[c]["caliber"] = got
            if not ok:
                failed.append(c)

    verdict = "PASS" if not failed else f"FAIL: {failed}"
    print(f"\nVERDICT: {verdict}", flush=True)
    if failed:
        got = {c: res[c].get("caliber") for c in CHANNELS if c in res}
        if WANT == "corrected":
            print("\n  This artifact must carry the CORRECTED caliber and does not. Fix: normalise each\n"
                  "  settlement rate to an 8h equivalent BEFORE the EMA: rate * (8 / interval_h_of_that_row).\n"
                  "  Applying it after the EMA is wrong for the ~29 coins that migrated 8h<->4h mid-history.\n"
                  "  Reference implementation: exports/eda/funding_dim_fix.py", flush=True)
        else:
            print("\n  ★ This artifact must carry the AS-TRAINED (un-normalised) caliber and does not.\n"
                  "  DO NOT 'fix' it by normalising: the frozen king/s2 heads were fitted on the\n"
                  "  un-normalised panel (exports/wide_dl_full.npz, built 2026-07-11, never rebuilt).\n"
                  "  Normalising here changes the MODEL'S INPUT DISTRIBUTION with no retraining, and\n"
                  "  this gate would then go green for it. Find who normalised it instead.", flush=True)
        if "MIDDLE" in got.values():
            print("\n  ★★ A reading landed in the FORBIDDEN MIDDLE (near neither reference). That means the\n"
                  "  funding dimension was changed without declaring which caliber was intended —\n"
                  "  neither the as-trained nor the corrected recipe produces this. Do not adjust the\n"
                  "  threshold; find the change.", flush=True)
    json.dump(dict(panel=panel, created="2026-07-25", auditor="0C", fail_threshold=FAIL_ABS,
                   expected_caliber=WANT, expectation_basis=BASIS, ref_as_trained=REF_AS_TRAINED,
                   ref_corrected=REF_CORRECTED, channels=res, verdict=verdict),
              open(EDA + "assert_funding_dim_result.json", "w"), indent=1, default=str)
    return 0 if not failed else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=MA + "/exports/wide_dl_full.npz")
    ap.add_argument("--caliber", default="auto", choices=["auto", "corrected", "as_trained"],
                    help="override the per-artifact expectation (auto = read the artifact's own "
                         "caliber stamp, then its sha256 declaration; never its path)")
    _a = ap.parse_args()
    sys.exit(main(_a.panel, _a.caliber))
