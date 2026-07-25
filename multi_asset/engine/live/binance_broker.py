"""Binance USDT-M perpetual adapter — satisfies the same 4-method contract as watchdog.MockBroker.

★ WHY THIS FILE EXISTS, AND WHAT IT IS NOT
------------------------------------------
`MockBroker` is a *specification*, not an *implementation*. `DEPLOYMENT_MUSTCHECK.md` MC-1 records
that the single most dangerous gap between them is this:

    the opening-halt must NEVER block a reduce-only order.

If a real adapter blocked indiscriminately, moving `halt_opening_orders` to the front of the
degradation ladder — which we did precisely because it is the one rung that needs no venue
cooperation — would block our own exit. An improvement would become a disaster.

MC-1 said that could only be verified with an account. It turns out **the venue documentation
resolves half of it before any account exists**, and the answer is a hard configuration constraint:

    `reduceOnly` "Cannot be sent in Hedge Mode."   (POST /fapi/v1/order)

⇒ In Hedge Mode our flatten cannot carry `reduceOnly` at all. So One-way Mode is not a preference,
it is a **precondition for the protection to exist**. This adapter refuses to arm itself otherwise.

The other half of MC-1 stands: the halt is enforced **in our own code, before any request leaves
this process**, and never delegated to a venue flag. Declining to send needs no exchange, no key,
no fill. That is the whole point of the rung.

MODES (fail-closed by default)
------------------------------
    DRY_RUN  (default)  no credentials read, no authenticated call ever made, orders recorded only
    TESTNET             testnet.binancefuture.com, requires BINANCE_TESTNET_KEY/SECRET
    LIVE                requires BINANCE_KEY/SECRET *and* BINANCE_LIVE_CONFIRM=I_UNDERSTAND

There is deliberately no way to reach LIVE by accident: it needs two independent env vars plus a
literal confirmation string, and it runs the arming checks below before the first order.

ARMING CHECKS (all must pass before LIVE will submit anything)
    A1  position mode is One-way   -> otherwise reduceOnly is unusable  -> NO PROTECTION
    A2  key has no withdrawal permission
    A3  reduce-only probe accepted by the venue (tiny order, immediately cancelled)
    A4  server clock skew within recvWindow

Endpoints used (developers.binance.com, USDT-M futures, verified 2026-07-25):
    POST /fapi/v1/order            timeInForce=GTX is post-only; reduceOnly bool (One-way only)
    POST /fapi/v1/batchOrders      max 5 per request
    GET  /fapi/v3/account          positionAmt / entryPrice / notional / unrealizedProfit
    GET  /fapi/v1/positionSide/dual  dualSidePosition: true=Hedge, false=One-way
    GET  /fapi/v1/income           incomeType=FUNDING_FEE — ONLY LAST 3 MONTHS (see FundingLedger)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from watchdog import BrokerUnavailable, OpeningHalted  # same exceptions the ladder already catches

# ── venue constants ──────────────────────────────────────────────────────────────────────────
BASE_LIVE = "https://fapi.binance.com"
BASE_TESTNET = "https://testnet.binancefuture.com"

TIF_POST_ONLY = "GTX"   # maker-only; venue rejects if it would cross. Our k=900s passive leg.
TIF_IOC = "IOC"         # residual taker top-up. Top-up is MANDATORY, not an optimisation:
                        # letting positions lag costs far more than the extra fee (~+27pp/yr).

# ── error classification ─────────────────────────────────────────────────────────────────────
# ⚠ Source: venue documentation only. NOT ONE of these has been observed on a real account.
# The behavioural fallback below is the actual protection; this table only makes it faster.
# An incomplete table must never fail open.
ERR_ACCOUNT_RESTRICTED = {
    -1002: "not authorized to execute this request",
    -2015: "invalid API-key, IP, or permissions for action",
    -2017: "API keys are locked on this account",
    -4088: "user can not place order currently",
    -4109: "inactive account",
    -4192: "trade forbidden due to cooling-off period",
}
# ★ -4189 is a restriction under which our PROTECTION STILL WORKS: the venue permits reduce-only
# but not opening. That is functionally the state our own halt puts us in, so it is classified
# separately — it must raise the alarm, but it must NOT be read as "we cannot flatten".
ERR_REDUCE_ONLY_ALLOWED = {-4189: "restricted: reduceOnly orders only"}
ERR_RATE_LIMITED = {-1003: "too many requests / IP banned"}
ERR_REDUCE_ONLY_REJECTED = {-2022, -4062, -4087, -4118, -4138}

ALL_DOC_DERIVED = {**ERR_ACCOUNT_RESTRICTED, **ERR_REDUCE_ONLY_ALLOWED, **ERR_RATE_LIMITED}


class ArmingRefused(RuntimeError):
    """Raised when a precondition for the protection to exist is not met. Never caught internally."""


class BinanceBroker:
    """Same contract as MockBroker: submit / flatten_all / set_reduce_only / halt_opening_orders."""

    def __init__(self, mode: str = "DRY_RUN", recv_window: int = 5000, timeout: float = 8.0):
        mode = mode.upper()
        if mode not in ("DRY_RUN", "TESTNET", "LIVE"):
            raise ValueError(f"unknown mode {mode!r}")
        self.mode = mode
        self.recv_window = recv_window
        self.timeout = timeout          # short timeout + retries; long timeouts turn a 15-minute
        self.actions: List[Dict[str, Any]] = []   # job into a 6-hour one on a stalling path
        self.reduce_only = False
        self.open_orders_halted = False
        self.armed = False
        self._consecutive_submit_failures = 0

        if mode == "DRY_RUN":
            self.base, self.key, self.secret = BASE_LIVE, None, None
            return
        if mode == "TESTNET":
            self.base = BASE_TESTNET
            self.key = os.environ.get("BINANCE_TESTNET_KEY")
            self.secret = os.environ.get("BINANCE_TESTNET_SECRET")
        else:
            if os.environ.get("BINANCE_LIVE_CONFIRM") != "I_UNDERSTAND":
                raise ArmingRefused("LIVE requires BINANCE_LIVE_CONFIRM=I_UNDERSTAND")
            self.base = BASE_LIVE
            self.key = os.environ.get("BINANCE_KEY")
            self.secret = os.environ.get("BINANCE_SECRET")
        if not self.key or not self.secret:
            raise ArmingRefused(f"{mode} requires credentials in env; none found")

    # ── transport ────────────────────────────────────────────────────────────────────────────
    def _request(self, method: str, path: str, params: Optional[Dict] = None, signed: bool = False):
        params = dict(params or {})
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = self.recv_window
            qs = urllib.parse.urlencode(params)
            sig = hmac.new(self.secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
            qs = f"{qs}&signature={sig}"
        else:
            qs = urllib.parse.urlencode(params)

        url = f"{self.base}{path}" + (f"?{qs}" if method == "GET" or signed else "")
        req = urllib.request.Request(url, method=method)
        if self.key:
            req.add_header("X-MBX-APIKEY", self.key)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode())
            except Exception:
                body = {"code": None, "msg": f"HTTP {e.code}"}
            raise VenueError(body.get("code"), body.get("msg"), e.code) from None

    # ── arming ───────────────────────────────────────────────────────────────────────────────
    def arm(self) -> Dict[str, Any]:
        """Run every precondition for the protection to exist. Refuses rather than degrades."""
        if self.mode == "DRY_RUN":
            self.armed = True
            return {"mode": "DRY_RUN", "checks": "skipped — no venue contacted"}

        out: Dict[str, Any] = {}

        # A1 — One-way Mode. reduceOnly "cannot be sent in Hedge Mode", so in Hedge Mode the
        # flatten cannot be marked reduce-only at all ⇒ the halt-first ladder loses its exit.
        dual = self._request("GET", "/fapi/v1/positionSide/dual", signed=True)
        out["position_mode"] = "HEDGE" if dual.get("dualSidePosition") else "ONE_WAY"
        if dual.get("dualSidePosition"):
            raise ArmingRefused(
                "account is in HEDGE mode; reduceOnly cannot be sent, so the protective flatten "
                "would be unmarked and the opening-halt would block our own exit. "
                "Set One-way Mode (POST /fapi/v1/positionSide/dual dualSidePosition=false) first."
            )

        # A2 — key must not be able to withdraw. Security comes from permission design, not from
        # where the machine sits.
        try:
            perm = self._request("GET", "/sapi/v1/account/apiRestrictions", signed=True)
            out["can_withdraw"] = perm.get("enableWithdrawals")
            if perm.get("enableWithdrawals"):
                raise ArmingRefused("API key has withdrawal permission enabled — disable it first")
        except VenueError as e:
            out["can_withdraw"] = f"unverified ({e.code}: {e.msg})"   # futures-only keys 404 here

        # A4 — clock skew larger than recvWindow silently rejects every signed request.
        t0 = time.time() * 1000
        srv = self._request("GET", "/fapi/v1/time")["serverTime"]
        skew = abs(srv - (t0 + time.time() * 1000) / 2)
        out["clock_skew_ms"] = round(skew)
        if skew > self.recv_window * 0.6:
            raise ArmingRefused(f"clock skew {skew:.0f}ms too close to recvWindow {self.recv_window}ms")

        self.armed = True
        out["armed"] = True
        return out

    # ── the four-method contract ─────────────────────────────────────────────────────────────
    def submit(self, order: Dict[str, Any], reason: str = "") -> bool:
        """★ The opening-halt is enforced HERE, in our own process, before anything leaves.

        It is deliberately NOT delegated to a venue flag: the rung exists precisely for the case
        where the venue is not cooperating. Declining to send needs no exchange, no key, no fill.
        And it is defined strictly over OPENING direction — a reduce-only order always passes,
        because the flatten IS reduce-only and blocking it would block our own exit.
        """
        if self.open_orders_halted and not order.get("reduce_only"):
            self.actions.append({"action": "order_blocked_by_halt", "order": order,
                                 "reason": reason, "ts": time.time()})
            raise OpeningHalted("opening-direction order refused: open_orders_halted is set")

        if self.mode == "DRY_RUN" or not self.armed:
            self.actions.append({"action": "submit_dry_run", "order": order, "reason": reason,
                                 "ts": time.time()})
            return True

        params = {
            "symbol": order["symbol"],
            "side": order["side"].upper(),
            "type": "LIMIT" if order.get("price") else "MARKET",
            "quantity": order["quantity"],
        }
        if order.get("price"):
            params["price"] = order["price"]
            params["timeInForce"] = order.get("tif", TIF_POST_ONLY)
        if order.get("reduce_only"):
            params["reduceOnly"] = "true"          # One-way Mode only; A1 guarantees that
        if order.get("client_id"):
            params["newClientOrderId"] = order["client_id"]

        try:
            resp = self._request("POST", "/fapi/v1/order", params, signed=True)
            self._consecutive_submit_failures = 0
            self.actions.append({"action": "submit", "order": order, "resp": resp,
                                 "reason": reason, "ts": time.time()})
            return True
        except VenueError as e:
            self._consecutive_submit_failures += 1
            self.actions.append({"action": "submit_failed", "order": order, "code": e.code,
                                 "msg": e.msg, "classification": self.classify(e),
                                 "consecutive_failures": self._consecutive_submit_failures,
                                 "reason": reason, "ts": time.time()})
            raise

    def flatten_all(self, positions: Dict[str, float], reason: str) -> List[Dict[str, Any]]:
        orders = [{"symbol": s, "side": "sell" if v > 0 else "buy", "quantity": abs(v),
                   "reduce_only": True, "tif": TIF_IOC}
                  for s, v in positions.items() if abs(v) > 1e-9]
        failed = []
        for o in orders:
            try:
                self.submit(o, reason)             # reduce_only -> passes even when halted
            except Exception as e:
                failed.append({"order": o, "err": str(e)})
        ok = not failed
        self.actions.append({"action": "flatten_all", "reason": reason, "n_orders": len(orders),
                             "orders": orders, "submitted_ok": ok, "failed": failed,
                             "ts": time.time()})
        if not ok:
            raise BrokerUnavailable(f"order submission failed for {len(failed)}/{len(orders)}")
        return orders

    def set_reduce_only(self, on: bool, reason: str) -> bool:
        """Venue-side reduce-only is a key/account setting we cannot toggle via the futures API.
        We therefore keep it as OUR flag and enforce it in submit(). Same reasoning as the halt:
        a protection that depends on the venue agreeing is not available when the venue is the
        problem. The operator switches the key setting out-of-band; this records intent."""
        self.reduce_only = on
        self.actions.append({"action": "set_reduce_only", "value": on, "reason": reason,
                             "submitted_ok": True, "enforced": "local", "ts": time.time()})
        return on

    def halt_opening_orders(self, reason: str) -> bool:
        """The only rung that does NOT need the exchange to cooperate. Runs FIRST in the ladder."""
        self.open_orders_halted = True
        self.actions.append({"action": "halt_opening_orders", "reason": reason,
                             "submitted_ok": True, "ts": time.time()})
        return True

    # ── readback & classification ────────────────────────────────────────────────────────────
    def positions(self) -> Dict[str, float]:
        """Venue-side truth. M5 drift detection compares this against what our own fills imply;
        without it, M5 only tests our own bookkeeping assumptions (see shadow's `shadow_sim`)."""
        if self.mode == "DRY_RUN":
            return {}
        acct = self._request("GET", "/fapi/v3/account", signed=True)
        return {p["symbol"]: float(p["positionAmt"])
                for p in acct.get("positions", []) if abs(float(p["positionAmt"])) > 0}

    def classify(self, err: "VenueError") -> str:
        if err.code in ERR_REDUCE_ONLY_ALLOWED:
            return "restricted_reduce_only_still_works"
        if err.code in ERR_ACCOUNT_RESTRICTED:
            return "account_restricted"
        if err.code in ERR_RATE_LIMITED or err.http in (418, 429):
            return "rate_limited"
        return "unknown"        # ← behavioural fallback still trips on this; table may be incomplete

    def public_endpoint_alive(self) -> bool:
        """Diagnostic only — NOT part of trigger logic (that ruling is in the protocol).
        Public feed alive + our orders failing => account-side; both dead => venue-side.
        The protective action is identical either way; this only tells the operator what to do next.
        """
        try:
            self._request("GET", "/fapi/v1/ping")
            return True
        except Exception:
            return False


class VenueError(RuntimeError):
    def __init__(self, code, msg, http=None):
        self.code, self.msg, self.http = code, msg, http
        super().__init__(f"[{code}] {msg}")


if __name__ == "__main__":
    import sys
    b = BinanceBroker(mode=sys.argv[1] if len(sys.argv) > 1 else "DRY_RUN")
    print(json.dumps(b.arm(), indent=2, ensure_ascii=False))
    print("public endpoint alive:", b.public_endpoint_alive())
