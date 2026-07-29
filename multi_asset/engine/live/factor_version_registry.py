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

# ★ `assert_funding_dim_expected_exit` IS 0 FOR BOTH VERSIONS SINCE 2026-07-27, AND THAT IS A
#   SEMANTIC CHANGE, NOT A THRESHOLD TWEAK (0C).
#   Until 07-27 the guard asserted ONE caliber (`corrected`) on whatever panel it was pointed at, so
#   the pre-fix panels were expected to FAIL it and this table recorded `1` with the comment "the
#   guard is EXPECTED to fail on this panel". That design put the gate on the wrong artifact and
#   stopped the shadow for 28 hours on its first armed run. The guard now asserts THE CALIBER EACH
#   ARTIFACT IS SUPPOSED TO HAVE — so every panel below passes its own expectation and a non-zero
#   exit means what a gate's non-zero exit should always mean: this artifact is not what it declares.
#   ⇒ A row that says "this is expected to fail" is a standing instruction to ignore a red. There is
#     now no such row, deliberately.
#   ⇒ AND IT IS CONSUMED. It sat here as prose for two days and went stale the moment the guard's
#     semantics changed; an unread declaration cannot notice that it has become false. pilot_daily's
#     guard chain now asserts the observed exit against it.
# ★ `panel_frozen` / `panel_live` ARE DOCUMENTATION. THEY ARE NOT THE CALIBER ROUTING KEY (0C
#   2026-07-29, team-lead ruling). They say which artifact each version is ABOUT; they no longer
#   decide what `assert_funding_dim` expects of a file. A path key is inherited by whatever file is
#   written to that path next, and is lost by the artifact that moves — silently, in both
#   directions. The expectation now travels INSIDE the artifact (`panel_caliber_stamp`), or is keyed
#   to its SHA-256 for artifacts that must not be rewritten (below).
FACTOR_VERSIONS = {
    "funding_ema_broken_v1": {
        "description": "pre-fix funding_ema — per-settlement rate, NOT normalised across 4h/8h. "
                       "This is the AS-TRAINED caliber: the frozen king/s2 heads were fitted on it.",
        "panel_frozen": "exports/wide_dl_full.npz",
        "panel_live": "exports/live/wide_dl_live.npz",
        "expected_caliber": "as_trained",
        "assert_funding_dim_expected_exit": 0,
    },
    "funding_ema_normfix": {
        "description": "settlement-interval corrected (rate * 8/interval_h, per row, before EMA)",
        "panel_frozen": "exports/wide_dl_full_fundfix.npz",
        "panel_live": "exports/live/wide_dl_live_fundfix.npz",
        "expected_caliber": "corrected",
        "assert_funding_dim_expected_exit": 0,
    },
}

# ---- artifacts that predate stamping and MUST NOT be rewritten to add one ----------------------
# ★ KEYED BY CONTENT, NOT BY NAME. sha256_16 of the file's bytes: a property the artifact carries
#   with it, immune to `mv`, and impossible for a different file to inherit.
# ⇒ Why not just stamp them? `exports/wide_dl_full.npz` is the panel the frozen heads were TRAINED
#   on. Appending a stamp member changes the file's sha256, and `panel_caliber_manifest.json`
#   blesses that exact hash as this generation's bit-identity. Adding a guard's own mark to the
#   artifact it guards would invalidate the stronger check to install the weaker one.
# ⇒ An entry here is a standing statement that a specific sequence of bytes holds a specific
#   caliber. A rebuild produces different bytes, does not match, and therefore reads as UNDECLARED
#   (exit 2, CANNOT JUDGE) rather than inheriting this expectation — which is the correct answer
#   for a rebuilt training panel: nobody has yet said what the new one is supposed to be.
UNSTAMPED_ARTIFACT_CALIBER = {
    "2e36dda1d2498c0f": {
        "caliber": "as_trained",
        "artifact": "exports/wide_dl_full.npz (built 2026-07-11)",
        "why": "the panel the frozen king/s2 fold-4 heads were fitted on; never rebuilt since, and "
               "deliberately not rebuilt after the 2026-07-25 settlement-interval fix — retraining "
               "and re-calibering are one decision, not two",
        "size_bytes": 1052380498,
        "recorded_utc": "2026-07-29T09:4xZ",
        "cross_check": "same hash blessed in exports/eda/panel_caliber_manifest.json",
    },
    "5b1b68cc1e4bb974": {
        "caliber": "corrected",
        "artifact": "exports/wide_dl_full_fundfix.npz (built 2026-07-25 by apply_funding_fix)",
        "why": "the corrected rebuild of the training panel, kept as the red-test substrate and the "
               "factor-leg reference; NO frozen head consumes it, which is exactly why it is the "
               "artifact that must FAIL if it ever appears in the training panel's role",
        "size_bytes": 1052380498,
        "recorded_utc": "2026-07-29T09:4xZ",
        "cross_check": "measured +0.1418/+0.1429 against the corrected reference +0.1463 (0C 07-27)",
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


def expected_gate_exit(version: str) -> int:
    """The exit code `assert_funding_dim.py` must return on THIS version's panels.

    Exists so the number is READ rather than merely written. The previous value (1, for the pre-fix
    version) survived a change in the guard's semantics untouched precisely because nothing consumed
    it — the same shape as `norm_stats`' hash, which is recorded in MANIFEST.json and compared by
    nobody. A declaration that is never checked is a comment with a colon in it.
    """
    if version not in FACTOR_VERSIONS:
        raise KeyError(f"unknown factor version {version!r}; known: {sorted(FACTOR_VERSIONS)}")
    return FACTOR_VERSIONS[version]["assert_funding_dim_expected_exit"]


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
        "unstamped_artifact_caliber": UNSTAMPED_ARTIFACT_CALIBER,
        "caliber_routing_rule": ("assert_funding_dim resolves an artifact's expected caliber from "
                                 "(1) the stamp inside the file, (2) this sha256 table, (3) nothing "
                                 "-> CANNOT JUDGE. `panel_frozen`/`panel_live` above are "
                                 "documentation and are NOT consulted for routing: a path key is "
                                 "inherited by whatever file is written there next."),
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
