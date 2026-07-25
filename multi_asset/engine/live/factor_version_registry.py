"""SINGLE SOURCE OF TRUTH for which factor version each track is supposed to run.

★ WHY THIS EXISTS: the guard chain closed `observed == DECLARED`, but `DECLARED == what the
  protocol says` was still checked by a human reading two documents. That is the last manual link
  in the version chain, and F10 already replaced exactly this kind of human cross-check with a
  machine assertion once. This closes it: protocol -> declaration -> observation, all machine.

★ IT IS A PER-TRACK MAP, NOT A SCALAR. A global assertion would turn the shadow red immediately and
  for no reason: champion and challenger run the PRE-FIX factor deliberately (they are the weight
  experiment's control), fixfunding runs the corrected one (it exists to test the fix), and the
  pilot book runs whatever protocol §5 makes effective. "Which version is correct" is a property of
  the track, not of the system.

★ THE PROTOCOL MUST REFERENCE THESE SYMBOLS, NOT RESTATE THE STRINGS. If §5 spells out a version
  string in prose, this file has not removed the manual step -- it has only moved it from "check the
  code against the protocol" to "keep a file in sync with the protocol". The point is that the human
  decision is entered ONCE, here, and machines propagate it. (Same pattern as the §11.1 day-budget
  table and the derived-number table.)

The chain necessarily bottoms out in a human somewhere -- the protocol is written by people. The
goal is not to remove the human but to give them exactly one place to type the decision.
"""
from __future__ import annotations
import json, os

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
REGISTRY_PATH = MA + "/exports/eda/factor_version_registry.json"

FACTOR_VERSIONS = {
    "funding_ema_broken_v1": {
        "description": "pre-fix funding_ema — per-settlement rate, NOT normalised across 4h/8h",
        "panel_frozen": "exports/wide_dl_full.npz",
        "panel_live": "exports/live/wide_dl_live.npz",
        "assert_funding_dim_expected_exit": 1,      # the guard is EXPECTED to fail on this panel
    },
    "funding_ema_normfix": {
        "description": "settlement-interval corrected (rate * 8/interval_h, per row, before EMA)",
        "panel_frozen": "exports/wide_dl_full_fundfix.npz",
        "panel_live": "exports/live/wide_dl_live_fundfix.npz",
        "assert_funding_dim_expected_exit": 0,
    },
}

# ---- the human decision, entered ONCE ----------------------------------------------------------
# protocol §5 effective version for the PILOT BOOK (team-lead ruling 2026-07-25: option B).
PROTOCOL_S5_EFFECTIVE = "funding_ema_normfix"

# per-track expected version. §5's ruling governs the pilot book ONLY; the shadow tracks are
# experiments and each declares what it is deliberately running.
TRACK_EXPECTED_VERSION = {
    "pilot_book":           PROTOCOL_S5_EFFECTIVE,
    "champion":             "funding_ema_broken_v1",
    "challenger":           "funding_ema_broken_v1",
    "champion_fixfunding":  "funding_ema_normfix",
}

TRACK_RATIONALE = {
    "pilot_book": "protocol §5 effective version (the ruling); must switch BEFORE pilot emits readings",
    "champion": "control arm of the weight experiment — pre-fix is the design, not a defect",
    "challenger": "the other arm of the same weight experiment — must match champion's input",
    "champion_fixfunding": "exists precisely to measure the fix out-of-sample",
}


def expected_for(track: str) -> str:
    if track not in TRACK_EXPECTED_VERSION:
        raise KeyError(f"unknown track {track!r}; known: {sorted(TRACK_EXPECTED_VERSION)}")
    return TRACK_EXPECTED_VERSION[track]


def assert_track_version(track: str, declared: str):
    """Returns (ok, detail). Non-ok must BLOCK that track's readings."""
    exp = expected_for(track)
    ok = (declared == exp)
    return ok, {
        "track": track, "declared": declared, "expected": exp, "ok": ok,
        "rationale": TRACK_RATIONALE.get(track),
        "meaning": ("declaration matches what the protocol/registry says this track should run"
                    if ok else
                    f"track {track!r} declares {declared!r} but the registry requires {exp!r} — "
                    "the engine is not running what the protocol says it runs"),
    }


def dump():
    payload = {
        "created": "2026-07-25",
        "purpose": "single source of truth: protocol -> declaration -> observation, all machine-checked",
        "protocol_s5_effective_version_pilot_book": PROTOCOL_S5_EFFECTIVE,
        "track_expected_version": TRACK_EXPECTED_VERSION,
        "track_rationale": TRACK_RATIONALE,
        "factor_versions": FACTOR_VERSIONS,
        "protocol_usage_rule": ("protocol §5 must REFERENCE the symbol "
                                "`PROTOCOL_S5_EFFECTIVE` / this JSON, never restate the version "
                                "string in prose — otherwise the manual step is merely relocated "
                                "from 'check code vs protocol' to 'keep file in sync with protocol'"),
    }
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    json.dump(payload, open(REGISTRY_PATH, "w"), indent=1)
    return payload


if __name__ == "__main__":
    print(json.dumps(dump(), indent=1))
