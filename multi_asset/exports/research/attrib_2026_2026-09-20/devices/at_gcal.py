#!/usr/bin/env python3
"""at_gcal.py — states, from THIS stream's own code path, which denominator and which anchor population the
g of `docs/RESULT_attribution_2026_vs_history_2026-09-20.md` uses, and proves it on the same path files.

Asked for by the coordinator on 2026-09-20 to reconcile the attribution stream's HIST g = +0.073 against a
recomputation that gave +0.043. Counterpart: the baseline-table stream's `devices/bt_g_convention.py`
(44cfecf2…, note `receipts/G_CONVENTION_reconciliation_2026-09-20.md`, commit ddee744fd).

WHAT THIS STREAM USES (read off at_control.py L47–L61, not asserted from memory):
    den   = GM * Z["nav0"]          GM = 2.0   ⇒ price / funding_paid / fee are each 1e4·X / (2 · NAV(A))
    g     = 1e4 * (Z["navm1"]/Z["navm0"] - 1.0) / GM
  ⇒ the denominator is the **TARGET gross** = 2 × the NAV at that anchor's own window start. It is NOT the
    window's realised gross `gross0`. On this run `navm0 == nav0` bitwise (the UNAVAILABLE rule never bit),
    so the NAV-return form and the component form share one denominator and the identity
    g = price − funding_paid − fee − unknown holds per anchor.
  Population: `s[k][m].mean()` (at_control.py) and `L1[k][mask].mean()` (at_attrib.py) over a mask that is a
    PURE TIME FILTER (`at_lib.period_mask`) ⇒ the arithmetic mean over **every anchor in the window**, with
    hold / halt / per-name-stop / zero-gross anchors all kept. The bootstrap uses the same convention:
    `at_lib.day_aggregate` sums per-anchor values and counts anchors, so Σ(day sums)/Σ(day counts) is that
    same unweighted per-anchor mean.

A NOTE ON ONE POPULATION VARIANT THAT IS EASY TO POSE WRONGLY. With 32 fill paths, "drop the halted anchors"
has two shapes. Dropping an anchor from ALL paths because ANY path halted there removes 21 HIST anchors that
most paths traded normally, and those anchors happen to average +11.4 bps (they follow a −4 % day stop, so the
book is small while the market rebounds) ⇒ +0.0292, which says nothing about the denominator question. The
path-consistent variant — each path drops its OWN halted anchors, then average across paths — gives +0.0730.
This device reports both and labels which one is meaningful.

usage: python at_gcal.py <ENV_WHITELIST_CSV> <OUT_DIR>
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import at_lib as L

T0 = time.time()
ENV_OK = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{L.ROOT}/receipts"
chk = L.Checks(T0)
rec = L.rec_head("at_gcal.py", sys.argv)
rec["purpose"] = "state and prove this stream's g denominator and anchor population (coordinator request 2026-09-20)"
chk("env.whitelist", not sorted(set(rec["env"]) - ENV_OK), {"extra": sorted(set(rec["env"]) - ENV_OK)})
rec["inputs"] = L.verify_pins(chk, ["AGG_A0"])

paths = sorted(f for f in os.listdir(L.RUN_A0) if f.startswith("PATH_") and f.endswith(".npz"))
G, H, S, T, R0, HD = [], [], [], [], [], []
for f in paths:
    Z = np.load(f"{L.RUN_A0}/{f}", allow_pickle=True)
    G.append(1e4 * (Z["navm1"] / Z["navm0"] - 1.0) / L.GM)          # ← at_control.py L49 + L61, verbatim
    H.append((Z["status"] == 1).astype(float))
    HD.append((Z["status"] == 2).astype(float))
    S.append((Z["n_stop_events"] > 0).astype(float))
    T.append((Z["gross0"] > 0).astype(float))
    with np.errstate(all="ignore"):
        R0.append(np.where(Z["gross0"] > 0, Z["gross0"] / (L.GM * Z["nav0"]), np.nan))
    if f == paths[0]:
        A = Z["A"].astype(np.int64)
        chk("navm0_equals_nav0_bitwise", bool(np.array_equal(Z["navm0"].view(np.uint64), Z["nav0"].view(np.uint64))),
            {"note": "⇒ the NAV-return form and the component form share the denominator 2·NAV(A)"})
G = np.stack(G); H = np.stack(H); S = np.stack(S); T = np.stack(T); HD = np.stack(HD)
g = G.mean(0); hfrac = H.mean(0); sfrac = S.mean(0); tfrac = T.mean(0); dfrac = HD.mean(0)
r0 = np.nanmean(np.stack(R0), 0)

out = {"convention": {
    "denominator": "TARGET gross = gross_mult · NAV(A) with gross_mult = 2.0 (at_control.py L47 `den = GM * Z[\"nav0\"]`, L61 `s[\"g\"] = 1e4 * s[\"r\"] / GM`)",
    "is_realised_gross0": False,
    "population": "every anchor in the time window; arithmetic mean; hold / halt / per-name-stop / zero-gross anchors all kept (at_control.py `s[k][m].mean()`, at_attrib.py `L1[k][mask].mean()`, mask = at_lib.period_mask = pure time filter)",
    "bootstrap": "at_lib.day_aggregate sums per-anchor values and counts anchors ⇒ Σ(day sums)/Σ(day counts) = the same unweighted per-anchor mean",
    "identity": "g = price − funding_paid − fee − unknown_excluded, every term over the same 2·NAV(A)"},
    "windows": {}}
for name, lo, hi, _ in L.PERIODS:
    m = L.period_mask(A, lo, hi)
    if not m.any():
        continue
    per_path_drop_own_halts = [float(G[i][m & (H[i] == 0)].mean()) for i in range(len(paths))]
    out["windows"][name] = {
        "n_anchors": int(m.sum()),
        "g_AS_PUBLISHED_target_gross_all_anchors": float(g[m].mean()),
        "population_counts": {"hold_any_path": int((m & (dfrac > 0)).sum()),
                              "halt_any_path": int((m & (hfrac > 0)).sum()),
                              "halt_all_paths": int((m & (hfrac == 1)).sum()),
                              "any_per_name_stop": int((m & (sfrac > 0)).sum()),
                              "zero_gross_any_path": int((m & (tfrac < 1)).sum())},
        "sensitivity_MEANINGFUL_per_path_drop_own_halts": float(np.mean(per_path_drop_own_halts)),
        "sensitivity_ILLPOSED_drop_anchor_if_any_path_halted": float(g[m & (hfrac == 0)].mean()),
        "sensitivity_traded_only_gross0_gt_0_on_every_path": float(g[m & (tfrac == 1)].mean()),
        "mean_realised_over_target_gross": float(np.nanmean(r0[m])),
    }
hist = out["windows"]["HIST"]
chk("HIST.g_is_the_published_number", abs(hist["g_AS_PUBLISHED_target_gross_all_anchors"] - 0.0728) < 5e-4,
    {"g": hist["g_AS_PUBLISHED_target_gross_all_anchors"], "doc_says": "+0.073"})
chk("HIST.population_is_not_the_driver", abs(hist["sensitivity_MEANINGFUL_per_path_drop_own_halts"] - hist["g_AS_PUBLISHED_target_gross_all_anchors"]) < 5e-4,
    {"all_anchors": hist["g_AS_PUBLISHED_target_gross_all_anchors"], "per_path_drop_own_halts": hist["sensitivity_MEANINGFUL_per_path_drop_own_halts"]})
chk("HIST.realised_and_target_gross_levels_agree", abs(hist["mean_realised_over_target_gross"] - 1.0) < 0.01,
    {"mean_gross0_over_2NAV": hist["mean_realised_over_target_gross"],
     "note": "the two conventions differ by the averaging of a ratio with a moving denominator, not by the gross level"})

p = f"{OUT}/AT_G_CONVENTION.json"
with open(p + ".tmp", "w") as f:
    json.dump(out, f, indent=1, default=str)
os.replace(p + ".tmp", p)
rec["outputs"] = {"g_convention": {"path": p, "sha256": L.sha(p)}}
rec["headline"] = {k: {"n": v["n_anchors"], "g": round(v["g_AS_PUBLISHED_target_gross_all_anchors"], 4)}
                   for k, v in out["windows"].items()}
v = L.write_receipt(rec, chk, f"{OUT}/AT_G_CONVENTION_RECEIPT.json", {"runtime_s": round(time.time() - T0, 1)})
print("AT_G_CONVENTION VERDICT=%s checks=%d failed=%s | HIST g = %+.4f (target gross, every anchor)"
      % (v, len(chk.rows), chk.fails, hist["g_AS_PUBLISHED_target_gross_all_anchors"]), flush=True)
sys.exit(0 if v == "PASS" else 3)
