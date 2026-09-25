"""fa_rn8verdict.py — apply AMENDMENT 2's frozen criteria MECHANICALLY to the two seeds' readouts and print the
verdict line. PREREG docs/PREREG_step1_rn8_clamp_2026-09-25.md, AMENDMENT 2 (commit 1ea8644ab).

The point of a separate device: the lead stated an expectation ("I expect it is still REJECT"). An expectation is not
a result. This device takes the two receipts and evaluates the clauses as written, with no judgement of mine in the
path, and prints which clauses fired.

AMENDMENT 2 criteria, as frozen:
  RECOMMEND_TO_USER  both seeds: (1) fullwin dbar > 0 AND its CI lower bound > 0;
                                 (2) pre2026 AND 2026 point estimates BOTH positive;
                                 (3) fullwin net channel > 0.
  REJECT             any seed: fullwin dbar <= 0, OR fullwin net channel <= 0.
  UNDECIDED          otherwise. Segments of opposite sign  -> write the judge-vs-live note.
                                Seeds of opposite sign     -> write the seed-reversal note.

The net channel is evaluated under BOTH literal readings (AMENDMENT 2 section B records the conflict): the confirmed
`price - funding_paid` is the operative one; `price + funding_paid` is printed beside it so the other reading needs no
re-run. Which CI bound is used is stated explicitly: ci95_bps, matching the earlier reading.

usage: ... fa_rn8verdict.py WL <read_s42.json> <read_s2027.json> <out.json>
"""
import os, sys, json, hashlib, time

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
R42, R2027, OUT = sys.argv[2], sys.argv[3], sys.argv[4]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


D = {"s42": json.load(open(R42)), "s2027": json.load(open(R2027))}
rec = {"device": "fa_rn8verdict.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "prereg": {"path": "docs/PREREG_step1_rn8_clamp_2026-09-25.md", "amendment_2": "1ea8644ab"},
       "inputs": {"s42": {"path": R42, "sha256": sha(R42)}, "s2027": {"path": R2027, "sha256": sha(R2027)}},
       "ci_bound_used": "ci95_bps lower bound", "per_seed": {}}

facts = {}
for k, d in D.items():
    fw = d["segments"]["fullwin"]; cf = d["channels"]["fullwin"]
    f = {"fullwin_dbar": fw["mean_bps_per_day"], "fullwin_ci95": fw["boot"]["ci95_bps"],
         "fullwin_ci95_lower": fw["boot"]["ci95_bps"][0],
         "pre2026_dbar": d["segments"]["pre2026"]["mean_bps_per_day"],
         "y2026_dbar": d["segments"]["2026"]["mean_bps_per_day"],
         "fullwin_net_confirmed_minus": cf["NET_price_minus_funding_paid"],
         "fullwin_net_literal_plus": cf["ALT_price_plus_funding_paid"],
         "fullwin_dPrice": cf["price"]["delta"], "fullwin_dFundPaid": cf["funding_paid"]["delta"]}
    f["c1_dbar_gt0_and_lower_gt0"] = bool(f["fullwin_dbar"] > 0 and f["fullwin_ci95_lower"] > 0)
    f["c2_both_segments_positive"] = bool(f["pre2026_dbar"] > 0 and f["y2026_dbar"] > 0)
    f["c3_net_gt0_confirmed"] = bool(f["fullwin_net_confirmed_minus"] > 0)
    f["c3_net_gt0_literal_plus"] = bool(f["fullwin_net_literal_plus"] > 0)
    f["reject_clause_dbar"] = bool(f["fullwin_dbar"] <= 0)
    f["reject_clause_net_confirmed"] = bool(f["fullwin_net_confirmed_minus"] <= 0)
    f["reject_clause_net_literal_plus"] = bool(f["fullwin_net_literal_plus"] <= 0)
    f["segments_opposite_sign"] = bool((f["pre2026_dbar"] > 0) != (f["y2026_dbar"] > 0))
    facts[k] = f
    rec["per_seed"][k] = f

seeds = ("s42", "s2027")


def verdict(net_key_ok, net_key_reject):
    fired = []
    for k in seeds:
        if facts[k]["reject_clause_dbar"]:
            fired.append(f"{k}: fullwin dbar {facts[k]['fullwin_dbar']:+.4f} <= 0")
        if facts[k][net_key_reject]:
            fired.append(f"{k}: fullwin net {facts[k]['fullwin_net_confirmed_minus' if net_key_reject=='reject_clause_net_confirmed' else 'fullwin_net_literal_plus']:+.4f} <= 0")
    if fired:
        return "REJECT", fired
    if all(facts[k]["c1_dbar_gt0_and_lower_gt0"] and facts[k]["c2_both_segments_positive"] and facts[k][net_key_ok] for k in seeds):
        return "RECOMMEND_TO_USER", ["all three conditions hold on both seeds"]
    return "UNDECIDED", ["no REJECT clause fired and RECOMMEND conditions not all met"]

v_conf, why_conf = verdict("c3_net_gt0_confirmed", "reject_clause_net_confirmed")
v_alt, why_alt = verdict("c3_net_gt0_literal_plus", "reject_clause_net_literal_plus")

notes = []
if any(facts[k]["segments_opposite_sign"] for k in seeds):
    notes.append("判据窗与实盘窗方向相反 (" + ", ".join(k for k in seeds if facts[k]["segments_opposite_sign"]) + ")")
if (facts["s42"]["fullwin_dbar"] > 0) != (facts["s2027"]["fullwin_dbar"] > 0):
    notes.append("又一次按种子翻转 (fullwin dbar)")

rec["verdict_operative_confirmed_sign"] = {"verdict": v_conf, "clauses_fired": why_conf,
                                           "net_definition": "Dprice - Dfunding_paid (lead-confirmed intent)"}
rec["verdict_alternate_literal_sign"] = {"verdict": v_alt, "clauses_fired": why_alt,
                                         "net_definition": "Dprice + Dfunding_paid (literal wording of AMENDMENT 2)"}
rec["mandatory_notes"] = notes
json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
assert os.path.exists(OUT), "receipt not written"

print("FA_RN8VERDICT AMD2 VERDICT=%s (operative, net=Dprice-DfundPaid) | alternate_literal_plus=%s" % (v_conf, v_alt), flush=True)
for c in why_conf:
    print("   clause: " + c, flush=True)
for n in notes:
    print("   NOTE: " + n, flush=True)
for k in seeds:
    f = facts[k]
    print("   %-6s fullwin dbar=%+8.4f ci95=[%+.3f, %+.3f] | pre2026=%+8.4f 2026=%+8.4f | net(-)=%+.4f net(+)=%+.4f"
          % (k, f["fullwin_dbar"], f["fullwin_ci95"][0], f["fullwin_ci95"][1], f["pre2026_dbar"], f["y2026_dbar"],
             f["fullwin_net_confirmed_minus"], f["fullwin_net_literal_plus"]), flush=True)
