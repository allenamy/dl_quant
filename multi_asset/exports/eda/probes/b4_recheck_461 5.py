"""#22 — re-measure the 4.61 net-Sharpe anchor with CLEAN DL legs, at the current cost calibers.

★ WHY IT MATTERS: `4.61` is the closest historical anchor to the user's Sharpe >= 5 target
  ("funding_ema + M0 DL ACCEPTED, net-Sh 4.61"). But it predates the lookahead discovery and its DL
  component was the DIRTY king — so it belongs to the "supporting number is contaminated" class and
  has to be re-earned on a clean caliber before it can anchor anything.

★ SAME APPARATUS, ONE VARIABLE: `replay_fullhist.run_replay()` is called directly (not
  reimplemented), with the certified clean predictions passed through the `--king/--s2` parameters.
  `COST_BPS` is a module constant with no CLI flag, so it is monkey-patched on the module before
  each call — which is why the cost actually used is re-read OUT of the returned artifact and
  printed, rather than assumed to be what was set.

★ DOUBLE TARGET (prereg v1 §4 / cost rebuild 2026-08-04): the point estimate 3.63 must be reported,
  and the DEPLOYMENT reading is the CI upper bound 5.8 — clearing only the point bets on the
  kindness of an n=16 cost estimate. 1.9 is kept as the historical grid column that 4.61 itself
  was quoted at, so the comparison is like-for-like at that column and honest at the others.

★ WHAT THIS CANNOT SAY: the engine 4-leg book (king/s2/funding/size) is not bit-identical to
  whatever "factor-book" construction produced 4.61 in July. This measures the engine's canonical
  book across cost calibers with clean vs dirty DL legs; if the drop is large it bounds how much of
  4.61 could have survived, it does not reconstruct 4.61's exact assembly.
"""
import json
import sys

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
import torch  # noqa: E402

torch.backends.mkldnn.enabled = False
from engine import replay_fullhist as RF   # noqa: E402  the real thing, not a copy

ARMS = {
    "DIRTY DL (as 4.61 was measured)": (None, None),
    "CLEAN DL (certified 5-fold OOS)": ("/tmp/king_pred_newgen.npz", "/tmp/s2_pred_newgen.npz"),
}
COSTS = [1.9, 3.63, 5.8]
HIST_ANCHOR = 4.61

res = {}
for arm, (kp, sp) in ARMS.items():
    for c in COSTS:
        RF.COST_BPS = c
        RF._SRC, RF._SRC_KEY = None, None          # force a rebuild for the new pred paths
        out = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap",
                            panel=None, king=kp, s2=sp, verbose=False)
        used = out.get("cost_bps")
        assert abs(float(used) - c) < 1e-9, "artifact says cost %s but %s was set" % (used, c)
        res[(arm, c)] = out
        print("  %-34s cost=%-5s  avg net Sharpe = %6.2f   (per-year %s)"
              % (arm, c, out["avg_net_of_cost_sharpe"],
                 [out["per_year"][y]["net_of_cost_sharpe"] for y in sorted(out["per_year"])]),
              flush=True)

print("\n%-34s %10s %10s %10s" % ("arm", "@1.9", "@3.63", "@5.8 (gate)"))
print("-" * 68)
for arm in ARMS:
    print("%-34s %10.2f %10.2f %10.2f"
          % (arm, res[(arm, 1.9)]["avg_net_of_cost_sharpe"],
             res[(arm, 3.63)]["avg_net_of_cost_sharpe"],
             res[(arm, 5.8)]["avg_net_of_cost_sharpe"]))

print("\n=== VERDICT vs the historical anchor %.2f ===" % HIST_ANCHOR)
clean = res[("CLEAN DL (certified 5-fold OOS)", 3.63)]["avg_net_of_cost_sharpe"]
dirty = res[("DIRTY DL (as 4.61 was measured)", 3.63)]["avg_net_of_cost_sharpe"]
print("  clean @3.63 = %.2f ;  dirty @3.63 = %.2f ;  historical quote = %.2f" % (clean, dirty, HIST_ANCHOR))
if clean >= HIST_ANCHOR:
    print("  ⇒ 4.61 SURVIVES on a clean caliber: Sharpe>=5 has a measured historical anchor.")
elif clean >= 0.5 * HIST_ANCHOR:
    print("  ⇒ 4.61 PARTLY survives — the anchor is real but well below its quoted level.")
else:
    print("  ⇒ 4.61 DOES NOT SURVIVE. The closest historical anchor to Sharpe>=5 was carried by the")
    print("    contaminated DL leg ⇒ **the target has no clean historical precedent**, and its")
    print("    difficulty should be re-stated to the user as 'somewhere nobody has been' rather")
    print("    than 'back to where we once were'.")
json.dump({("%s@%s" % (a, c)): v for (a, c), v in res.items()},
          open("/mnt/storage/private/work_hsy/b4_causal_scratch/recheck_461.json", "w"),
          indent=1, default=float)
