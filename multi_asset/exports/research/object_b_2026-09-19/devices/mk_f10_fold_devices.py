#!/usr/bin/env python3
"""Generate the two derived F10 devices for object B (PREREG_object_B_recipe_oof_and_object_A_paper_2026-09-19 §1 / §3 S2) from the in-service
sources by exact, once-only text edits (each asserted count == 1 on the source). Nothing else changes; the devices self-report their provenance.

  f10_refit_fold.py      <- /workspace/pod_f10_refit_ext.py  (sha ea3675b8…, the in-service V2MAIN refit trainer)
      edit 1  after the XL concatenation: optional in-memory truncation to anchors whose label end (E + 4h) < F10_CUTOFF (unset => no-op)
      edit 2  the checkpoint path comes from F10_SAVE (never the in-service f8_ext/models/f10_live_s{SEED}.pt)
  f10_np_export_fold.py  <- /workspace/pod_f10_np_export.py  (sha 3e304c27…, the in-service np export + gate V1)
      edit 1  checkpoint path from F10_CK; edit 2  output path from F10_NPOUT; edit 3  trained_through from the checkpoint (not the data axis end)
usage: python3 mk_f10_fold_devices.py <out_dir>"""
import hashlib, io, json, os, sys, time

OUT = sys.argv[1]
SRC_TRAIN = ("/workspace/pod_f10_refit_ext.py", "ea3675b8012ea266646571f6e1550f248d894cae832b190a8beab27befab9fb7")
SRC_EXPORT = ("/workspace/pod_f10_np_export.py", "3e304c27606d3c12f9734d520773b2afe5aa85dcd0cdc5e984e041f9988474f9")


def load(p, s):
    b = open(p, "rb").read(); h = hashlib.sha256(b).hexdigest(); assert h == s, (p, h); return b.decode("utf-8"), h


def once(src, a, b):
    n = src.count(a); assert n == 1, (n, a[:80]); return src.replace(a, b)


tr, trs = load(*SRC_TRAIN)
a1 = 'XL = np.concatenate([FE["X"], F9["X"]], 1).astype(np.float32); del FE, F9\n'
b1 = a1 + ('_CUT = os.environ.get("F10_CUTOFF")   # OBJECT-B DERIVED EDIT 1/2: yearly fold = anchors whose label end (E + 4h) < cutoff; unset => no-op\n'
           'if _CUT:\n'
           '    assert np.all(np.diff(E_ts) > 0) and np.all(np.diff(pa) >= 0)\n'
           '    _n = int(np.searchsorted(E_ts + 14400, int(_CUT), side="left"))\n'
           '    E_ts = E_ts[:_n]; y4s = y4s[:_n]; nA = _n\n'
           '    _k = int(np.searchsorted(pa, _n)); pa = pa[:_k]; ps = ps[:_k]; XL = XL[:_k]\n'
           '    log(f"F10_CUTOFF {_CUT}: kept {_n} anchors (last {E_ts[-1]}, label end {E_ts[-1] + 14400}) and {_k} pairs")\n')
tr = once(tr, a1, b1)
a2 = 'os.makedirs(f"{OUT}/models", exist_ok=True)\n'
b2 = ('_SAVE = os.environ["F10_SAVE"]   # OBJECT-B DERIVED EDIT 2/2: never the in-service checkpoint\n'
      'assert not os.path.realpath(_SAVE).startswith("/workspace/f8_ext/"), _SAVE\n'
      'os.makedirs(os.path.dirname(_SAVE), exist_ok=True)\n')
tr = once(tr, a2, b2)
tr = once(tr, '           f"{OUT}/models/f10_live_s{SEED}.pt")\n', '           _SAVE)\n')
tr = f'# OBJECT-B DEVICE generated {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} from {SRC_TRAIN[0]} sha256 {trs}; 3 asserted edits (truncation block, save path x2)\n' + tr

ex, exs = load(*SRC_EXPORT)
ex = once(ex, 'CK = f"{OUT}/models/f10_live_s{SEED}.pt"\n', 'CK = os.environ["F10_CK"]   # OBJECT-B DERIVED EDIT 1/3\n')
ex = once(ex, 'trained_through = int(TG["E_ts"].astype(np.int64).max())\n',
          'trained_through = int(ck["trained_through"])   # OBJECT-B DERIVED EDIT 3/3: the checkpoint\'s own training end, not the data axis end\n')
ex = once(ex, 'np.savez(f"{OUT}/models/f10_live_s{SEED}_np.npz", **W,', 'np.savez(os.environ["F10_NPOUT"], **W,   # OBJECT-B DERIVED EDIT 2/3\n        ')
ex = f'# OBJECT-B DEVICE generated {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} from {SRC_EXPORT[0]} sha256 {exs}; 3 asserted edits (ckpt path, out path, trained_through)\n' + ex

os.makedirs(OUT, exist_ok=True); rec = {}
for name, txt, src in (("f10_refit_fold.py", tr, SRC_TRAIN), ("f10_np_export_fold.py", ex, SRC_EXPORT)):
    p = os.path.join(OUT, name); io.open(p, "w", encoding="utf-8").write(txt)
    rec[name] = {"source": src[0], "source_sha256": src[1], "device_sha256": hashlib.sha256(txt.encode()).hexdigest()}
print(json.dumps(rec, indent=1))
