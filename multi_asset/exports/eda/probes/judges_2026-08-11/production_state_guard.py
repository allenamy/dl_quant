"""Production-state isolation guard — no test may write into production state.

★ WHY THIS EXISTS: FAILURE FORM #4, THE MOST INSIDIOUS ONE.

  A newly-installed "standing state" display immediately caught an invisible shutdown. It looked
  like a textbook verification success. Investigating the source showed the standing state had been
  written into PRODUCTION by our own test fixtures (a -8%/-48% synthetic day). The verification
  apparatus manufactured the very condition it then detected -- supplying both the "defect" and the
  "ability to detect the defect", each corroborating the other.

  Four ways a check passes for the wrong reason:
    1. the TEST supplied a condition production never supplies      (watchdog unit tests)
    2. REALITY supplied a false condition and nobody questioned it  (57.8h "stale" panel)
    3. the ENVIRONMENT changed between observation and verification (re-checking a fixed system)
    4. the VERIFICATION APPARATUS manufactured the condition it then detected   <-- this module

  #4 is the worst because the defect and its detection corroborate each other, so the whole thing
  reads as a clean success story.

★ THE RULE, ENFORCED HERE AS AN ASSERTION RATHER THAN A COMMENT:
    No test may write production state. Every state path must be explicitly overridden, and at the
    end of the run the guard asserts production state is byte-identical to the snapshot taken
    before it. Watchdog state was polluted this time; next time it would be a different path --
    so the guard covers ALL of them, not the one that happened to break.

Usage:
    g = ProductionStateGuard(); g.snapshot()
    ... run tests ...
    ok, diff = g.assert_unchanged()
"""
from __future__ import annotations
import hashlib, os
from typing import Dict, Tuple

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"

# EVERY production state path. Adding a new one that writes state? Add it here too.
PRODUCTION_STATE_PATHS = {
    "pilot_log":       MA + "/exports/live/pilot_log",
    "watchdog_state":  MA + "/exports/live/watchdog",          # state.json, events.jsonl, ALARM.log, quarantine/
    "pilot_daily":     MA + "/exports/live/pilot_daily",       # reports, mirror, delivery_status, injection_evidence
    "regime":          MA + "/exports/live/regime",
    "track_matrix":    MA + "/exports/live/track_matrix",
    "challenger":      MA + "/exports/live/challenger",
    "fixfunding":      MA + "/exports/live/fixfunding",
}


def _fingerprint(root: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not os.path.exists(root):
        return out
    if os.path.isfile(root):
        return {os.path.basename(root): _hash(root)}
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            p = os.path.join(dirpath, fn)
            try:
                out[os.path.relpath(p, root)] = _hash(p)
            except OSError:
                out[os.path.relpath(p, root)] = "UNREADABLE"
    return out


def _hash(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()[:16]


class ProductionStateGuard:
    def __init__(self, paths=None):
        self.paths = paths or PRODUCTION_STATE_PATHS
        self.before: Dict[str, Dict[str, str]] = {}

    def snapshot(self):
        self.before = {k: _fingerprint(v) for k, v in self.paths.items()}
        return self.before

    def diff(self) -> Dict[str, Dict[str, list]]:
        out = {}
        for k, root in self.paths.items():
            now = _fingerprint(root)
            b = self.before.get(k, {})
            added = sorted(set(now) - set(b))
            removed = sorted(set(b) - set(now))
            changed = sorted(f for f in set(now) & set(b) if now[f] != b[f])
            if added or removed or changed:
                out[k] = {"added": added[:10], "removed": removed[:10], "changed": changed[:10],
                          "n_added": len(added), "n_removed": len(removed),
                          "n_changed": len(changed)}
        return out

    def assert_unchanged(self) -> Tuple[bool, Dict]:
        d = self.diff()
        return (not d), d


def override_all(PD, RC=None, DR=None, tmp: str = ""):
    """Point every module-level production path at a temp dir. Returns a restore callable.

    Overriding only the path that broke last time is how the next one breaks -- so this touches
    all of them, and tests should use it rather than setting paths individually.
    """
    saved = {}

    def _set(mod, attr, val):
        if mod is not None and hasattr(mod, attr):
            saved[(mod, attr)] = getattr(mod, attr)
            setattr(mod, attr, val)

    _set(PD, "LOG_ROOT", tmp + "/pilot_log")
    _set(PD, "OUT", tmp + "/pilot_daily")
    _set(PD, "MIRROR", tmp + "/pilot_daily/mirror")
    _set(PD, "WATCHDOG_STATE_DIR", tmp + "/watchdog")
    _set(RC, "OUT", tmp + "/regime")
    _set(DR, "STATUS_PATH", tmp + "/delivery_status.json")
    _set(DR, "CONFIG", tmp + "/smtp_config.json")

    def restore():
        for (mod, attr), val in saved.items():
            setattr(mod, attr, val)
    return restore
