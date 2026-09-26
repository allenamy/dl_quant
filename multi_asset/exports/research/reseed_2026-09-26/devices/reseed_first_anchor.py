#!/usr/bin/env python3
"""First-anchor acceptance after the seat-history re-seed (lead 2026-09-26: "live w3_raw equals the device-predicted new seats bitwise, or
within a declared tolerance; the target-layer change is reconciled with the expectation"). READ-ONLY. Criteria frozen here before install.

  (1) FILE, bitwise: the producer's file after anchor B (state/snap/B/leg_returns_live.json) == installed[k:] + k appended entries, with
      k == the anchors processed since the install (1 for the first anchor). The kept part must be BITWISE equal per leg.
  (2) SEATS: w3_pred = the frozen seat formula (reseed_leg_returns.seats, == shadow_loop_v3.py L784-L790) on that file's last `look`
      entries. Tolerances DECLARED from what the records store (bitwise is not measurable on a rounded record):
        regime_dash w3_raw (stored to 4 dp)            |w3_pred - w3_raw| <= 5e-5 + 1e-12 per leg
        target_combo/B.json w3_masked (round(x, 6))    round(masked(w3_pred), 6) == w3_masked EXACTLY (the combo's own mask + rounding,
                                                        combo_stage.py L285-L286 / L331)
  (3) TARGET LAYER: the counterfactual OLD seats = the same formula on (backup .pre_reseed file)[k:] + the same k appended entries — i.e.
      what the old history would have given at B. Both seat vectors go through news2's target build (d10_reseed_combo_impact.build_target,
      IMPORTED, the producer's L800-L822 form) on B's own prev_rec. Reported: sum|dw| (target gross is 1 by construction), flips, top 5.
      The expectation (D10_RESEED_COMBO_IMPACT.json, 28d9f7496) DECAYS anchor by anchor (8.9 % at 09-24 00Z → 3.3 % at 09-26 00Z: each
      new anchor adds one entry both histories share), so a later anchor is expected to show LESS change. CONSISTENT iff
      sum|dw| <= the expectation's max AND flips <= its max flips; otherwise OUTSIDE_EXPECTATION (named, for review). The value is
      printed beside the expectation's last value and trend.
Unknown is not zero: a missing record ⇒ UNDECIDED.
usage: ~/wide_shadow/venv/bin/python reseed_first_anchor.py --anchor B --build DIR --stamp UTCSTAMP [--state ~/wide_shadow/state]"""
import argparse, importlib.util, json, os, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
QR = os.path.expanduser("~/Desktop/quant_research")
D10 = f"{QR}/multi_asset/exports/research/news2_2026-09-23/devices/d10_reseed_combo_impact.py"
D10_EXP = f"{QR}/multi_asset/exports/research/news2_2026-09-23/receipts/d10_2026-09-25/D10_RESEED_COMBO_IMPACT.json"
DASH = os.path.expanduser("~/regime_dash/regime_dash.jsonl")
CFG = os.path.expanduser("~/wide_shadow/shadow_bundle/config.json")
LEGS = ("king", "rev24", "fund")


def mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--anchor", type=int, required=True); ap.add_argument("--build", required=True)
    ap.add_argument("--stamp", required=True); ap.add_argument("--state", default=os.path.expanduser("~/wide_shadow/state"))
    ap.add_argument("--old", default=None, help="the pre-install file (default: <state>/leg_returns_live.json.pre_reseed_<stamp>)"); a = ap.parse_args()
    RS = mod(os.path.join(HERE, "reseed_leg_returns.py"), "rs_dev"); D = mod(D10, "d10_combo")
    B = a.anchor; look = int(json.load(open(CFG))["params"]["msharpe_look"]); P = json.load(open(CFG))["params"]
    NW = len(json.load(open(CFG))["symbols_panel"])
    V = {}
    inst = RS.load_lr(os.path.join(a.build, "leg_returns_live.NEW.json"))
    old = RS.load_lr(a.old or os.path.join(a.state, f"leg_returns_live.json.pre_reseed_{a.stamp}"))
    snapf = os.path.join(a.state, "snap", str(B), "leg_returns_live.json")
    if not os.path.exists(snapf):
        print(f"UNDECIDED: no snapshot for {RS.u(B)}"); print("RESEED_FIRST_ANCHOR VERDICT=UNDECIDED"); return 2
    live = RS.load_lr(snapf); n = len(live["king"])
    k = next((k for k in range(0, 13) if all((live[l][:n - k] if k else live[l]) == inst[l][k:] for l in LEGS)), None)
    print(f"(1) file after {RS.u(B)}: kept part == installed[k:] bitwise with k={k}")
    V["file"] = "PASS" if k == 1 else (f"RED (the file does not continue the installed series)" if k is None else f"UNDECIDED (k={k} appends since install, expected 1)")
    if k is None:
        print(f"RESEED_FIRST_ANCHOR VERDICT=RED file={V['file']}"); return 1
    app = {l: live[l][n - k:] for l in LEGS}
    w_new = RS.seats({l: live[l][-look:] for l in LEGS})
    old_cont = {l: (old[l] + app[l])[-look:] for l in LEGS}
    w_old = RS.seats(old_cont)
    print(f"    appended entries: {[[app[l][i] for l in LEGS] for i in range(k)]}")
    print(f"(2) w3_pred(new) = {w_new.tolist()}  | counterfactual old = {w_old.tolist()}")
    dash = None
    for line in open(DASH):
        try: r = json.loads(line)
        except ValueError: continue
        if int(r.get("anchor_ts") or 0) == B and "w3_raw" in r: dash = [float(x) for x in r["w3_raw"]]
    if dash is None: V["w3_raw"] = "UNDECIDED (no dashboard row)"
    else:
        d = [abs(x - y) for x, y in zip(w_new, dash)]
        V["w3_raw"] = "PASS" if max(d) <= 5e-5 + 1e-12 else f"RED (max |d| {max(d):.2e} > 5e-5)"
        print(f"    regime_dash w3_raw {dash} max|d| {max(d):.2e} (tolerance 5e-5: stored to 4 dp)")
    tcp = os.path.join(a.state, "target_combo", f"{B}.json")
    if not os.path.exists(tcp): V["w3_masked"] = "UNDECIDED (no target_combo)"
    else:
        wm = json.load(open(tcp)).get("w3_masked")
        m = np.array([w_new[0], 0.0, w_new[2]]); m = m / m.sum() if m.sum() > 1e-12 else np.array([0.5, 0.0, 0.5])
        pred = [round(float(x), 6) for x in m]
        V["w3_masked"] = "PASS" if pred == wm else f"RED (pred {pred} != recorded {wm})"
        print(f"    target_combo w3_masked {wm} vs predicted {pred}")
    pr = (json.load(open(os.path.join(a.state, "snap", str(B), "aux.json"))).get("prev_rec") or {})
    if int(pr.get("anchor_ts", -1)) != B: V["target"] = "UNDECIDED (prev_rec of B missing)"
    else:
        tn, _ = D.build_target(pr["legz"], pr["members"], pr["sel_idx"], list(w_new), P, NW)
        to, _ = D.build_target(pr["legz"], pr["members"], pr["sel_idx"], list(w_old), P, NW)
        if tn is None or to is None: V["target"] = "UNDECIDED (target build gate)"
        else:
            dd = tn - to; s = float(np.abs(dd).sum()); flips = int(((np.sign(tn) * np.sign(to)) < 0).sum())
            E = json.load(open(D10_EXP)); ex = [x for x in E["anchors"] if "sum_abs_dw" in x]
            if not ex: V["target"] = "UNDECIDED (no expectation)"
            else:
                hi = max(x["sum_abs_dw"] for x in ex); fhi = max(int(x["direction_flips"]) for x in ex)
                top = [(int(i), float(dd[i])) for i in np.argsort(-np.abs(dd))[:5]]
                print(f"(3) target layer: sum|dw| {s:.4f} flips {flips} | expectation: last {ex[-1]['anchor']} {ex[-1]['sum_abs_dw']:.4f} "
                      f"(flips {ex[-1]['direction_flips']}), max {hi:.4f}, max flips {fhi}, trend {[round(x['sum_abs_dw'], 4) for x in ex[-4:]]} | top5 {top}")
                V["target"] = "CONSISTENT" if (s <= hi and flips <= fhi) else f"OUTSIDE_EXPECTATION (sum|dw| {s:.4f} vs max {hi:.4f}; flips {flips} vs max {fhi})"
    for key, v in V.items(): print(f"  {key}: {v}")
    overall = ("RED" if any(v.startswith("RED") for v in V.values()) else "UNDECIDED" if any(v.startswith("UNDECIDED") for v in V.values())
               else "OUTSIDE_EXPECTATION" if V.get("target", "").startswith("OUTSIDE") else "PASS")
    print(f"RESEED_FIRST_ANCHOR VERDICT={overall} " + " ".join(f"{k_}={v.split()[0]}" for k_, v in V.items()))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
