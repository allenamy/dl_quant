"""sigma_ladder — read-only consumer of the dashboard-written gross ladder state (PREREG_deploy_sigma_ladder_2026-09-04 §1).

The anchor loop multiplies external_book.gross_mult by `g`. FAIL-SAFE IS g = 1.0: a missing, stale,
malformed, out-of-range or tampered file never reduces exposure; it yields g=1.0 with a `reason`
the loop logs and (when the file exists but is rejected) alarms INFO. Pure functions + one loader."""
from __future__ import annotations
import hashlib, json, os, time
from typing import Any, Dict, Optional, Tuple

ALLOWED_G = (0.5, 1.0)
MAX_AGE_S = 6 * 3600
SCHEMA = "sigma_ladder_v1"
DEFAULT_PATH = os.path.join(os.environ.get("LIVE_STATE_ROOT", os.path.expanduser("~/dl_quant_live/state")), "live", "sigma_ladder.json")


def _sha(doc: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps({k: doc.get(k) for k in ("schema", "g", "p", "anchor_ts", "written_utc")}, sort_keys=True).encode()).hexdigest()[:16]


def evaluate(doc: Optional[Dict[str, Any]], now: float) -> Tuple[float, Dict[str, Any]]:
    """Return (g, info). Pure: `doc` is the parsed file (or None), `now` epoch seconds."""
    info: Dict[str, Any] = {"src": "sigma_ladder", "g": 1.0, "accepted": False, "reason": None}
    if doc is None:
        info["reason"] = "missing"; return 1.0, info
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        info["reason"] = "schema"; return 1.0, info
    try:
        g = float(doc["g"])
    except Exception:
        info["reason"] = "g_unreadable"; return 1.0, info
    if not any(abs(g - a) < 1e-12 for a in ALLOWED_G):
        info["reason"] = f"g_out_of_whitelist:{g}"; return 1.0, info
    if doc.get("sha") != _sha(doc):
        info["reason"] = "sha_mismatch"; return 1.0, info
    try:
        wt = time.mktime(time.strptime(str(doc["written_utc"])[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
    except Exception:
        info["reason"] = "written_utc_unreadable"; return 1.0, info
    age = float(now) - wt
    if age < -600 or age > MAX_AGE_S:
        info["reason"] = f"stale_or_future:{age:.0f}s"; return 1.0, info
    info.update({"g": g, "accepted": True, "p": doc.get("p"), "anchor_ts": doc.get("anchor_ts"), "age_s": round(age, 1),
                 "streak_low": doc.get("streak_low"), "streak_high": doc.get("streak_high"), "rule": doc.get("rule")})
    return g, info


def load(path: str = DEFAULT_PATH, now: Optional[float] = None) -> Tuple[float, Dict[str, Any]]:
    """Read the state file and evaluate. Any I/O or parse failure -> g=1.0 with reason."""
    now = time.time() if now is None else now
    if not os.path.exists(path):
        return evaluate(None, now)
    try:
        with open(path) as fh:
            doc = json.load(fh)
    except Exception as e:  # noqa: BLE001
        g, info = evaluate({"schema": "corrupt"}, now); info["reason"] = f"unreadable:{type(e).__name__}"; return g, info
    g, info = evaluate(doc, now); info["path"] = path
    return g, info
