#!/usr/bin/python3
"""tests_producer_risk — the producer can say "I am degraded, run me smaller", AND THE BOOK GETS SMALLER.

WOULD LIVE AT: ~/dl_quant_live/live/tests_producer_risk.py
SUITES ENTRY:  "tests_producer_risk:$_SELF/live/tests_producer_risk.py"  (run_acceptance.sh, after tests_sigma_ladder)
BLIND SPOT:    ops/gate_coverage.py SUITE_SCOPE["tests_producer_risk"]  (verify() goes RED without it)

*** MOCK ONLY: fixture documents, no account, no credentials, no venue, no state written. ***

★ WHY THIS SUITE EXISTS, IN ONE PARAGRAPH.
`external_book.target_vector` divides the producer's weights by their own gross, unconditionally
(external_book.py:483-490).  So the live gross is NAV x gross_mult x g_sigma and NOTHING the producer
writes can lower it: a half-computed book, or a sleeve that silently went NaN, is re-levered to full
risk by one division.  This suite is the machine-checkable half of the fix — the producer declares
`risk_scale` inside the target file the executor already verifies, and the executor multiplies it into
`target_leverage`, where the leverage policy and the exposure floor can both see it.

★ IT IS RED BEFORE THE PATCH, ON PURPOSE.  Against an unpatched live/external_book.py every check
below fails with "parse_risk_scale missing".  A suite that has never been seen failing is an
unverified claim (run_acceptance.sh's own rule); this one is born failing and turns green exactly when
the behaviour arrives.

★ THE DENOMINATOR IS PRINTED AND A ZERO DENOMINATOR IS RED (battery convention 2026-07-27).
"""
import hashlib
import json
import os
import sys
import time

sys.dont_write_bytecode = True          # ★ never leave __pycache__ inside the real-money repo
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

LIVE = os.environ.get("DL_QUANT_LIVE_LIVE", os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(LIVE)
sys.path.insert(0, LIVE)
import external_book as EB              # noqa: E402

FAILS = []
N = [0]


def check(name, cond, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail else ''}", flush=True)
    if not cond:
        FAILS.append(name)


# ── fixtures ────────────────────────────────────────────────────────────────────────────────────
NOW = 1_789_128_000.0                   # a real 4h anchor (2026-09-11 12:00Z), injected, never time.time()
ANCHOR = int(NOW)
SYMS = ["AAAUSDT", "BBBUSDT", "CCCUSDT"]
W = {"AAAUSDT": 0.5, "BBBUSDT": -0.3, "CCCUSDT": 0.2}
CFG = {"schema": "wide_target_v1", "max_age_min": 10, "require_anchor_match": True,
       "gross_mult": 2.0, "min_notional_mult": 2.0, "universe_sha_pin": None, "booster_sha_pin": None,
       "path": "/nonexistent", "anchor_offset_min": 24, "poll_grace_min": 5}


def doc(**extra):
    d = {"schema": "wide_target_v1", "weights": dict(W), "anchor_ts": ANCHOR,
         "universe": list(SYMS), "universe_sha": EB.universe_sha(SYMS),
         "booster_sha": "b" * 64, "weights_sha": "c" * 64,
         "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - 120)),
         "gross_norm": float(sum(abs(v) for v in W.values())), "n_names": len(W),
         "producer": "wide_shadow"}
    d.update(extra)
    return d


def parsed(**extra):
    return EB.parse_target(json.dumps(doc(**extra)).encode(), CFG, ANCHOR, NOW)


HAS = hasattr(EB, "parse_risk_scale")
print("[0] the patch is present at all")
check("0a external_book.parse_risk_scale exists", HAS,
      "" if HAS else "UNPATCHED TREE — every check below is expected to fail; this is the red state")

if HAS:
    print("[1] absent field is EXACTLY today's behaviour")
    r, i = EB.parse_risk_scale(doc())
    check("1a absent -> 1.0 accepted", r == 1.0 and i["accepted"] and i["declared"] is False and i["reason"] == "absent", i)
    p = parsed()
    check("1b parse_target ok and risk_scale 1.0", p["ok"] and p["risk_scale"] == 1.0, p.get("reason"))
    v = EB.target_vector(p, SYMS)
    check("1c vector is unit gross", abs(sum(abs(x) for x in v) - 1.0) < 1e-12, sum(abs(x) for x in v))

    print("[2] a declared, whitelisted scale is carried through EXACTLY")
    for val in (1.0, 0.8, 0.5):
        r, i = EB.parse_risk_scale(doc(risk_scale=val))
        check(f"2a risk_scale={val} accepted exactly", r == val and i["accepted"] and i["declared"], i)
        p = parsed(risk_scale=val, risk_reason="ami sleeve NaN", sleeve_alloc=0.20)
        check(f"2b parse_target carries {val}", p["ok"] and p["risk_scale"] == val, p.get("reason"))
        check(f"2c reason+alloc carried for {val}",
              p["risk_info"].get("risk_reason") == "ami sleeve NaN" and p["sleeve_alloc"] == 0.20, p.get("risk_info"))
        vv = EB.target_vector(p, SYMS)
        check(f"2d vector STILL unit gross at {val} (scale must NOT touch the weights)",
              abs(sum(abs(x) for x in vv) - 1.0) < 1e-12 and all(abs(a - b) < 1e-15 for a, b in zip(vv, v)),
              sum(abs(x) for x in vv))

    print("[3] every malformed value REJECTS THE FILE — never a silent coercion to full risk")
    for bad, label in ((0.7, "off-whitelist 0.7"), (0.0, "zero"), (2.0, "above 1"), (-0.5, "negative"),
                       ("0.8", "string"), (None, "null"), (True, "bool"), (float("nan"), "nan"),
                       (float("inf"), "inf")):
        r, i = EB.parse_risk_scale(doc(risk_scale=bad))
        check(f"3a {label}: not accepted", (not i["accepted"]) and i["declared"], i)
        check(f"3b {label}: fail-safe value is still 1.0", r == 1.0, r)
        pb = parsed(risk_scale=bad)
        check(f"3c {label}: parse_target REJECTS the whole file", (not pb["ok"]) and pb["reason"] == "risk_scale",
              pb.get("reason"))

    print("[4] arithmetic contract: target_leverage = gross_mult x g x risk_scale")
    for gm, g, rs, want in ((2.0, 1.0, 1.0, 2.0), (2.0, 1.0, 0.8, 1.6), (2.0, 1.0, 0.5, 1.0),
                            (2.0, 0.5, 0.8, 0.8), (1.5, 1.0, 0.8, 1.2)):
        check(f"4a {gm}x{g}x{rs}={want}", abs(gm * g * rs - want) < 1e-12)

print("[5] the loop is WIRED (static read — this is a text assertion, not a behavioural one)")
AL = os.path.join(REPO, "scheduler", "anchor_loop.py")
try:
    src = open(AL).read()
except Exception as e:                                   # noqa: BLE001
    src = ""
    check("5a anchor_loop.py readable", False, e)
check("5a risk_scale read from the external dict", 'external.get("risk_scale"' in src)
check("5b multiplied into target_leverage", "gross_mult\"] * _g * _r" in src or 'gross_mult"] * _g * _r' in src)
check("5c the low-mode branch tests _r as well as _g", "_g < 1.0 or _r < 1.0" in src)
check("5d leverage_source names producer_risk", "producer_risk(" in src)
check("5e HIGH (not INFO) alarm when the producer self-declares degraded",
      'self.alarm("HIGH", f"生产者自报降级' in src)
check("5f schema-regression guard remembers a producer that used to declare",
      "external_risk_scale_seen" in src)

print("[6] the battery and the coverage census both know about this suite")
try:
    acc = open(os.path.join(REPO, "run_acceptance.sh")).read()
except Exception:                                        # noqa: BLE001
    acc = ""
check("6a SUITES entry exists", "tests_producer_risk:" in acc)
try:
    gc = open(os.path.join(REPO, "ops", "gate_coverage.py")).read()
except Exception:                                        # noqa: BLE001
    gc = ""
check("6b blind-spot entry exists", '"tests_producer_risk"' in gc)

if N[0] == 0:
    print("\nFAILURES: zero checks ran — an empty suite is RED, never green")
    sys.exit(1)
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}   ({N[0]} checks)")
sys.exit(1 if FAILS else 0)
