"""Read-only, stdlib-only heartbeat snapshot. No venue calls or executor imports.

LOCAL_NO_FLAG is only a statement about the captured local records. It is
neither an anchor acceptance nor proof of model identity / venue positions.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path


FIELDS = ("triggers", "metric_errors", "conditions_blind", "conditions_unevaluated", "conditions_partial", "conditions_degraded")


def stamp(s):
    if not isinstance(s, str):
        raise ValueError("timestamp_not_string")
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("timestamp_without_zone")
    return t.timestamp()


def read_json(path):
    meta = {"path": str(path)}
    try:
        raw = path.read_bytes()  # Parse precisely the bytes hashed below.
        meta["sha256"] = hashlib.sha256(raw).hexdigest()
        def reject_constant(value):
            raise ValueError("nonfinite_json")
        return json.loads(raw, parse_constant=reject_constant), meta
    except (OSError, ValueError) as e:
        meta["error"] = type(e).__name__
        return None, meta


def summarize(state, ev, jobs, heartbeat, now):
    if not __debug__:
        return {"verdict": "UNAVAILABLE", "errors": ["optimized_python_disables_schema_checks"], "anchor_acceptance": False}
    errors = []
    flags = []
    out = {"observed_utc": now, "anchor_acceptance": False,
           "scope": "local_records_only_no_venue_or_model_verification"}
    try:
        clock = stamp(now)
    except (ValueError, TypeError):
        return dict(out, verdict="UNAVAILABLE", errors=["invalid_observation_time"])
    try:
        assert isinstance(state, dict) and isinstance(state["_mode"], str)
        assert type(state["reduce_only"]) is bool and "tripped_at" in state
        if state["tripped_at"] is not None:
            assert isinstance(state["tripped_at"], (str, int, float)) and type(state["tripped_at"]) is not bool
            flags.append("state_has_trip")
        out["state"] = {k: state[k] for k in ("_mode", "reduce_only", "tripped_at")}
        if state["_mode"] != "LIVE" or state["reduce_only"]:
            flags.append("state_not_unrestricted_live")
    except (AssertionError, KeyError, TypeError):
        errors.append("state_schema")
    try:
        assert isinstance(ev, dict) and type(ev["tripped"]) is bool
        age = clock - stamp(ev["evaluated_utc"])
        assert age >= -5
        assert all(isinstance(ev[k], list) for k in FIELDS)
        out["watchdog"] = {"evaluated_utc": ev["evaluated_utc"], "age_seconds": age,
                           "tripped": ev["tripped"], "counts": {k: len(ev[k]) for k in FIELDS}}
        if ev["tripped"]:
            flags.append("watchdog_tripped")
        flags.extend(k for k in FIELDS if ev[k])
        # No new watchdog age threshold: it is evaluated per 4h anchor.
    except (AssertionError, KeyError, TypeError, ValueError):
        errors.append("watchdog_schema")
    try:
        assert isinstance(jobs, list)
        # registry_edit.add does not require closed; its matching inflight_status
        # treats absence as still open. Never infer completion from another label.
        assert all(isinstance(j, dict) and isinstance(j["name"], str) and j["name"] and ("closed" not in j or type(j["closed"]) is bool) for j in jobs)
        assert len({j["name"] for j in jobs}) == len(jobs)
        out["active_jobs"] = [j["name"] for j in jobs if not j.get("closed", False)]
        out["closed_jobs_count"] = sum(j.get("closed", False) for j in jobs)
        out["registry_implicit_open_names"] = [j["name"] for j in jobs if "closed" not in j]
        out["registry_scope"] = "recorded_status_not_process_liveness"
    except (AssertionError, KeyError, TypeError):
        errors.append("registry_schema")
    try:
        assert isinstance(heartbeat, dict)
        ms = heartbeat["run_ms"]
        assert type(ms) in (int, float) and math.isfinite(ms)
        t = stamp(heartbeat["run_utc"])
        assert abs(ms / 1000 - t) < 1.0 and clock - t >= -5
        age = clock - t
        out["collector"] = {"run_utc": heartbeat["run_utc"], "age_seconds": age, "fresh": age <= 180}
        if age > 180:
            flags.append("collector_heartbeat_stale")
    except (AssertionError, KeyError, TypeError, ValueError, OverflowError):
        errors.append("collector_schema")
    out.update(errors=errors, flags=flags)
    out["verdict"] = "UNAVAILABLE" if errors else "LOCAL_ATTENTION" if flags else "LOCAL_NO_FLAG"
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    home = Path.home()
    paths = {
        "state": home / "dl_quant_live/state/live/watchdog/state.json",
        "watchdog": home / "dl_quant_live/state/live/watchdog/last_eval.json",
        "registry": args.registry,
        "collector": home / "xvenue_collector/state/heartbeat.json",
    }
    pairs = {k: read_json(v) for k, v in paths.items()}
    now = datetime.now(timezone.utc).isoformat()
    result = summarize(*(pairs[k][0] for k in paths), now)
    result["sources"] = {k: v[1] for k, v in pairs.items()}
    result["device_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    text = json.dumps(result, indent=2, allow_nan=False, ensure_ascii=False) + "\n"
    if args.output:
        with args.output.open("x") as f:  # Never overwrite an earlier receipt.
            f.write(text)
    print(text, end="")
    return 3 if result["verdict"] == "UNAVAILABLE" else 1 if result["verdict"] == "LOCAL_ATTENTION" else 0


if __name__ == "__main__":
    raise SystemExit(main())
