"""S3: every stage must report whether the thing it processes ACTUALLY ADVANCED.

★ WHY THIS EXISTS
On 2026-07-25 the shadow's newest observation was three days old while the daily cron logged a clean
`done` every morning. Every downstream stage printed a CUMULATIVE count — `wrote 132`, `n_anchors
132`, `scored 132`, `132 anchors / 22 days` — and "132" is perfectly compatible with "not one new
anchor". Only the ingest step printed a real delta (`48168 -> 48697 rows (+529)`), and it counts
panel ROWS, not anchors, so it moved while the anchor frontier did not.

Two rules, both paid for:

  1. **A total is not a progress signal.** The number that tells you the system is alive must be a
     DELTA against the previous run, not a count of everything that exists.
  2. **Read the frontier from the ARTIFACT, never from the writer's tally.** A writer reporting how
     much it wrote is the exact failure this codebase already hit once (`rows_emitted: 110` while
     zero rows reached disk). The artifact on disk is the only witness that cannot flatter itself.

State lives in exports/live/frontier_state.json, one entry per stage. A stage that has never run
reports `first_observation` rather than a delta — absence is said, not folded into 0.
"""
from __future__ import annotations

import glob
import json
import os
from typing import Any, Dict, List, Optional

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
STATE_PATH = MA + "/exports/live/frontier_state.json"


def _load() -> Dict[str, Any]:
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save(state: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        tmp = STATE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f, indent=1)
        os.replace(tmp, STATE_PATH)
    except Exception:
        pass            # a frontier bookkeeping failure must never take down the stage it observes


def anchors_from_json_dir(d: str, key: str = "anchor_ts_ms") -> List[int]:
    """Anchor timestamps READ BACK from the files on disk — not from whatever wrote them."""
    out = []
    for f in glob.glob(os.path.join(d, "positions_*.json")):
        try:
            with open(f) as fh:
                v = json.load(fh).get(key)
            if v is not None:
                out.append(int(v))
        except Exception:
            continue
    return sorted(out)


def report(stage: str, anchors: List[int], log=print, extra: Optional[Dict[str, Any]] = None):
    """Record + print this stage's frontier and its movement since the previous run.

    `anchors` must come from reading the artifact. Returns the record so a caller can publish it.
    """
    import pandas as pd                      # local: keeps this module importable without pandas

    state = _load()
    prev = state.get(stage) or {}
    cur_max = max(anchors) if anchors else None
    cur_n = len(anchors)
    prev_max, prev_n = prev.get("max_anchor_ts_ms"), prev.get("n_anchors")

    rec: Dict[str, Any] = {
        "stage": stage, "n_anchors": cur_n, "max_anchor_ts_ms": cur_max,
        "max_anchor_utc": (pd.to_datetime(cur_max, unit="ms", utc=True).isoformat()
                           if cur_max is not None else None),
        "source": "read back from artifacts on disk",
    }
    if prev_max is None:
        rec["advanced"] = None
        rec["status"] = "first_observation"       # not "0 new" — we have no prior to compare to
    else:
        rec["n_new_anchors"] = cur_n - int(prev_n or 0)
        rec["advanced"] = bool(cur_max is not None and cur_max > prev_max)
        rec["previous_max_anchor_utc"] = pd.to_datetime(prev_max, unit="ms", utc=True).isoformat()
        rec["status"] = "advanced" if rec["advanced"] else "NO_NEW_ANCHORS"
    if extra:
        rec.update(extra)

    if rec["status"] == "first_observation":
        log(f"[frontier] {stage}: first observation — frontier {rec['max_anchor_utc']} "
            f"({cur_n} anchors on disk); no previous run to compare against")
    elif rec["advanced"]:
        log(f"[frontier] {stage}: ADVANCED to {rec['max_anchor_utc']} "
            f"(+{rec['n_new_anchors']} anchors since {rec['previous_max_anchor_utc']})")
    else:
        log(f"[frontier] ★ {stage}: NO NEW ANCHORS — frontier still {rec['max_anchor_utc']} "
            f"(unchanged since the previous run). The stage completed; the data did not move.")

    state[stage] = {"max_anchor_ts_ms": cur_max, "n_anchors": cur_n,
                    "last_seen_utc": pd.Timestamp.utcnow().isoformat()}
    _save(state)
    return rec
