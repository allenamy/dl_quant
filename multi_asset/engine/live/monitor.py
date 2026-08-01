"""Live shadow — item 4: C4 monitoring daily report.

Rolling cross-sectional rank-IC of the emitted positions vs the realized 4h return (backfilled as
anchors mature), a decay alarm vs the historical baseline, and a daily-report json. Wraps the engine
C4 (engine/ic_monitor.py). Outputs exports/live/monitor/daily_report.json (+ ic_history*.csv).

★ TWO CORRECTIONS, 2026-07-25, BOTH LANDED BEFORE THE DRY-RUN CLOCK STARTS (protocol §2.5.5)

(1) UNIVERSE (S1). This module used to hand `w = np.zeros(src.N)` to `xsec_rank_ic`, whose universe
    is `isfinite(pos) & isfinite(realized)`. **Zero is finite**, so ~27 non-member names entered
    every cross-sectional correlation, tied at one rank — while the comparison baseline is computed
    by the engine over the *tradeable* set only. A diluted reading was being compared against an
    undiluted benchmark: measured 9–16% dilution, last-60 rolling 0.0344 here vs 0.0430 in engine
    caliber, i.e. 11% above the decay threshold instead of 39%. That gap produced spurious alerts.

    The fix is not "mask it at the call site" — it is to stop representing absence as a number.
    A name that is not in the book is **NaN (absent)**, never weight 0. A zero survives every
    finiteness filter and silently joins the universe; that is the same landmine the factory hit on
    2026-07-20, one layer up. We then ALSO index to `src.tradeable(t)` explicitly, so a future caller
    cannot re-introduce it by handing us a zero-filled vector.

    ★ The identical zero-fill is CORRECT elsewhere in this codebase (engine/replay_fullhist.py builds
    a full-N zero vector for TURNOVER — a name leaving the book must count as turnover). A zero
    weight contributes exactly zero to a dot product but becomes one more member of a large tied
    block in a rank correlation. "We zero-fill non-members" is not a property you can judge without
    naming the consuming operation.

(2) CURVE. This module scored ONLY `A_provisional_3leg` — a curve that drops the funding leg, i.e.
    not the book we intend to trade. Decay on the deployable caliber was therefore UNMONITORED, and
    the downstream consumer (dl_quant_live/ops/check_factor_health.py) correctly refused to forward
    a verdict from it. We now publish THREE series, each with its own rolling value, threshold and
    alert history, so no consumer has to guess which one it is reading:

        deployable_4leg   DECISION         fixfunding track, corrected funding, 4 legs
        as_trained_4leg   CONTROL          champion curve B, pre-fix funding, 4 legs
        provisional_3leg  CONTINUITY_ONLY  champion curve A — the only unbroken series since launch

    The control exists to answer one question and only one: when the decision series moves, is that
    the FACTOR or the CALIBER? The two arms differ in nothing else.

★ `decay_alarm` is CUMULATIVE (`bool(mon.alerts)` = "has ever alerted") and is kept only for
  compatibility. `below_threshold_now` is the current state. A consumer that reads the cumulative
  flag as a present-tense fact will report decay forever after one dip.
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

# ★ MA MUST be defined before its first use. The portability refactor (ef2ddbb) left
# `sys.path.insert(0, MA)` ABOVE this line, so this module raised NameError at import AND as a
# script — measured `rc=1`. It was invisible because nothing in the acceptance suites executes this
# module's top level, and run_daily.sh's `run()` aborts the whole chain on a step failure.
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset

sys.path.insert(0, MA)
sys.path.insert(0, os.path.join(MA, "engine", "live"))
from engine.ic_monitor import ICMonitor, xsec_rank_ic   # noqa: E402

POS_DIR = MA + "/exports/live/positions"
FIX_POS_DIR = MA + "/exports/live/fixfunding/positions"
OUT = MA + "/exports/live/monitor"
PANEL = MA + "/exports/live/wide_dl_live.npz"
FROZEN_PANEL = MA + "/exports/wide_dl_full.npz"          # the panel the baseline is measured on
REPLAY_ARTIFACT = MA + "/exports/eda/engine_fullhist_replay.json"   # where BASELINE_BY_YEAR comes from
# REGIME-AWARE baseline: use the CURRENT-regime engine rank-IC, not the full-history average (0.076).
# 2026 is a weaker regime (~0.062), so a live rolling IC near 0.059 is 2026-NORMAL, not degraded —
# comparing it to the 0.076 full-history level would read a healthy signal as decaying. Keyed by year;
# update as new regimes are entered (values = engine canonical per-year rank-IC, computed by
# engine/replay_fullhist.py over the TRADEABLE set — which is why this module must score the same
# universe; see correction (1) above).
BASELINE_BY_YEAR = {2022: 0.062, 2023: 0.086, 2024: 0.081, 2025: 0.076, 2026: 0.062}
WINDOW = 60                # rolling anchors (NOTE: 60 *scored* anchors, not 60 calendar anchors —
                           # skipped anchors silently lengthen the wall-clock span of the window)
DECAY_FRAC = 0.5           # alarm if rolling IC < DECAY_FRAC * baseline

# key -> (role, track, positions dir, extractor). `track` keys into factor_version_registry, which
# is the single source of truth for which factor version each track is SUPPOSED to run.
SERIES_SPEC = [
    ("deployable_4leg",  "DECISION",        "champion_fixfunding", FIX_POS_DIR,
     lambda rec: rec["positions"]),
    ("as_trained_4leg",  "CONTROL",         "champion",            POS_DIR,
     lambda rec: rec["curve"]["B_backfilled_4leg"]["positions"]),
    ("provisional_3leg", "CONTINUITY_ONLY", "champion",            POS_DIR,
     lambda rec: rec["curve"]["A_provisional_3leg"]["positions"]),
]
DECISION_KEY = "deployable_4leg"
# the caliber label the downstream consumer keys on (dl_quant_live/ops/check_factor_health.py)
DECISION_CALIBER = "champion_fixfunding"


def _src():
    from engine.panel_source import PanelSource
    return PanelSource(panel=PANEL,
                       king=MA + "/exports/live/king_pred_live.npz",
                       s2=MA + "/exports/live/s2_pred_live.npz")


def _baseline_provenance(year: int, declared: float):
    """Trace BASELINE_BY_YEAR back to the artifact that produced it, and check two things the
    baseline's validity actually depends on.

    ★ (a) IS IT A MEASUREMENT? The comment wrote 2026 as "~0.062" while 2022-2025 were exact, which
    reads like an estimate. It is not: `exports/eda/engine_fullhist_replay.json` (the canonical
    replay behind avg_net 12.21) gives per-year mean_rank_ic 0.0616/0.0859/0.0805/0.0764/0.0622 for
    2022..2026 — every coded constant is that number rounded, 2026 included. The collision with 2022
    is real, not a placeholder. We assert it here rather than trusting the comment, because "the
    comment says it was measured" is exactly the class of claim this project keeps finding false.

    ★ (b) IS THE BASELINE DISJOINT FROM WHAT IT JUDGES? If the baseline were computed over a window
    that INCLUDES the decline being tested, the test would be comparing a decline against a
    benchmark already depressed by it — too lenient by construction. Today it is disjoint: the
    frozen panel ends 2026-06-30 and shadow scoring starts 2026-07-01. But that holds by accident of
    a file's end date, so it is asserted here: an overlap must degrade the verdict to UNKNOWN rather
    than quietly weaken it.
    """
    prov = {"declared": declared, "year": year,
            "source": os.path.relpath(REPLAY_ARTIFACT, MA), "is_measurement": None}
    try:
        rep = json.load(open(REPLAY_ARTIFACT))
        py = rep.get("per_year", {}).get(str(year)) or rep.get("per_year", {}).get(year)
        measured = None if py is None else py.get("mean_rank_ic")
        prov.update(measured=measured, trading_days=None if py is None else py.get("trading_days"),
                    replay_config=rep.get("config"))
        if measured is not None:
            prov["is_measurement"] = True
            prov["matches_declared"] = bool(abs(round(float(measured), 3) - declared) < 5e-4)
            if not prov["matches_declared"]:
                prov["WARNING"] = (f"declared {declared} != round(measured {measured}, 3) — the "
                                   f"constant no longer matches the artifact it came from")
        else:
            prov["is_measurement"] = False
            prov["WARNING"] = f"no per_year entry for {year} in the replay artifact"
    except Exception as e:
        prov["is_measurement"] = False
        prov["WARNING"] = f"could not read the replay artifact: {type(e).__name__}: {e}"
    return prov


def _baseline_window_disjoint(first_scored_ts_ms):
    """The baseline is computed on the FROZEN panel; scoring runs on anchors after it. Verify."""
    out = {"frozen_panel": os.path.relpath(FROZEN_PANEL, MA)}
    try:
        ts = np.load(FROZEN_PANEL, allow_pickle=True)["ts"].astype(np.int64)
        end = int(ts.max())
        out["baseline_window_end_utc"] = pd.to_datetime(end, unit="ms", utc=True).isoformat()
        if first_scored_ts_ms is None:
            out["disjoint"] = None
            out["note"] = "nothing scored yet — disjointness undetermined, not assumed"
        else:
            out["first_scored_anchor_utc"] = pd.to_datetime(int(first_scored_ts_ms), unit="ms",
                                                            utc=True).isoformat()
            out["disjoint"] = bool(int(first_scored_ts_ms) > end)
            if not out["disjoint"]:
                out["WARNING"] = ("the baseline window OVERLAPS the anchors being judged — the "
                                  "benchmark contains the very decline under test; the decay "
                                  "verdict is UNKNOWN, not lenient-but-usable")
    except Exception as e:
        out["disjoint"] = None
        out["WARNING"] = f"could not read the frozen panel: {type(e).__name__}: {e}"
    return out


def _panel_identity(src):
    """Cheap, audit-usable identity for the panel these readings were produced from. Not a hash
    (the npz is large and this runs daily); size+mtime+last-anchor pins it well enough to answer
    'which panel produced the 07-15 readings' — the question the champion position files currently
    cannot answer at all (S5)."""
    try:
        st = os.stat(PANEL)
        return {"path": os.path.relpath(PANEL, MA), "bytes": st.st_size,
                "mtime_utc": pd.Timestamp(st.st_mtime, unit="s", tz="UTC").isoformat(),
                "n_rows": int(len(src.ts)),
                "last_anchor_utc": pd.to_datetime(int(src.ts[-1]), unit="ms",
                                                  utc=True).isoformat() if len(src.ts) else None}
    except Exception as e:
        return {"path": PANEL, "error": f"{type(e).__name__}: {e}"}


def _score_series(src, tj, sym2j, pos_dir, extract, baseline_ic):
    """One position series -> rolling rank-IC over the TRADEABLE universe.

    Absence is NaN, never 0. `n_missing_in_book` counts tradeable names the book did not price at
    all: those are dropped from the correlation (correctly — we have no opinion on them), but the
    count is published, because an absence that silently shrinks the universe is exactly the kind of
    thing that must be visible rather than folded away.
    """
    mon = ICMonitor(window=WINDOW, baseline_ic=baseline_ic, decay_frac=DECAY_FRAC)
    hist, n_missing_total, n_scored_names, scored_ts = [], 0, [], []
    for f in sorted(glob.glob(pos_dir + "/positions_*.json")):
        rec = json.load(open(f))
        ti = tj.get(int(rec["anchor_ts_ms"]))
        if ti is None:
            continue
        ret = src.Y4[ti]
        if not np.isfinite(ret).any():        # label not matured yet -> backfill on a later run
            continue
        try:
            pos = extract(rec)
        except (KeyError, TypeError):
            continue                          # this series is not present in this file
        # ★ NaN = absent. A non-member must not be representable as a weight.
        w = np.full(src.N, np.nan)
        for s, wt in pos.items():
            j = sym2j.get(s)
            if j is not None:
                w[j] = wt
        m = src.tradeable(ti)                 # the engine's universe — the one the baseline uses
        n_missing_total += int(np.sum(~np.isfinite(w[m])))
        n_scored_names.append(int(np.sum(np.isfinite(w[m]) & np.isfinite(ret[m]))))
        r = mon.update(rec["anchor_ts_ms"], w[m], ret[m])
        if r["ic"] is not None and np.isfinite(r["ic"]):
            scored_ts.append(int(rec["anchor_ts_ms"]))
        hist.append({"anchor_utc": rec["anchor_utc"], "ic": r["ic"], "rolling_ic": r["rolling_ic"],
                     "n": r["n"], "alert": r["alert"]})
    scored = [h for h in hist if h["ic"] is not None and np.isfinite(h["ic"])]
    roll = mon.rolling_ic() if scored else float("nan")
    thr = DECAY_FRAC * baseline_ic
    return {
        "n_anchors_scored": len(scored),
        "rolling_rank_ic": round(float(roll), 4) if scored else None,
        "below_threshold_now": bool(scored and np.isfinite(roll) and roll < thr),
        "window_full": bool(hist and hist[-1]["n"] >= WINDOW),
        "n_alerts": len(mon.alerts),
        "first_alert": mon.alerts[0] if mon.alerts else None,
        "latest_alert": mon.alerts[-1] if mon.alerts else None,
        "decay_alarm_cumulative": bool(mon.alerts),
        "mean_names_per_anchor": round(float(np.mean(n_scored_names)), 1) if n_scored_names else None,
        "n_tradeable_names_missing_from_book": n_missing_total,
        "first_scored_anchor_ts_ms": min(scored_ts) if scored_ts else None,
        "last_scored_anchor_ts_ms": max(scored_ts) if scored_ts else None,
    }, hist


def run(verbose=True):
    os.makedirs(OUT, exist_ok=True)
    src = _src()
    tj = {int(t): i for i, t in enumerate(src.ts)}
    sym2j = {s: j for j, s in enumerate(src.symbols)}
    # regime-aware baseline: the year of the most recent scored anchor
    files_all = sorted(glob.glob(POS_DIR + "/positions_*.json"))
    cur_year = pd.Timestamp.utcnow().year
    if files_all:
        cur_year = pd.to_datetime(json.load(open(files_all[-1]))["anchor_ts_ms"],
                                  unit="ms", utc=True).year
    baseline_ic = BASELINE_BY_YEAR.get(int(cur_year), 0.062)

    try:
        import factor_version_registry as FVR
    except Exception:
        FVR = None

    series, outputs = {}, {}
    for key, role, track, pos_dir, extract in SERIES_SPEC:
        stats, hist = _score_series(src, tj, sym2j, pos_dir, extract, baseline_ic)
        stats["role"] = role
        stats["track"] = track
        stats["factor_version"] = FVR.expected_for(track) if FVR else None
        stats["positions_dir"] = os.path.relpath(pos_dir, MA)
        if role == "CONTINUITY_ONLY":
            stats["note"] = ("drops the funding leg — NOT the book we trade. Kept because it is the "
                             "only unbroken series since launch. Never a decision input.")
        if hist:
            p = OUT + f"/ic_history_{key}.csv"
            pd.DataFrame(hist).to_csv(p, index=False)
            outputs[key] = os.path.relpath(p, MA)
            if key == DECISION_KEY:            # keep the historical filename pointing at the decision
                pd.DataFrame(hist).to_csv(OUT + "/ic_history.csv", index=False)
        series[key] = stats

    dec = series.get(DECISION_KEY, {})

    # ── baseline traceability + the disjointness the decay test depends on ────────────────────
    base_prov = _baseline_provenance(int(cur_year), baseline_ic)
    disjoint = _baseline_window_disjoint(dec.get("first_scored_anchor_ts_ms"))
    # A verdict is only publishable when the benchmark is a real measurement AND it does not
    # overlap the anchors it judges. Either failure yields UNKNOWN — never a softer verdict.
    verdict_usable = bool(base_prov.get("is_measurement") and base_prov.get("matches_declared")
                          and disjoint.get("disjoint") is True)

    # ── S3: did the thing we score actually advance since the previous run? ───────────────────
    try:
        import frontier as FR
        # read back from the decision series' own artefacts — never from our in-memory tally
        fr = FR.report("monitor.decision_series", FR.anchors_from_json_dir(FIX_POS_DIR))
    except Exception as e:
        fr = {"error": f"{type(e).__name__}: {e}"}

    # ★★★ THE MIXTURE THE DECISION SERIES WAS BUILT AT (2026-08-01).
    # `caliber` names the CURVE (which legs, which universe) and says nothing about the WEIGHTS.
    # The pilot's deployed book moved to the challenger mixture today while this series stays at
    # champion .30/.10/.30/.30 by design — so from now on the consumer must be able to see that a
    # decay verdict here is about the FACTORS at the old mixture, not about the traded book. It
    # could not: nothing in this report named a weight. Second occurrence of the shape whose first
    # was a decay alarm reading `A_provisional_3leg`, a curve with no funding leg.
    # ★ READ BACK FROM THE ARTEFACT, not from a constant in this file: the positions we scored are
    #   the thing that has a mixture, and a local copy could disagree with them. Absent or
    #   unreadable stays UNKNOWN — never "the same".
    _decision_weights = None
    try:
        _pf = sorted(glob.glob(os.path.join(FIX_POS_DIR, "positions_*.json")))
        if _pf:
            _decision_weights = (json.load(open(_pf[-1])) or {}).get("weights")
    except Exception as _e:
        _decision_weights = f"UNREAD ({type(_e).__name__}: {str(_e)[:60]})"

    report = {
        "as_of": pd.Timestamp.utcnow().isoformat(),
        "decision_weights": _decision_weights,
        "decision_weights_source": (f"read back from the newest artefact in {FIX_POS_DIR}; "
                                    f"null means the artefact names no mixture, which is UNKNOWN "
                                    f"and not 'the same as deployed'"),
        # ---- top-level = THE DECISION SERIES (consumers that read these get the deployable book) --
        "caliber": DECISION_CALIBER,
        "decision_series": DECISION_KEY,
        "rolling_rank_ic": dec.get("rolling_rank_ic"),
        "n_anchors_scored": dec.get("n_anchors_scored"),
        "below_threshold_now": dec.get("below_threshold_now"),
        "decay_alarm": dec.get("decay_alarm_cumulative"),     # CUMULATIVE — compat only, see note
        "n_alerts": dec.get("n_alerts"),
        "latest_alert": dec.get("latest_alert"),
        "baseline_ic": baseline_ic, "baseline_regime_year": int(cur_year),
        "decay_alarm_threshold": round(DECAY_FRAC * baseline_ic, 4),
        "baseline_provenance": base_prov,
        "baseline_window": disjoint,
        "verdict_usable": verdict_usable,
        "frontier": fr,
        # ---- the full picture -------------------------------------------------------------------
        "series": series,
        "universe": ("tradeable(t) = member110 & finite(king) & finite(s2) — the SAME universe the "
                     "engine baseline is computed over. Non-members are NaN (absent), never weight "
                     "0: a zero passes every finiteness filter and silently joins the cross-section."),
        "provenance": {"panel": _panel_identity(src),
                       "monitor_window_anchors": WINDOW, "decay_frac": DECAY_FRAC,
                       "factor_version_source": "engine/live/factor_version_registry.py"},
        "outputs": outputs,
        "note": ("rolling rank-IC of live positions vs realized 4h return; backfilled as labels "
                 "mature. Structural-caliber signal-health monitor (not a P&L). Baseline is "
                 "REGIME-AWARE (current-year engine level), so a reading near the current regime's "
                 "IC is healthy, not decayed. ★ `decay_alarm` is CUMULATIVE ('has ever alerted'); "
                 "read `below_threshold_now` for the present state. ★ Judge decay ONLY on "
                 f"`{DECISION_KEY}`; `as_trained_4leg` is the control that separates FACTOR from "
                 "CALIBER; `provisional_3leg` is continuity only and drops the funding leg."),
    }
    json.dump(report, open(OUT + "/daily_report.json", "w"), indent=1)
    if verbose:
        for k, v in series.items():
            print(f"[monitor] {k:17s} {v['role']:16s} n={v['n_anchors_scored']:4d} "
                  f"rolling={v['rolling_rank_ic']} below_thr_now={v['below_threshold_now']} "
                  f"alerts={v['n_alerts']}", flush=True)
        print(f"[monitor] decision={DECISION_KEY} caliber={DECISION_CALIBER} "
              f"baseline={baseline_ic} (regime-{cur_year}) threshold={report['decay_alarm_threshold']}",
              flush=True)
        print(f"[monitor] baseline: measured={base_prov.get('is_measurement')} "
              f"matches_declared={base_prov.get('matches_declared')} "
              f"(replay {base_prov.get('measured')} over {base_prov.get('trading_days')} trading days) "
              f"| window_disjoint={disjoint.get('disjoint')} "
              f"(baseline ends {str(disjoint.get('baseline_window_end_utc'))[:10]}, "
              f"scoring starts {str(disjoint.get('first_scored_anchor_utc'))[:10]}) "
              f"| verdict_usable={verdict_usable}", flush=True)
        for w in (base_prov.get("WARNING"), disjoint.get("WARNING")):
            if w:
                print(f"[monitor] ★ {w}", flush=True)
        print(f"[monitor] -> {OUT}/daily_report.json + ic_history*.csv", flush=True)
    return report


if __name__ == "__main__":
    run()
