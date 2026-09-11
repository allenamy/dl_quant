"""Round-3 placebo report: family agreement + the re-judged table. Reads JUDGE_r3_placebo.json."""
import json, numpy as np, sys
R = "/workspace/uplift_2026-09-11/r3_placebo"
J = json.load(open(R + "/JUDGE_r3_placebo.json"))
FAMS = {"R": ["R1", "R2", "R3"], "RO": ["O1", "O2"], "T": ["T1", "T2", "T3"], "P_legacy": ["P1"]}
span = sys.argv[1] if len(sys.argv) > 1 else "FULL"
rows = [(k, v) for k, v in J.items() if v["span"] == span]
rows.sort(key=lambda kv: -kv[1].get("pooled_matched", {}).get("margin_net", -9e9))

print("=" * 150)
print("TURNOVER-MATCHED PLACEBO RE-JUDGE  |  span %s  |  statistic g = net_ex/gross_total (bps/anchor/unit gross)  |  post-warm (first 900 anchors dropped, E-0911-A)" % span)
print("=" * 150)
print("%-20s %5s | %8s %8s %7s %7s | %-4s %8s %8s %7s %6s | %8s %8s | %-30s"
      % ("arm", "n", "RE_net", "RE_gros", "RE_cost", "RE_turn", "fam", "NL_net", "NL_gros", "NL_cost", "c_rat",
         "mrg_net", "mrg_gros", "CI95 on paired margin (net)"))
for k, v in rows:
    re = v["real"]
    first = True
    for fam, tags in FAMS.items():
        have = [t for t in tags if t in v["nulls"]]
        if not have:
            continue
        g = np.mean([v["nulls"][t]["g"] for t in have])
        gg = np.mean([v["nulls"][t]["ggross"] for t in have])
        gc = np.mean([v["nulls"][t]["gcost"] for t in have])
        cr = gc / max(re["gcost"], 1e-12)
        mn = np.mean([v["nulls"][t]["margin_net"] for t in have])
        mg = np.mean([v["nulls"][t]["margin_gross"] for t in have])
        lo = np.mean([v["nulls"][t]["margin_net_CI95"][0] for t in have])
        hi = np.mean([v["nulls"][t]["margin_net_CI95"][1] for t in have])
        head = ("%-20s %5d | %+8.4f %+8.4f %7.4f %7.4f" % (v["arm"][:20], re["n"], re["g"], re["ggross"], re["gcost"], re["turn"])) if first else " " * 61
        print("%s | %-4s %+8.4f %+8.4f %7.4f %6.2f | %+8.4f %+8.4f | [%+0.3f,%+0.3f]"
              % (head, fam, g, gg, gc, cr, mn, mg, lo, hi))
        first = False
    pm = v.get("pooled_matched")
    if pm:
        print("%s | %-4s %+8.4f %+8.4f %7.4f %6.2f | %+8.4f %+8.4f | %s CI95[%+0.3f,%+0.3f] BONF12[%+0.3f,%+0.3f]"
              % (" " * 61, "ALL", pm["null_g"], pm["null_ggross"], pm["null_gcost"], pm["cost_ratio"],
                 pm["margin_net"], pm["margin_gross"], pm["verdict"], pm["CI95"][0], pm["CI95"][1],
                 pm["CI_BONF12"][0], pm["CI_BONF12"][1]))
    lb = v.get("legacy_bias")
    if lb and lb.get("matched_margin_net") is not None:
        print("%s   LEGACY-vs-MATCHED: permutation placebo margin %+0.4f, matched %+0.4f  =>  round-1/2 overstated the margin by %+0.4f bps (%.0f%%), legacy cost ratio %.1fx"
              % (" " * 61, lb["legacy_margin_net"], lb["matched_margin_net"], lb["bias_bps"],
                 100 * lb["bias_bps"] / max(abs(lb["matched_margin_net"]), 1e-9), lb["legacy_cost_ratio"]))
    print("-" * 150)

# family agreement
print()
print("FAMILY AGREEMENT (paired margin in NET g, span %s): do the independent null families give the same answer?" % span)
print("%-20s %9s %9s %9s | %9s %9s" % ("arm", "R", "RO", "T", "max spread", "pooled"))
for k, v in rows:
    m = {}
    for fam, tags in FAMS.items():
        if fam == "P_legacy": continue
        have = [t for t in tags if t in v["nulls"]]
        if have: m[fam] = np.mean([v["nulls"][t]["margin_net"] for t in have])
    if len(m) < 3: continue
    sp = max(m.values()) - min(m.values())
    print("%-20s %+9.4f %+9.4f %+9.4f | %9.4f %+9.4f"
          % (v["arm"][:20], m["R"], m["RO"], m["T"], sp, v["pooled_matched"]["margin_net"]))
