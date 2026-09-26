#!/usr/bin/env python3
"""Hook for gap_arm_replay.sh: mutate the SANDBOX copy of fea171/state to emulate a producer gap before anchor A.
arm=base: nothing. arm=gap: remove state_H_{kc,fc,f10}_<A-4h> and state/weights/<A-4h>.npz (A-4h never ran).
arm=bridge: as gap, then write state_H_*_<A-4h> from state_H_*_<A-8h> with the SAME payload function the live bridge uses
(combo_state_bridge.payload); weights/<A-4h> stays absent exactly as in the live bridge."""
import importlib.util, os, sys
import numpy as np
sb, A, arm = sys.argv[1], int(sys.argv[2]), sys.argv[3]
fea = f"{sb}/wide_shadow/fea171"; st = f"{sb}/wide_shadow/state"; P, PP = A - 14400, A - 28800
assert os.path.realpath(sb).startswith(os.path.realpath(os.environ["SCR_ROOT"])), "hook only mutates the scratch sandbox"
if arm in ("gap", "bridge"):
    for leg in ("kc", "fc", "f10"):
        os.remove(f"{fea}/state_H_{leg}_{P}.npz")
    os.remove(f"{st}/weights/{P}.npz")
if arm == "bridge":
    spec = importlib.util.spec_from_file_location("b", os.path.join(os.path.dirname(os.path.abspath(__file__)), "combo_state_bridge.py"))
    B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
    for leg in ("kc", "fc", "f10"):
        open(f"{fea}/state_H_{leg}_{P}.npz", "xb").write(B.payload(np.load(f"{fea}/state_H_{leg}_{PP}.npz"), P))
print(f"HOOK arm={arm} A={A} P={P} states_present={[os.path.exists(f'{fea}/state_H_{l}_{P}.npz') for l in ('kc','fc','f10')]} weights_P={os.path.exists(f'{st}/weights/{P}.npz')}")
