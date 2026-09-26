#!/usr/bin/env python3
"""funding_interval.py — the one settlement-interval resolver for FND-01 / FND-02 / FND-03 (FX-DATA).

The defect family, from FACT_TABLE section FND: every builder in this lineage resolves an interval as
`declared-if-present -> else spacing -> else 8.0`, and "declared" is read from a **per-symbol map**, so one symbol gets one
interval for its whole API segment. `r6_fetch_funding.py` filled that map from a single `/fapi/v1/fundingInfo` read at
2026-09-11 and `r6_panel_splice.py` L82 applied it to every September row, which is FND-01's 547 wrong cells.

This resolver takes a ROW and never a symbol->interval map. That is not a style choice: the map is the defect, and a function
that cannot accept one cannot reproduce it (red test FI-5).

Precedence, frozen:
  1. the archive's own per-settlement column (`iv_zip`)                      -> EXACT
  2. FX-PROD's P9 exact tier, read as the COLUMN `iv_best` being non-null    -> EXACT
  3. spacing, and ONLY where spacing is safe (see below)                     -> EXACT_BY_SPACING
  4. otherwise                                                              -> one of the UNRESOLVED kinds, never a guess

Read by column, never by the source string (FX-PROD's instruction, and checked: of 243,989 rows, `iv_best_source` values
beginning `unresolved` have `iv_best` non-null in 0 cases, and no row with a non-null `iv_best` carries such a source).

LIKELY never satisfies a gate. `iv_likely` is a best guess for a human reading the table -- its supporting rules are 40/41 and
52/62 -- and `gate_interval` refuses it rather than letting it become a label by omission.

Spacing safety: a short->long switch row is exactly where the time difference lies (FIXPROGRAM P9), so spacing may not be used
as truth when the backward and forward gaps disagree. 166 of 243,989 rows are in that state.

UNRESOLVED is three different things and the lead has ruled they must stay distinguishable:
  * `EVIDENCE_NOT_AVAILABLE` -- the zip is unpublished or a pull failed. It carries a retry record and blocks only when an
    affected row actually enters that month's training input.
  * `SOURCES_CONFLICT` -- sources contradict each other. A real refusal; it blocks.
  * `NONSTANDARD_SPACING` -- added on the lead's ruling of 2026-09-25. A non-switch row (back == fwd) whose spacing lands off
    ALLOWED_IV, the real case being a 3-hour gap. Before this, such a row reached `gate_interval` as EXACT_BY_SPACING and the
    ALLOWED_IV check there raised IntervalError, which crashed a whole rebuild over one row. The lead's ruling is "neither
    raise nor guess": name it, count it, report it per year, and let the build continue. The scope is the SPACING tier only --
    a DECLARED value off the grid still refuses in `gate_interval`, which is what test cell FI8 pins (`iv_zip="3.0"` raises).
    Measured basis: the archive's declared column carries only {1.0, 2.0, 4.0, 8.0} over 2,584,596 rows
    (D10_S1_SRC_IDENTITY.json), so an off-grid value can only come from spacing.
"""
EXACT = "EXACT"
EXACT_BY_SPACING = "EXACT_BY_SPACING"
LIKELY = "LIKELY"
EVIDENCE_NOT_AVAILABLE = "UNRESOLVED_EVIDENCE_NOT_AVAILABLE"
SOURCES_CONFLICT = "UNRESOLVED_SOURCES_CONFLICT"
NONSTANDARD_SPACING = "UNRESOLVED_NONSTANDARD_SPACING"
NOT_IN_P9 = "NOT_IN_P9"
GATEABLE = (EXACT, EXACT_BY_SPACING)
ALLOWED_IV = (1.0, 2.0, 4.0, 6.0, 8.0)


class IntervalError(ValueError):
    """an interval question the resolver refuses to answer"""


def _f(v):
    if v is None: return None
    s = str(v).strip()
    if s in ("", "None", "nan"): return None
    try: return float(s)
    except ValueError: return None


def spacing_is_safe(row):
    """False on a short->long switch row: back and forward gaps disagree, which is where the time difference lies (P9)."""
    b, f = _f(row.get("iv_gap_back")), _f(row.get("iv_gap_fwd"))
    if b is None or f is None: return False
    return b == f


def resolve(row, *, allow_spacing):
    """Resolve one settlement row. `allow_spacing` is required: a caller must say whether spacing is acceptable at all."""
    if row is None:
        return {"iv": None, "tier": NOT_IN_P9, "source": None, "spacing_safe": False,
                "note": "no P9 row for this (symbol, settlement time); flagged, never guessed"}
    if not isinstance(allow_spacing, bool):
        raise IntervalError("allow_spacing must be an explicit bool (no default)")
    zip_iv = _f(row.get("iv_zip"))
    if zip_iv is not None:
        return {"iv": zip_iv, "tier": EXACT, "source": "iv_zip", "spacing_safe": spacing_is_safe(row),
                "note": "the archive's own per-settlement column"}
    best = _f(row.get("iv_best"))
    if best is not None:
        return {"iv": best, "tier": EXACT, "source": row.get("iv_best_source") or "iv_best",
                "spacing_safe": spacing_is_safe(row),
                "note": "P9 exact tier, selected on the COLUMN iv_best being non-null, not on the source string"}
    likely = _f(row.get("iv_likely"))
    if likely is not None:
        return {"iv": None, "tier": LIKELY, "source": row.get("iv_likely_support") or "iv_likely",
                "likely_iv": likely, "spacing_safe": spacing_is_safe(row),
                "note": "a best guess for a human reader; it never satisfies a gate and is never promoted to EXACT"}
    if allow_spacing and spacing_is_safe(row):
        sp = _f(row.get("iv_gap_back"))
        if sp is not None and sp not in ALLOWED_IV:
            # lead's ruling 2026-09-25: a non-switch row whose spacing lands off the allowed grid
            # (the real case is a 3-hour gap) is neither guessed nor allowed to crash the build. It
            # becomes a NAMED unresolved subclass, counted and reported like the other two.
            # Scope is the SPACING tier only: a DECLARED value off the grid still refuses in
            # gate_interval, which is what test cell FI8 pins (iv_zip="3.0" must raise).
            return {"iv": None, "tier": NONSTANDARD_SPACING, "source": "spacing",
                    "spacing_value": sp, "spacing_safe": True,
                    "note": "backward and forward gaps agree but the gap is not in the allowed set; "
                            "named unresolved rather than guessed, and the build continues"}
        return {"iv": sp, "tier": EXACT_BY_SPACING, "source": "spacing",
                "spacing_safe": True, "note": "backward and forward gaps agree, so this is not a switch row"}
    src = (row.get("iv_best_source") or "")
    if src.startswith("conflicting"):
        return {"iv": None, "tier": SOURCES_CONFLICT, "source": src, "spacing_safe": spacing_is_safe(row),
                "note": "sources contradict each other; this blocks"}
    return {"iv": None, "tier": EVIDENCE_NOT_AVAILABLE, "source": src or None, "spacing_safe": spacing_is_safe(row),
            "note": "evidence not yet available (unpublished zip or failed pull); blocks only when an affected row enters "
                    "that month's training input, and carries a retry record"}


def gate_interval(res, *, what):
    """The only way to turn a resolution into a number a builder may use. LIKELY and every UNRESOLVED kind are refused."""
    if res["tier"] in GATEABLE:
        iv = res["iv"]
        if iv not in ALLOWED_IV:
            raise IntervalError("%s: resolved interval %r is not in the allowed set %s" % (what, iv, list(ALLOWED_IV)))
        return iv
    raise IntervalError("%s: refusing to use a %s row as an interval (source %r). %s"
                        % (what, res["tier"], res.get("source"), res["note"]))

# ======================================================================================================
# D10 stage 2 truth rule -- lead's DECISION_RULE_D10_stage2_2026-09-26.md (1814d4334) §1, THE SINGLE DEFINITION
# ======================================================================================================
# lead's words: "按实际结算间距记, 用小时的精确值, 不吸附到网格". Rationale, measured: funding accrues over the
# time actually elapsed, while the archive's per-settlement COLUMN is forward-looking on a transition row (it
# carries the NEW regime). The four measured cases are all the moment a name leaves a 1h spike -- DEXE/ACE/PROM
# column 4.0 against a real 2.0h gap, COTI 4.0 against 1.0h -- and that is the population the funding leg
# shorts, so using the column understates RN8 by 2-4x exactly there.
#
# THIS IS DELIBERATELY NOT `resolve()`. Two rules live in this file on purpose and must not be conflated:
#   * `resolve()` / `gate_interval()` serve the FX-DATA FND-01/02/03 rebuild (consumers:
#     docs/fixprogram_2026-09-13/FX_DATA/devices/fx_fnd_hol_rebuild{,_v2}.py). There, off-grid spacing is
#     UNRESOLVED_NONSTANDARD_SPACING -- named, counted, never guessed. That behaviour is UNCHANGED.
#   * `interval_d10()` below is the D10 stage 2 truth rule, where lead has ruled the exact spacing IS the
#     answer, 3h included. So a 3h gap is 3.0 here and UNRESOLVED there, and that is not a contradiction: they
#     answer different questions for different consumers.
# ALLOWED_IV governs the DECLARED/column tiers only. It is not applied to the D10 spacing value, because
# snapping is exactly what lead's ruling removes.
#
# This rule is a MODELLING CONVENTION and differs from the live NC `snap_interval` (which snaps, ties to the
# larger). Per the user ruling, train and live must share one rule, so the producer adopts this one in the
# October rebuild via the deployment protocol -- until then, live and this differ BY DESIGN and any parity
# reading across that boundary must say so.

SPACING_MIN_H = 1.0            # lead: "实际间距超出 [1, 8] 小时: 截到边界"
SPACING_MAX_H = 8.0
DECLARED_FALLBACK_GAP_H = 24.0  # lead: "与上一笔相隔超过 24h: 用交易所声明的间隔"

SPACING_EXACT = "SPACING_EXACT"
SPACING_CLAMPED_LOW = "SPACING_CLAMPED_LOW"
SPACING_CLAMPED_HIGH = "SPACING_CLAMPED_HIGH"
DECLARED_FIRST_EVENT = "DECLARED_FIRST_EVENT"
DECLARED_LONG_GAP = "DECLARED_LONG_GAP"
DECLARED_UNAVAILABLE = "UNRESOLVED_DECLARED_UNAVAILABLE"
NON_INCREASING_TIME = "UNRESOLVED_NON_INCREASING_TIME"

D10_CLAMPED = (SPACING_CLAMPED_LOW, SPACING_CLAMPED_HIGH)
D10_DECLARED = (DECLARED_FIRST_EVENT, DECLARED_LONG_GAP)
D10_USABLE = (SPACING_EXACT,) + D10_CLAMPED + D10_DECLARED


def interval_d10(prev_ft, ft, declared_iv):
    """The D10 stage 2 interval for ONE settlement. Returns {iv, tier, gap_h, declared_iv}.

    prev_ft -- the previous settlement's unix seconds for the SAME symbol, or None if this is its first
    ft      -- this settlement's unix seconds
    declared_iv -- the exchange's declared interval for this settlement (the archive column), or None

    Order is lead's, and it matters: the long-gap fallback is checked BEFORE clamping, so a 30h gap uses the
    declared interval rather than clamping to 8.0. A gap of exactly 24h is NOT "> 24h", so it clamps.

    Never returns a default 8.0. The defect family this file exists for is precisely
    `declared-if-present -> else spacing -> else 8.0`, so when the declared value is needed and absent the
    answer is UNRESOLVED_DECLARED_UNAVAILABLE and the caller must handle it, not a silent 8.
    """
    d = _f(declared_iv)
    ft = None if ft is None else int(ft)
    if ft is None:
        return {"iv": None, "tier": NON_INCREASING_TIME, "gap_h": None, "declared_iv": d,
                "note": "no settlement timestamp"}
    if prev_ft is None:
        if d is None:
            return {"iv": None, "tier": DECLARED_UNAVAILABLE, "gap_h": None, "declared_iv": None,
                    "note": "first event for this symbol and no declared interval; not defaulted to 8.0"}
        return {"iv": d, "tier": DECLARED_FIRST_EVENT, "gap_h": None, "declared_iv": d}
    gap_s = ft - int(prev_ft)
    if gap_s <= 0:
        return {"iv": None, "tier": NON_INCREASING_TIME, "gap_h": gap_s / 3600.0, "declared_iv": d,
                "note": "settlements are not strictly increasing; a data error, refused rather than guessed"}
    gap_h = gap_s / 3600.0
    if gap_h > DECLARED_FALLBACK_GAP_H:
        if d is None:
            return {"iv": None, "tier": DECLARED_UNAVAILABLE, "gap_h": gap_h, "declared_iv": None,
                    "note": "gap exceeds the fallback threshold and no declared interval is available"}
        return {"iv": d, "tier": DECLARED_LONG_GAP, "gap_h": gap_h, "declared_iv": d}
    if gap_h < SPACING_MIN_H:
        return {"iv": SPACING_MIN_H, "tier": SPACING_CLAMPED_LOW, "gap_h": gap_h, "declared_iv": d}
    if gap_h > SPACING_MAX_H:
        return {"iv": SPACING_MAX_H, "tier": SPACING_CLAMPED_HIGH, "gap_h": gap_h, "declared_iv": d}
    return {"iv": gap_h, "tier": SPACING_EXACT, "gap_h": gap_h, "declared_iv": d}


def interval_d10_series(fts, declared_ivs):
    """Apply interval_d10 across one symbol's settlement series.

    Returns (list of per-event results, Counter of tiers). lead requires the clamped events to be counted
    per event and named, so the counter is part of the contract rather than a convenience.
    """
    import collections
    out, tiers = [], collections.Counter()
    prev = None
    for k, ft in enumerate(fts):
        d = declared_ivs[k] if declared_ivs is not None and k < len(declared_ivs) else None
        r = interval_d10(prev, ft, d)
        out.append(r)
        tiers[r["tier"]] += 1
        if r["tier"] != NON_INCREASING_TIME:
            prev = int(ft)
    return out, tiers
