"""Venue error-code table for the "account restricted" stop-loss (§4-5) — and why it CANNOT be complete.

★ READ THIS BEFORE TRUSTING THE TABLE BELOW.

We have no account, so not one of these codes has been observed. Every row is copied from public
API documentation, and exchange docs are notoriously incomplete for exactly this class of state:
risk/compliance-triggered restrictions are rarely enumerated publicly. **A whitelist that cannot be
measured is, by construction, incomplete.**

⇒ Therefore the enumeration is NOT the protection. The protection is BEHAVIOURAL:

    PRIMARY (the real guard)   order submission failing persistently -- N consecutive attempts or
                               M consecutive anchors -- triggers the account-anomaly path
                               REGARDLESS of what came back, including unknown codes and timeouts.
    SECONDARY (an optimisation) a hit on a known code triggers IMMEDIATELY, without waiting for N.

**The asymmetry that makes this safe: if the table hits, we are fast; if the table misses, we are
merely slower. It can never fail open.** Anyone who later notices the table is incomplete should be
able to see, right here, that its incompleteness was designed around rather than overlooked.

★ CAN WE DISTINGUISH "ACCOUNT RESTRICTED" FROM "VENUE OUTAGE"? Honestly: not reliably, and not at
all without an account. Both present as "our orders stop working". The correct responses differ
(an outage is waited out; a restriction means stop and investigate), but since we cannot tell them
apart from the outside, BOTH ROUTE TO THE SAME CONSERVATIVE PATH: flatten + reduce-only. We do not
invent a discriminator we cannot validate. If the venue later gives us a code we can trust, the
fast path uses it -- but the behavioural fallback never depends on that.

Verification status vocabulary:
    doc-derived, UNVERIFIED   copied from public docs; never observed by us
    observed                  seen on a real account (none yet, and none until the user opens one)
"""

# (venue, code, meaning, action, source, verification)
VENUE_ERROR_CODES = [
    # --- Hyperliquid: documented error strings on the exchange endpoint ---
    dict(venue="hyperliquid", code="Insufficient margin", restricted=False,
         meaning="margin shortfall on this order", action="reduce size (not a restriction)",
         source="HL API docs", verification="doc-derived, UNVERIFIED"),
    dict(venue="hyperliquid", code="User or API Wallet does not exist", restricted=True,
         meaning="key/wallet not recognised — revoked or wrong environment",
         action="account-anomaly path", source="HL API docs", verification="doc-derived, UNVERIFIED"),
    dict(venue="hyperliquid", code="Order rejected: reduce only", restricted=True,
         meaning="account already in reduce-only — someone or something restricted it",
         action="account-anomaly path", source="HL API docs", verification="doc-derived, UNVERIFIED"),
    dict(venue="hyperliquid", code="Too many requests", restricted=False,
         meaning="rate limited (F13 cold-start budget)",
         action="back off; NOT a restriction", source="HL API docs",
         verification="doc-derived, UNVERIFIED"),
    # --- generic HTTP-level signatures worth treating as restriction-suspicious ---
    dict(venue="*", code="HTTP 401", restricted=True, meaning="auth rejected",
         action="account-anomaly path", source="HTTP", verification="doc-derived, UNVERIFIED"),
    dict(venue="*", code="HTTP 403", restricted=True,
         meaning="forbidden — geo/compliance/account restriction",
         action="account-anomaly path", source="HTTP", verification="doc-derived, UNVERIFIED"),
    dict(venue="*", code="HTTP 418", restricted=True, meaning="banned after repeated violations",
         action="account-anomaly path", source="HTTP", verification="doc-derived, UNVERIFIED"),
    dict(venue="*", code="HTTP 429", restricted=False, meaning="rate limited",
         action="back off; NOT a restriction", source="HTTP", verification="doc-derived, UNVERIFIED"),
    dict(venue="*", code="HTTP 503", restricted=False, meaning="venue unavailable",
         action="outage path (same conservative action)", source="HTTP",
         verification="doc-derived, UNVERIFIED"),
]

RESTRICTED_CODES = {(r["venue"], r["code"]) for r in VENUE_ERROR_CODES if r["restricted"]}

COMPLETENESS_DISCLAIMER = (
    "This table CANNOT be complete: no code in it has been observed, because there is no account. "
    "Completeness is not provided by the table but by the behavioural fallback (N consecutive "
    "failed attempts / M consecutive anchors triggers regardless of the code, including unknown "
    "codes and timeouts). A table hit only makes the trigger FASTER; a table miss makes it SLOWER, "
    "never absent."
)


def is_restricted_code(venue: str, code: str) -> bool:
    """Fast path only. A False here means 'not a known restriction code', NEVER 'account is fine'."""
    return (venue, code) in RESTRICTED_CODES or ("*", code) in RESTRICTED_CODES


def summary():
    return {"n_rows": len(VENUE_ERROR_CODES),
            "n_restricted": len(RESTRICTED_CODES),
            "n_observed": sum(1 for r in VENUE_ERROR_CODES if r["verification"] == "observed"),
            "completeness": COMPLETENESS_DISCLAIMER,
            "distinguishes_restriction_from_outage": False,
            "distinguish_note": ("we cannot distinguish them from outside and do not pretend to; "
                                 "both route to flatten + reduce-only"),
            "rows": VENUE_ERROR_CODES}


if __name__ == "__main__":
    import json
    print(json.dumps(summary(), indent=1))
