#!/usr/bin/env python3
"""Real local_ledger + anchor_check, synthetic transport; never production/API."""
import sys
import types
import unittest
import contextlib
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import venue_readonly_symbol_bound as V

A = 1790524800
RID = "A1790526240"


class SymbolIdentityTests(unittest.TestCase):
    def check_trade(self, local_symbol="ETHUSDT", trade_symbol="BTCUSDT", local_oid=77,
                    trade_oid=77, local_cid="same-cid", venue_cid="same-cid"):
        order = {"symbol": local_symbol, "rebalance_id": RID, "submit_ts": A + 1440,
                 "client_id": local_cid,
                 "request_ledger": [] if local_oid is None else [{"order_id": local_oid}]}
        anchor = {"rebalance_id": RID, "target_gross": 100.0, "realized_gross": 70.0}
        def day(d):
            return {"orders": [order], "anchors": [anchor]} if d == "20260927" else {"orders": [], "anchors": []}
        pl = types.SimpleNamespace(read_day=lambda root, d: day(d), read_fills=lambda root, d: [])
        def transport(path, params):
            if path == "/fapi/v1/income":
                return [{"symbol": trade_symbol, "time": (A + 1500) * 1000}]
            if path == "/fapi/v1/userTrades":
                return [{"symbol": trade_symbol, "orderId": trade_oid, "quoteQty": "70", "maker": True}]
            if path == "/fapi/v1/allOrders":
                return [{"symbol": trade_symbol, "orderId": trade_oid, "clientOrderId": venue_cid}]
            raise AssertionError("unplanned endpoint")
        with patch.dict(sys.modules, {"pilot_log": pl}), patch.object(V, "TRANSPORT", transport):
            return V.anchor_check(A, now_ms=(A + 3600) * 1000)

    def test_cross_symbol_same_order_id_is_foreign(self):
        r = self.check_trade()
        self.assertEqual(r["n_foreign_order_ids"], 1)
        self.assertEqual(r["VERDICT"], "FAIL")

    def test_cross_symbol_same_client_id_fallback_is_foreign(self):
        r = self.check_trade(local_oid=None)
        self.assertEqual(r["n_foreign_order_ids"], 1)

    def test_same_symbol_same_order_id_is_local(self):
        self.assertEqual(self.check_trade(local_symbol="BTCUSDT")["VERDICT"], "PASS")

    def test_same_symbol_client_id_fallback_remains_valid(self):
        r = self.check_trade(local_symbol="BTCUSDT", local_oid=None)
        self.assertEqual(r["VERDICT"], "PASS")
        self.assertEqual(r["n_matched_by_client_id_only"], 1)

    def test_large_decimal_string_ids_do_not_round(self):
        r = self.check_trade(local_symbol="BTCUSDT", local_oid="9007199254740993", trade_oid="9007199254740992")
        self.assertEqual(r["n_foreign_order_ids"], 1)

    def test_float_or_boolean_ids_are_unknown_not_lossily_coerced(self):
        for invalid in [77.0, True, "77.5"]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(V.Unknown):
                    self.check_trade(local_oid=invalid)

    def test_non_readonly_endpoint_still_refused(self):
        with self.assertRaises(RuntimeError):
            V._get("/fapi/v1/order", {})

    def test_pagination_preserves_boundary_and_real_duplicates(self):
        rows = [{"time": i + 1, "tranId": i} for i in range(1002)]
        rows[999]["time"] = rows[1000]["time"] = 1000
        rows += [{"time": 2000, "tranId": 8888}] * 2
        def tr(path, p):
            self.assertEqual(path, "/fapi/v1/income")
            return [r for r in rows if p["startTime"] <= r["time"] <= p["endTime"]][:p["limit"]]
        with patch.object(V, "TRANSPORT", tr):
            self.assertEqual(len(V.income_all("COMMISSION", 0, 3000)), 1004)

    def test_saturated_trade_page_remains_unknown(self):
        ledger = ({("BTCUSDT", 77)}, set(), {"rebalance_id": RID, "target_gross": 100, "realized_gross": 70}, 0, None, 0)
        def tr(path, p):
            if path == "/fapi/v1/income": return [{"time": (A + 1500) * 1000, "symbol": "BTCUSDT"}]
            if path == "/fapi/v1/userTrades": return [{}] * 1000
            raise AssertionError("unexpected path")
        with patch.object(V, "TRANSPORT", tr), self.assertRaises(V.Unknown):
            V.anchor_check(A, now_ms=(A + 3600) * 1000, ledger=ledger)

    def test_main_receipt_has_new_identity_and_cannot_overwrite(self):
        ledger = ({("BTCUSDT", 77)}, set(), {"rebalance_id": RID, "target_gross": 100, "realized_gross": 70}, 0, None, 0)
        def tr(path, p):
            if path == "/fapi/v1/income": return [{"time": (A + 1500) * 1000, "symbol": "BTCUSDT"}]
            if path == "/fapi/v1/userTrades": return [{"symbol": "BTCUSDT", "orderId": 77, "quoteQty": "70", "maker": True}]
            raise AssertionError("unexpected path")
        with tempfile.TemporaryDirectory() as d, patch.object(V, "TRANSPORT", tr), patch.object(V, "local_ledger", return_value=ledger):
            path = Path(d) / "receipt.json"
            argv = ["anchor", "--anchor", str(A), "--out", str(path)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(V.main(argv), 0)
                r = json.loads(path.read_text())
                self.assertEqual(r["device"], "venue_readonly_symbol_bound.py")
                self.assertEqual(r["identity_key"], "symbol_orderId_v1")
                self.assertEqual(len(r["self_sha256"]), 64)
                self.assertFalse(r["coverage"]["global_single_writer_proven"])
                with self.assertRaises(FileExistsError): V.main(argv)
        self.assertEqual(V._cred, {})


if __name__ == "__main__":
    unittest.main()
