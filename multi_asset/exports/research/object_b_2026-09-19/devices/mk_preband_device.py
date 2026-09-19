#!/usr/bin/env python3
"""AMENDMENT 4 A4.2: generate combo_stage_replay_3520d363_preband.py from the replay device combo_stage_replay_3520d363.py (92c49fa8…) by 4 asserted,
record-only insertions (no computation changes):
  I1 module-level list `_PREBAND = []` after `from scipy.stats import rankdata`
  I2 first statement of chain(): `_PREBAND.append(None)` (a placeholder per call, so an early `return None` keeps the call order)
  I3 right after `smv = H + P["alpha"] * (tgt - H)`: `_PREBAND[-1] = smv.copy()` — the pre-band state (before L92's neutral band)
  I4 after the kc/fc state files are written: if PREBAND_OUT is set, save the 4 recorded vectors (self-parity king, sidecar f10, kc, fc)
usage: python3 mk_preband_device.py <dir>"""
import hashlib, io, json, os, sys
D = sys.argv[1]; SRC = f"{D}/combo_stage_replay_3520d363.py"; PIN = "92c49fa82d4c5c1bdb70c6155c0c3e7bfe3c5f012e1db0aeb686ef1fbcd6e1d8"
src = io.open(SRC, encoding="utf-8").read(); assert hashlib.sha256(src.encode()).hexdigest() == PIN


def once(s, a, b):
    assert s.count(a) == 1, (s.count(a), a[:60]); return s.replace(a, b)


s = once(src, "from scipy.stats import rankdata\n", "from scipy.stats import rankdata\n_PREBAND = []   # OBJECT-B INSTRUMENT I1 (AMENDMENT 4)\n")
s = once(s, "def chain(zc):\n    w = np.where(sel, zc, 0.0)\n", "def chain(zc):\n    _PREBAND.append(None)   # OBJECT-B INSTRUMENT I2\n    w = np.where(sel, zc, 0.0)\n")
s = once(s, '    smv = H + P["alpha"] * (tgt - H)\n', '    smv = H + P["alpha"] * (tgt - H)\n    _PREBAND[-1] = smv.copy()   # OBJECT-B INSTRUMENT I3: pre-band state\n')
s = once(s, "    np.savez(_p, anchor=A, idx=_nz, val=_sm[_nz])\n",
         "    np.savez(_p, anchor=A, idx=_nz, val=_sm[_nz])\n"
         "if os.environ.get(\"PREBAND_OUT\"):   # OBJECT-B INSTRUMENT I4: the 4 chain() calls in file order\n"
         "    assert len(_PREBAND) == 4, len(_PREBAND)\n"
         "    np.savez(os.environ[\"PREBAND_OUT\"], **{k_: (v_ if v_ is not None else np.full(NW, np.nan)) for k_, v_ in zip((\"king_selfparity\", \"f10_sidecar\", \"kc\", \"fc\"), _PREBAND)})\n")
out = f"{D}/combo_stage_replay_3520d363_preband.py"; io.open(out, "w", encoding="utf-8").write(s)
print(json.dumps({"source": SRC, "source_sha256": PIN, "device": out, "device_sha256": hashlib.sha256(s.encode()).hexdigest(), "n_insertions": 4}))
