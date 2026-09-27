#!/usr/bin/env python3
"""Synthetic red/green controls; no production imports, credentials or network."""
import copy
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

import recovery_acceptance as R

A = 1790524800
NOW = "2026-09-27T17:05:00Z"


class RecoveryAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.inputs = {k: str(self.root / k) for k in (
            "inspect", "anchors", "anchor_log", "ledger_receipt", "alarm_log",
            "watchdog_eval", "watchdog_state", "anchor_report", "venue_receipt")}
        self.data = {
            "inspect": f"### anchor {A} = 09-27 16:00:00Z  [BLIND: per-arm outcomes withheld]\nDONE\n",
            "anchors": [{"anchor_ts": A + 1440.8, "rebalance_id": "A1790526240",
                "target_gross": 200000.0, "realized_gross": 140000.0,
                "opening_halted": False, "external_book": {"nominal_ts": A,
                    "ok": True, "reason": None, "sha_ok": True},
                "chase_experiment": {"secret_arm_result": "DO_NOT_ECHO"}}],
            "anchor_log": '2026-09-27T16:00:01Z anchor start mode=LIVE\n2026-09-27T16:25:00Z phase_A: {"action":"TRADE","book_source":"external","rebalance_id":"A1790526240","anchor_ts":1790526240.8}\n2026-09-27T16:49:00Z anchor done rc=0\n',
            "ledger_receipt": {"A": A, "rebalance_id": "A1790526240", "utc": "2026-09-27T17:02:00Z",
                "K2_fill_ratio": 0.70, "K4_blocked_by_halt_rows": 0,
                "K5_watchdog_state_json_exists": False},
            "alarm_log": [{"ts": "2026-09-27T08:48:10Z", "severity": "HIGH", "msg": "historical"}],
            "watchdog_eval": {"evaluated_utc": "2026-09-27T16:48:00Z", "tripped": False,
                "triggers": [], "conditions_blind": [], "conditions_unevaluated": []},
            "anchor_report": {"anchor_ts": A, "utc": "2026-09-27T16:55:06Z", "status": "green", "lines": []},
            "venue_receipt": {"anchor": A, "rebalance_id": "A1790526240", "utc": "2026-09-27T17:01:30Z",
                "device": "venue_readonly_symbol_bound.py", "identity_key": "symbol_orderId_v1", "VERDICT": "PASS", "bad": [],
                "window_ms": [1790525640000, 1790528480000], "n_commission_rows": 320,
                "n_symbols": 300, "n_venue_trades": 320, "n_foreign_order_ids": 0,
                "fill_ratio_realized_over_target": 0.70, "blocked_by_halt_rows": 0},
        }

    def run_case(self, minimum=0.6):
        for k, d in self.data.items():
            p = Path(self.inputs[k])
            if d is None:
                if p.exists(): p.unlink()
            elif k in ("inspect", "anchor_log"):
                p.write_text(d)
            elif k in ("anchors", "alarm_log"):
                p.write_text("\n".join(json.dumps(r) for r in d) + "\n")
            else:
                p.write_text(json.dumps(d))
        return R.evaluate(self.inputs, A, NOW, minimum)

    def check(self, result, key, status):
        self.assertIn(key, result["checks"], "required gate has not been implemented")
        self.assertEqual(result["checks"][key]["status"], status)

    def test_complete_receipts_pass_and_never_echo_arm_data(self):
        r = self.run_case()
        self.assertEqual(r["verdict"], "PASS")
        self.assertNotIn("DO_NOT_ECHO", json.dumps(r))
        self.assertFalse(r["coverage"]["global_single_writer_proven"])

    def test_old_or_missing_report_is_pending_not_pass(self):
        for report in [None, {"anchor_ts": A - 14400, "utc": "2026-09-27T12:55:06Z", "status": "green"}]:
            with self.subTest(report=report):
                self.data["anchor_report"] = report
                r = self.run_case()
                self.assertEqual(r["verdict"], "PENDING")
                self.check(r, "anchor_report", "PENDING")

    def test_false_nominal_anchor_cannot_hide_in_rid_time_range(self):
        self.data["anchors"][0]["external_book"]["nominal_ts"] = A - 14400
        self.assertEqual(self.run_case()["verdict"], "FAIL")

    def test_rid_and_anchor_wall_time_must_agree(self):
        self.data["anchors"][0]["rebalance_id"] = "A1790526250"
        self.assertEqual(self.run_case()["verdict"], "FAIL")

    def test_duplicate_anchor_rows_fail(self):
        self.data["anchors"] *= 2
        self.assertEqual(self.run_case()["verdict"], "FAIL")

    def test_halt_or_bad_external_book_fail(self):
        baseline = copy.deepcopy(self.data)
        for field in ["halt", "external", "sha"]:
            with self.subTest(field=field):
                self.data = copy.deepcopy(baseline)
                if field == "halt": self.data["anchors"][0]["opening_halted"] = True
                elif field == "external": self.data["anchors"][0]["external_book"]["ok"] = False
                else: self.data["anchors"][0]["external_book"]["sha_ok"] = False
                self.assertEqual(self.run_case()["verdict"], "FAIL")

    def test_low_or_nonfinite_fill_ratio_never_passes(self):
        for value in [0.0, float("nan"), float("inf")]:
            with self.subTest(value=value):
                self.data["anchors"][0]["realized_gross"] = value
                self.assertNotEqual(self.run_case()["verdict"], "PASS")

    def test_second_anchor_uses_95_percent_gate(self):
        self.assertEqual(self.run_case(0.95)["verdict"], "FAIL")

    def test_missing_or_nan_watchdog_tripped_is_unknown(self):
        for value in [None, float("nan"), 0, "false"]:
            with self.subTest(value=value):
                self.data["watchdog_eval"]["tripped"] = value
                self.check(self.run_case(), "watchdog_eval", "UNKNOWN")

    def test_future_watchdog_is_fail_and_old_watchdog_pending(self):
        for date, status in [("2026-09-27T20:48:00Z", "FAIL"), ("2026-09-27T12:40:16Z", "PENDING")]:
            self.data["watchdog_eval"]["evaluated_utc"] = date
            self.check(self.run_case(), "watchdog_eval", status)

    def test_blind_watchdog_never_passes(self):
        self.data["watchdog_eval"]["conditions_blind"] = ["cond5"]
        self.assertNotEqual(self.run_case()["verdict"], "PASS")

    def test_existing_watchdog_state_fails(self):
        self.data["watchdog_state"] = {"reduce_only": True}
        self.check(self.run_case(), "watchdog_state", "FAIL")

    def test_normal_live_watchdog_file_passes_and_records_presence(self):
        self.data["watchdog_state"] = {"reduce_only": False, "tripped_at": None, "_mode": "LIVE"}
        self.data["ledger_receipt"]["K5_watchdog_state_json_exists"] = True
        r = self.run_case()
        self.assertEqual(r["verdict"], "PASS")
        self.assertTrue(r["inputs"]["watchdog_state"]["present"])
        self.assertIn("sha256", r["inputs"]["watchdog_state"])

    def test_state_missing_malformed_contradictory_or_wrong_mode_never_passes(self):
        normal = {"reduce_only": False, "tripped_at": None, "_mode": "LIVE"}
        states = [{}, [], {**normal, "reduce_only": "false"}, {**normal, "reduce_only": 0},
                  {**normal, "tripped_at": "2026-09-27T16:48:00Z"}, {**normal, "_mode": "DRY_RUN"},
                  {**normal, "tripped": True}, {**normal, "kind": "proportional_local"},
                  {**normal, "degradation": {}}, {**normal, "opening_halted": True}]
        states += [{k: v for k, v in normal.items() if k != missing} for missing in normal]
        for state in states:
            with self.subTest(state=state):
                self.data["watchdog_state"] = state
                self.data["ledger_receipt"]["K5_watchdog_state_json_exists"] = True
                self.assertNotEqual(self.run_case()["checks"]["watchdog_state"]["status"], "PASS")

    def test_ledger_presence_is_observation_and_must_match_direct_state(self):
        for present, receipt in [(True, False), (False, True), (False, 0), (False, None)]:
            self.data["watchdog_state"] = {"reduce_only": False, "tripped_at": None, "_mode": "LIVE"} if present else None
            self.data["ledger_receipt"]["K5_watchdog_state_json_exists"] = receipt
            self.assertNotEqual(self.run_case()["checks"]["ledger_receipt"]["status"], "PASS")

    def test_existing_state_invalid_json_or_unreadable_is_unknown(self):
        self.data["watchdog_state"] = {"reduce_only": False, "tripped_at": None, "_mode": "LIVE"}
        self.data["ledger_receipt"]["K5_watchdog_state_json_exists"] = True
        self.run_case(); p = Path(self.inputs["watchdog_state"])
        p.write_text("{broken DO_NOT_ECHO")
        self.check(R.evaluate(self.inputs, A, NOW), "watchdog_state", "UNKNOWN")
        original = Path.read_bytes
        def unreadable(path):
            if path == p: raise PermissionError("denied")
            return original(path)
        with patch.object(Path, "read_bytes", unreadable):
            self.check(R.evaluate(self.inputs, A, NOW), "watchdog_state", "UNKNOWN")

    def test_separate_rid_clock_and_capture_clock_bind_to_real_phase_a(self):
        self.data["anchors"][0]["anchor_ts"] = A + 1441.442726
        self.data["anchor_log"] = self.data["anchor_log"].replace('1790526240.8', '1790526241.442726')
        self.assertEqual(self.run_case()["verdict"], "PASS")

    def test_phase_a_missing_wrong_identity_or_duplicate_cannot_pass(self):
        base = self.data["anchor_log"]
        phase = next(line for line in base.splitlines() if "phase_A:" in line)
        cases = [(base.replace(phase + "\n", ""), "PENDING"),
                 (base.replace('"anchor_ts":1790526240.8', '"anchor_ts":1790526241.8'), "FAIL"),
                 (base.replace('"rebalance_id":"A1790526240"', '"rebalance_id":"A1790526200"'), "FAIL"),
                 (base + phase + "\n", "FAIL")]
        for log, status in cases:
            self.data["anchor_log"] = log
            self.check(self.run_case(), "anchor", status)

    def test_phase_a_log_seconds_are_truncated_and_optional_nominal_is_checked(self):
        self.data["anchor_log"] = self.data["anchor_log"].replace('16:25:00Z', '16:24:00Z')
        self.assertEqual(self.run_case()["verdict"], "PASS")
        self.data["anchor_log"] = self.data["anchor_log"].replace('"action":"TRADE"', '"action":"TRADE","external_filters":{"nominal_ts":1790510400}')
        self.check(self.run_case(), "anchor", "FAIL")

    def test_unlistable_state_parent_is_unknown(self):
        self.run_case()
        with patch.object(Path, "iterdir", side_effect=PermissionError("unreadable")):
            r = R.evaluate(self.inputs, A, NOW)
        self.check(r, "watchdog_state", "UNKNOWN")

    def test_nonexistent_state_parent_is_unknown(self):
        self.inputs["watchdog_state"] = str(self.root / "missing" / "state.json")
        self.check(self.run_case(), "watchdog_state", "UNKNOWN")

    def test_new_high_alarm_fails_and_does_not_echo_message(self):
        self.data["alarm_log"].append({"ts": "2026-09-27T16:48:10Z", "severity": "HIGH", "msg": "DO_NOT_ECHO"})
        r = self.run_case()
        self.check(r, "alarms", "FAIL")
        self.assertNotIn("DO_NOT_ECHO", json.dumps(r))

    def test_pending_report_cannot_mask_foreign_trade_fail(self):
        self.data["anchor_report"] = None
        self.data["venue_receipt"]["n_foreign_order_ids"] = 1
        self.assertEqual(self.run_case()["verdict"], "FAIL")

    def test_venue_stale_wrong_rid_future_or_empty_coverage_never_pass(self):
        baseline = copy.deepcopy(self.data)
        for change in [{"anchor": A - 14400}, {"rebalance_id": "A1790526250"},
                       {"utc": "2026-09-27T21:01:30Z"}, {"n_venue_trades": 0, "n_commission_rows": 0},
                       {"window_ms": [1790525640000, 1790526600000]}, {"VERDICT": "UNKNOWN"}]:
            with self.subTest(change=change):
                self.data = copy.deepcopy(baseline)
                self.data["venue_receipt"].update(change)
                self.assertNotEqual(self.run_case()["verdict"], "PASS")

    def test_ledger_blocked_rows_fail(self):
        self.data["ledger_receipt"]["K4_blocked_by_halt_rows"] = 1
        self.assertEqual(self.run_case()["verdict"], "FAIL")

    def test_legacy_bare_id_receipt_cannot_pass(self):
        self.data["venue_receipt"].update(device="venue_readonly.py")
        self.data["venue_receipt"].pop("identity_key")
        self.check(self.run_case(), "venue_receipt", "UNKNOWN")

    def test_missing_anchor_done_pending_and_failed_done_fail(self):
        start = "2026-09-27T16:00:01Z anchor start mode=LIVE\n"
        self.data["anchor_log"] = start
        self.check(self.run_case(), "anchor_done", "PENDING")
        self.data["anchor_log"] += "2026-09-27T16:49:00Z anchor done rc=1\n"
        self.check(self.run_case(), "anchor_done", "FAIL")

    def test_inspect_wrong_anchor_or_unblind_rejected(self):
        for text in ["### anchor 1790510400 = stale\nDONE\n", f"### anchor {A} = [UNBLINDED: x]\nDONE\n"]:
            self.data["inspect"] = text
            self.assertEqual(self.run_case()["verdict"], "FAIL")

    def test_malformed_input_becomes_unknown_without_raw_content(self):
        self.run_case()
        Path(self.inputs["anchors"]).write_text("not-json DO_NOT_ECHO")
        r = R.evaluate(self.inputs, A, NOW)
        self.assertEqual(r["verdict"], "UNKNOWN")
        self.assertNotIn("DO_NOT_ECHO", json.dumps(r))

    def test_cli_pass_exit_receipt_and_no_overwrite(self):
        self.run_case()
        out = self.root / "verdict.json"
        cmd = [sys.executable, "-B", str(Path(R.__file__)), "--anchor", str(A),
               "--observed-at", NOW, "--out", str(out)]
        for k, path in self.inputs.items(): cmd += ["--" + k.replace("_", "-"), path]
        run = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(out.read_text())["verdict"], "PASS")
        before = out.read_bytes()
        again = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(again.returncode, 0)
        self.assertEqual(out.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
