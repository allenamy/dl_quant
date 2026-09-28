"""Small offline schema/unknown controls; never imports executor code."""
import copy
import unittest
from light_local_audit import summarize, read_json
from pathlib import Path
import tempfile


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.state = {"_mode": "LIVE", "reduce_only": False, "tripped_at": None}
        self.ev = {"evaluated_utc": "2026-09-28T04:49:20Z", "tripped": False}
        for k in ("triggers", "metric_errors", "conditions_blind", "conditions_unevaluated", "conditions_partial", "conditions_degraded"):
            self.ev[k] = []
        self.jobs = [{"name": "resident", "closed": False}, {"name": "done", "closed": True}]
        self.hb = {"run_utc": "2026-09-28T07:00:00Z", "run_ms": 1790578800000}

    def go(self, now="2026-09-28T07:01:00Z"):
        return summarize(self.state, self.ev, self.jobs, self.hb, now)

    def test_valid_is_local_only_and_registry_uses_closed(self):
        r = self.go()
        self.assertEqual(r["verdict"], "LOCAL_NO_FLAG")
        self.assertEqual(r["active_jobs"], ["resident"])
        self.assertFalse(r["anchor_acceptance"])

    def test_missing_real_keys_never_defaults_to_clean(self):
        for obj, key in (("state", "_mode"), ("ev", "evaluated_utc"), ("ev", "conditions_partial")):
            saved = copy.deepcopy(getattr(self, obj))
            del getattr(self, obj)[key]
            self.assertEqual(self.go()["verdict"], "UNAVAILABLE")
            setattr(self, obj, saved)

    def test_booleans_are_not_truthy_strings(self):
        self.state["reduce_only"] = "false"
        self.assertEqual(self.go()["verdict"], "UNAVAILABLE")

    def test_registry_missing_closed_string_and_duplicate_refused(self):
        for jobs in ([{"name": "x", "status": "done"}], [{"name": "x", "closed": "false"}], self.jobs + [self.jobs[0]]):
            self.jobs = jobs
            self.assertEqual(self.go()["verdict"], "UNAVAILABLE")

    def test_partial_is_not_no_flag(self):
        self.ev["conditions_partial"] = ["cond4_drawdown"]
        r = self.go()
        self.assertEqual(r["verdict"], "LOCAL_ATTENTION")
        self.assertEqual(r["watchdog"]["counts"]["conditions_partial"], 1)

    def test_trip_always_remains_visible(self):
        self.ev["tripped"] = True
        self.hb["run_ms"] = float("nan")
        r = self.go()
        self.assertEqual(r["verdict"], "UNAVAILABLE")
        self.assertTrue(r["watchdog"]["tripped"])

    def test_collector_stale_over_180_seconds(self):
        r = self.go("2026-09-28T07:03:01Z")
        self.assertEqual(r["verdict"], "LOCAL_ATTENTION")
        self.assertFalse(r["collector"]["fresh"])

    def test_heartbeat_timestamp_mismatch(self):
        self.hb["run_ms"] += 60000
        self.assertEqual(self.go()["verdict"], "UNAVAILABLE")

    def test_source_missing_or_bad_json_is_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            self.assertEqual(read_json(p)[1]["error"], "FileNotFoundError")
            p.write_text('{"key": NaN}')
            self.assertEqual(read_json(p)[1]["error"], "ValueError")

    def test_naive_clock_refused(self):
        self.assertEqual(self.go("2026-09-28T07:01:00")["verdict"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
