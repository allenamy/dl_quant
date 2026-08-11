"""fapi -> panel -> king/s2 -> the preds file the anchor loop already consumes.

★ WHY THIS WRITES A FILE INSTEAD OF RETURNING A DICT INTO `_trade`
  The staleness ladder is built on ONE question: how old is the newest usable prediction. If the
  computation were inlined into `_trade`, a failed computation would have to be turned into a
  "pretend it's stale" branch by hand -- a second code path expressing the same idea, which is how
  the two drift apart. By producing the same artefact the server shadow produced, a failure needs
  no branch at all: nothing is written, the previous file keeps its old `computed_ts`, and the
  ladder does what it already does (HOLD -> DERISK -> FLATTEN).

★ AND THAT IS WHY A BLOCKED BUILD MUST NOT WRITE ANYTHING.
  The tempting failure is to write preds with a fresh `computed_ts` and some fallback content --
  which converts "we have no signal" into "we have a signal, and it is wrong", the one outcome the
  ladder cannot protect against. Warmup BLOCK, caliber BLOCK, missing funding: all return without
  touching the file. Refusing to emit is a valid, and here the only correct, answer.

★ SPLIT-PATH, ONE MORE TIME, BECAUSE THIS IS WHERE BOTH CALIBERS MEET IN ONE PROCESS
      king/s2   <- AS-TRAINED panel   (the settlement-interval bug REPRODUCED on purpose)
      funding leg <- NORMFIX series   (rate x 8/interval_h per row, before the EMA)
  Both are built here, from the same settlements, seconds apart. The stamp written into the file
  is asserted against config by the consumer, so the guarantee is a mechanism and not a habit.

★ THE COLUMN SET IS PART OF THE MODEL. The encoder attends across columns, so changing the 140
  columns changes every prediction. The file therefore carries `n_columns` + a hash of the exact
  ordered column list, and the consumer refuses preds whose column set it cannot recognise.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, Optional

import numpy as np

import funding_panel as FP
import inference as INF
import live_panel as LP
import panel_build as PB

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
PREDS_PATH = os.environ.get("LIVE_PREDS_PATH", os.path.join(_REPO, "state", "preds_latest.json"))


def columns_fingerprint(symbols) -> Dict[str, Any]:
    """The identity of the cross-section, in a form a consumer can check in one comparison."""
    joined = "\n".join(str(s) for s in symbols)
    return {"n_columns": len(symbols),
            "columns_sha256": hashlib.sha256(joined.encode()).hexdigest()}


def btc_rvol_bps_min(CLOSE, symbols, anchor: int, lookback_h: int = 24):
    """BTC realised vol in bps/min from the panel's own hourly closes — the regime classifier's
    documented input, computed causally (std of trailing 1h returns / sqrt(60)).

    ★ WHY IT LIVES HERE. `regime_at_anchor` is stamped on every anchors row, and the whole point
    of that column is that the label was fixed BEFORE the markout it will later be used to filter.
    Computing it at signal time, from the same panel the prediction came from, is what makes that
    true; computing it later — at analysis time, from whatever data is around — is exactly the
    rationalisation the classifier exists to prevent ("that day was stress").
    Returns None when BTC is absent or the window is short: `unknown` is a legitimate label and a
    guessed number is not.
    """
    try:
        j = [i for i, s in enumerate(symbols) if str(s) == "BTCUSDT"]
        if not j or CLOSE is None:
            return None
        col = np.asarray(CLOSE, float)[max(0, anchor - lookback_h): anchor + 1, j[0]]
        col = col[np.isfinite(col) & (col > 0)]
        if col.size < 8:
            return None
        r = np.diff(np.log(col))
        return float(np.std(r, ddof=1) * 1e4 / np.sqrt(60.0))
    except Exception:
        return None


def _save_atomic(path: str, obj: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, default=str)
    os.replace(tmp, path)          # atomic: a crash never leaves a half-written prediction


def compute(source, hours: Optional[int] = None, refresh: bool = True,
            progress=None) -> Dict[str, Any]:
    """Build the panel, run both models, assemble the preds payload. Raises rather than degrading.

    Returns the payload; the caller decides whether to persist it (see `refresh_preds`).
    """
    t0 = time.time()
    built = LP.build_live_panel(source, hours=hours, refresh=refresh, progress=progress)
    CH, ts, syms = built["CH"], built["ts"], built["symbols"]
    anchor = len(ts) - 1

    # ── [GAP-OBS] how many bars did each name actually print? ─────────────────────────────────
    # ★ COUNTED FROM `CLOSE`, NOT FROM `CH`. By the time this function holds `CH`, the wash has
    #   already happened one layer up in `panel_build.build_channels`
    #   (`np.nan_to_num(CH, nan=0.0, ...)`), so every gap there is an ordinary-looking 0.0 — and
    #   0.0 is a value a real bar can have. `CLOSE` still carries NaN, upstream of every wash,
    #   and NaN there means exactly "no bar".
    # ★★ WHAT A GAP CURRENTLY BECOMES, and why this is only an OBSERVATION. `normalise` runs
    #   nan_to_num BEFORE standardising, so a missing bar arrives at the model as
    #   z = (0 - mu)/sd. Measured against the frozen norm_stats: median |z| = 0.04 (harmless on
    #   most channels), but 12 of 32 channels exceed |z| = 1 and ONE ratio-type channel
    #   (mu≈0.999, sd≈0.049) saturates the clip at -10 — on that channel a halted name presents
    #   as the strongest reading the model can represent.
    # ★★★ AND IT IS NOT A BUG WE MAY FIX HERE. The training panel washes gaps identically
    #   (build_wide_dl.py) and the trainer standardises in the same order with the same clip
    #   (wide_panel_dataset.py:97), so the frozen heads were FITTED on this convention. Masking
    #   or dropping gapped names at inference time would introduce a train/serve inconsistency
    #   that does not exist today. ⇒ Recorded in the model-generation caliber ledger; the
    #   behavioural fix belongs to the next retrain, applied to BOTH sides at once.
    #   This block makes the event visible. It changes nothing the model sees.
    _gap = {}
    try:
        _C = built.get("CLOSE")
        if _C is not None:
            _w0 = max(0, anchor - INF.W + 1)
            _win_close = np.asarray(_C)[_w0: anchor + 1]        # (W, N), the rows `window` uses
            _miss = (~np.isfinite(_win_close)).sum(axis=0)
            # "fresh" = inside the most recent 24 hourly bars: a halt still shaping the newest
            #   input, as opposed to one aging out of the window. The system had no notion of
            #   this distinction before — a missing bar scored identically wherever it sat.
            _fresh = (~np.isfinite(_win_close[-24:])).sum(axis=0)
            _gap = {"window_bars": int(_win_close.shape[0]),
                    "n_missing_bars": {str(sy): int(n) for sy, n in zip(syms, _miss) if n},
                    "n_missing_bars_fresh_24h": {str(sy): int(n)
                                                 for sy, n in zip(syms, _fresh) if n},
                    "caliber": ("counted on CLOSE (pre-wash, NaN = no bar); CH is already "
                                "nan_to_num'd by panel_build and cannot be counted on"),
                    "does_not_establish": ("that a gapped name was EXCLUDED — it was not. The "
                                           "name keeps its weight; this records only that its "
                                           "inputs were fabricated for n bars.")}
    except Exception as _e:            # an observation must never cost a prediction
        _gap = {"error": f"{type(_e).__name__}: {_e}"}

    # membership: row-wise top-110 by trailing dollar volume, evaluated AT THE ANCHOR. The mask is
    # only ever consumed at the anchor row (the model takes a (N,) mask per anchor), so this is the
    # traded roster, not a panel-wide approximation.
    QV = np.asarray(built.get("QVOL") if "QVOL" in built else np.nan)
    DV = built.get("DVOL30")
    if DV is None:
        raise RuntimeError("panel build did not return DVOL30")
    # ★ eligibility must mean TRADABLE, not merely "we have data". exchangeInfo is public and the
    # anchor path fetches it anyway; a SETTLING name keeps emitting klines for weeks.
    tradable = None
    try:
        tradable = set(source.perp_symbols())
    except Exception as e:
        # fail LOUD but not closed: without the venue list we fall back to data-only eligibility,
        # and the caller is told, because silently reverting to the weaker criterion is how this
        # class of bug persists.
        print(f"[compute_preds] venue TRADING list unavailable ({e}); "
              f"falling back to data-only eligibility", flush=True)
    member = PB.derive_member(DV, built["CLOSE"], symbols=syms, tradable=tradable)
    if tradable is not None:
        not_trading = [str(syms[j]) for j in range(len(syms))
                       if member[anchor, j] and str(syms[j]) not in tradable]
        if not_trading:
            raise RuntimeError(f"members not TRADING on the venue: {not_trading[:8]}")
    mask = member[anchor].astype(np.float32)
    if mask.sum() < 20:
        raise RuntimeError(f"only {int(mask.sum())} members at the anchor; refusing to trade a "
                           f"cross-section this thin")

    if progress:
        progress("panel built; loading frozen models")
    models, manifest = INF.load()
    window = CH[anchor - INF.W + 1: anchor + 1].transpose(1, 0, 2)
    scores, head_diag = {}, {}
    for name in ("king", "s2"):
        comp, base, _diag = models[name].composite(window, mask)
        head_diag[name] = _diag
        if comp is None:
            raise RuntimeError(f"{name} produced no usable factor heads at this anchor")
        scores[name] = {str(syms[j]): float(v) for j, v in zip(base, comp)}

    # ── funding LEG: the CORRECTED caliber, rebuilt from the same settlements ────────────────
    fc = LP.FundingCache(symbols=syms)
    rows = fc.as_rows(until_ms=int(ts[-1]))
    FUND_FIX, IH, fprov = FP.build_funding_grid(ts, syms, rows, FP.CALIBER_NORMFIX)
    blind = [s for j, s in enumerate(syms) if mask[j] and not np.isfinite(FUND_FIX[anchor, j])]
    if blind:
        raise RuntimeError(f"{len(blind)} member(s) have no corrected funding value at the anchor: "
                           f"{blind[:8]}")

    member_syms = [str(syms[j]) for j in range(len(syms)) if mask[j]]

    # ── [GAP-OBS] split the gaps by MEMBERSHIP, because the two cases mean opposite things ──────
    # ★★★ THE COUNT IS THE SAME AND THE MEANING IS INVERTED. "a name has fresh missing bars" is:
    #   · a MEMBER  -> it is being scored and weighted on inputs that were fabricated for those
    #                  bars, and on one ratio-type channel a fabricated bar reads as the strongest
    #                  signal the model can represent. Dangerous.
    #   · a NON-MEMBER -> a dead ticker that membership already excluded. It holds nothing, it is
    #                  scored by nobody, and its absence of bars is the correct state. Harmless.
    # Measured 2026-07-31: all three fresh-gap names (EOSUSDT/MATICUSDT/RNDRUSDT) were
    # NON-members, each missing 24 of 24 bars — delisted tickers still present as panel columns.
    # The alert nonetheless told the reader "they still hold weight". **It was stating a fact that
    # was not true**, about names the system had already handled correctly.
    # ⇒ Same number, opposite meaning: the classification has to happen HERE, where membership is
    #   known, not in the alarm, which would have to re-derive it and could disagree.
    try:
        _mem = set(member_syms)
        _fresh_all = dict(_gap.get("n_missing_bars_fresh_24h") or {})
        _gap["fresh_members"] = {k: v for k, v in _fresh_all.items() if k in _mem}
        _gap["fresh_non_members"] = {k: v for k, v in _fresh_all.items() if k not in _mem}
        _gap["membership_caliber"] = (
            "fresh_members = scored AND weighted on fabricated inputs (act); "
            "fresh_non_members = excluded by member derivation, holds nothing (record only)")
    except Exception as _e:
        _gap["membership_split_error"] = f"{type(_e).__name__}: {_e}"
    cfg = json.load(open(os.path.join(_REPO, "config", "book.json")))

    # ── regime, stamped at signal time ──────────────────────────────────────────────────────
    # ★ The THRESHOLDS come from live/regime_classifier.py, not from a copy here: they are
    # pre-registered (calm <7, stress >=18 bps/min, reused from makerfill_deepdive and
    # deliberately not re-tuned), and a second copy is how a pre-registered constant quietly
    # becomes a tuned one.
    _rvol = btc_rvol_bps_min(built.get("CLOSE"), syms, anchor)
    try:
        import sys as _sys
        _live = os.path.join(_REPO, "live")
        if _live not in _sys.path:
            _sys.path.insert(0, _live)
        import regime_classifier as _RC
        _label = _RC.label(_rvol)
        _thr = {"calm_max": _RC.CALM_MAX, "stress_min": _RC.STRESS_MIN}
    except Exception as e:
        _label, _thr = "unknown", {"error": str(e)[:120]}
    payload = {
        "computed_ts": time.time(),
        "anchor_ts_ms": int(ts[-1]),
        "producer": "local:signal/compute_preds.py",
        "factor_versions": cfg.get("factor_versions"),
        "symbols": member_syms,
        "data_gaps": _gap,
        "king": {s: scores["king"][s] for s in member_syms if s in scores["king"]},
        "s2": {s: scores["s2"][s] for s in member_syms if s in scores["s2"]},
        # ★★★ [S2] THE COLLAPSE DIAGNOSTIC IS PERSISTED. Per-head std was the ONLY quantity in
        # which a dead model is visible, and it was computed and discarded every anchor — so a
        # collapse could only ever be caught by a test that happened to be looking, never by the
        # record. It now travels with the prediction it produced.
        # ⇒ Kept SMALL on purpose (per-head std / rel_std / n_distinct / live, plus the emitted
        #   sigma) — a summary, not the scores themselves, so it costs a few hundred bytes and
        #   cannot become a second copy of the signal.
        "head_health": head_diag,
        "funding_ema": {s: float(FUND_FIX[anchor, syms.index(s)]) for s in member_syms},
        "dvol30": {s: float(DV[anchor, syms.index(s)]) for s in member_syms},
        "panel": {"hours": int(len(ts)), "first_ts_ms": int(ts[0]), "last_ts_ms": int(ts[-1]),
                  **columns_fingerprint(syms),
                  "warmup_floor_h": PB.WARMUP_HARD_FLOOR_H,
                  "caliber_gate": built["provenance"].get("caliber_gate"),
                  "funding_leg_caliber": FP.CALIBER_NORMFIX,
                  "funding_span_derived": fprov["n_span_derived"]},
        "regime": {"label": _label, "btc_rvol_bps_min": _rvol, "thresholds": _thr,
                   "source": "signal-time, panel hourly closes, trailing 24h "
                             "(std of 1h log-returns / sqrt(60)); thresholds from "
                             "live/regime_classifier.py"},
        "models": manifest,
        "elapsed_s": round(time.time() - t0, 1),
    }
    missing = [s for s in member_syms if s not in payload["king"] or s not in payload["s2"]]
    if missing:
        raise RuntimeError(f"{len(missing)} members lack a model score: {missing[:8]}")
    return payload


def refresh_preds(source, path: str = PREDS_PATH, hours: Optional[int] = None,
                  refresh: bool = True, progress=None) -> Dict[str, Any]:
    """Compute and persist. On ANY failure the file is left untouched -- see the module docstring.

    Returns a status dict for the run log. Never raises: the anchor must continue into the
    staleness ladder, which is the mechanism that already handles "no fresh signal".
    """
    try:
        payload = compute(source, hours=hours, refresh=refresh, progress=progress)
    except PB.PanelWarmupError as e:
        return {"ok": False, "reason": "warmup_block", "detail": str(e)[:300],
                "preds_written": False}
    except FP.FundingCaliberError as e:
        return {"ok": False, "reason": "caliber_block", "detail": str(e)[:300],
                "preds_written": False}
    except Exception as e:                      # network, venue, model, anything
        return {"ok": False, "reason": type(e).__name__, "detail": str(e)[:300],
                "preds_written": False}
    _save_atomic(path, payload)
    return {"ok": True, "preds_written": True, "path": path,
            # ★ the gap summary rides the RETURN as well as the file, because the caller alarms on
            #   it and re-reading the file it just wrote would let the two disagree about which
            #   anchor they describe.
            # ★ THE CALLER GETS THE SPLIT, NOT THE RAW SET. Handing it the union would make the
            #   alarm re-derive membership — a second copy of a rule that already has an owner,
            #   and two copies of one rule is how it comes to mean two things.
            "data_gaps_fresh_members": dict(_gap.get("fresh_members") or {}),
            "data_gaps_fresh_non_members": dict(_gap.get("fresh_non_members") or {}),
            "n_data_gaps": len(_gap.get("n_missing_bars") or {}),
            "n_symbols": len(payload["symbols"]),
            "anchor_ts_ms": payload["anchor_ts_ms"],
            "panel_hours": payload["panel"]["hours"],
            "n_columns": payload["panel"]["n_columns"],
            "elapsed_s": payload["elapsed_s"]}


if __name__ == "__main__":
    import fapi_source
    print(json.dumps(refresh_preds(fapi_source.FapiSource()), indent=1, default=str))
