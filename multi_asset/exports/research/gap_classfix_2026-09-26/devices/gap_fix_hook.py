#!/usr/bin/env python3
"""Hook for gap_fix_replay.sh (ACCEPTANCE_gap_classfix_2026-09-26 §2): mutate the SANDBOX copy of fea171 / state before replaying anchor A.
  base        nothing
  gap<K>      anchors A-4h .. A-K*4h never ran: remove state_H_{kc,fc,f10}_<a> and state/weights/<a>.npz for each
  bridge<K>   gap<K>, then state_H_*_<A-4h> := the lead's combo_state_bridge.payload(state at A-(K+1)*4h) (weights stay absent, as live)
  x1          state_H_kc_<A-4h> := garbage bytes
  x2          state_H_kc_<A-4h> := its own idx/val with anchor key A-8h (mismatched)
  x3          state_H_kc_<A-4h> := its own anchor/val with one idx = NW (out of range)
  xref        reference for x1-x3: state_H_kc_<A-4h> := payload(state_H_kc_<A-8h>, A-4h)
Prints one HOOK line with the sha of every file it wrote or removed."""
import hashlib, importlib.util, io, os, re, sys
import numpy as np

sb, A, arm = sys.argv[1], int(sys.argv[2]), sys.argv[3]
fea = f"{sb}/wide_shadow/fea171"; st = f"{sb}/wide_shadow/state"; H4 = 14400
assert os.path.realpath(sb).startswith(os.path.realpath(os.environ["SCR_ROOT"]) + os.sep), "hook only mutates the scratch sandbox"
_spec = importlib.util.spec_from_file_location(
    "bridge", "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/gap_recovery_2026-09-26/devices/combo_state_bridge.py")
B = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(B)
LEGS = ("kc", "fc", "f10")
done = []


def sp(leg, a): return f"{fea}/state_H_{leg}_{a}.npz"
def sha(b): return hashlib.sha256(b).hexdigest()[:12]


def rm(p):
    done.append(f"rm {os.path.relpath(p, sb)} {sha(open(p, 'rb').read())}"); os.remove(p)


def put(p, raw):
    if os.path.exists(p): rm(p)
    with open(p, "xb") as f: f.write(raw)
    done.append(f"put {os.path.relpath(p, sb)} {sha(raw)}")


def npz(**kw):
    b = io.BytesIO(); np.savez(b, **kw); return b.getvalue()


m = re.fullmatch(r"(gap|bridge)(\d+)", arm)
if arm == "base":
    pass
elif m:
    K = int(m.group(2)); assert K >= 1
    for j in range(1, K + 1):
        a = A - j * H4
        for leg in LEGS: rm(sp(leg, a))
        rm(f"{st}/weights/{a}.npz")
    if m.group(1) == "bridge":
        S = A - (K + 1) * H4
        for leg in LEGS: put(sp(leg, A - H4), B.payload(np.load(sp(leg, S)), A - H4))
elif arm in ("x1", "x2", "x3", "xref"):
    P, PP = A - H4, A - 2 * H4
    z = np.load(sp("kc", P))
    if arm == "x1":
        put(sp("kc", P), b"\x00not-an-npz" * 64)
    elif arm == "x2":
        put(sp("kc", P), npz(anchor=PP, idx=z["idx"], val=z["val"]))
    elif arm == "x3":
        with np.load(f"{sb}/wide_shadow/state/rolling.npz") as _r:
            _f = _r.zip.open("data.npy"); np.lib.format.read_magic(_f); NW = np.lib.format.read_array_header_1_0(_f)[0][1]
        idx = z["idx"].copy(); idx[-1] = NW
        put(sp("kc", P), npz(anchor=P, idx=idx, val=z["val"]))
    else:
        put(sp("kc", P), B.payload(np.load(sp("kc", PP)), P))
else:
    raise SystemExit(f"unknown arm {arm}")
print(f"HOOK arm={arm} A={A} " + " | ".join(done))
