#!/usr/bin/env python3
"""READ-ONLY hook for one engine cell (lead approval 2026-09-25 ~15:2xZ: "只读钩子单格(基线, NC s42X)"; DECISION RULE step 1 revision 5
02a9fde80 mechanism control). It records, per call of the executor mirror's scheduler.anchor_loop.apply_withhold_and_reshape (called by
exec_sim.Sim.on_anchor), the post-clamp book: rs["clamped_after_reshape"] (book_net_usdt, net_shift_usdt, pinned_net_usdt, names) plus
sizing_gross / net_before / net_after / n_popped, and the anchor A read from the caller's frame. It changes NOTHING the engine computes:
the wrapper calls the original with the same arguments, returns its exact return value, and serialises a deep copy of the report
(json.dumps on a copy; any hook error is counted in the hook file, never raised). Zero behavioural impact is a PREREQUISITE CONTROL, not an
assumption: the cell's per-window series must equal the filed NC s42X series bitwise (c4hook_read.py).
Mechanics: the mirror path (config paths.exec_mirror) is put on sys.path and scheduler.anchor_loop imported HERE, before bt_launch runs;
the engine's own later `import scheduler.anchor_loop as AL` (exec_sim.ExecutorCode.__init__) gets this same module object from
sys.modules, whose realpath is inside the mirror (the engine's assertion still holds). Children are forked (copy-on-write) and inherit the
wrapper; each process appends to HOOK_<pid>.jsonl.
usage: /workspace/venv/bin/python -B hook_prelude.py <hook out dir> <bt_launch.py> <bt_launch args ...>"""
import copy, json, os, runpy, sys, sys as _s

OUT = os.path.abspath(sys.argv[1]); BT = os.path.abspath(sys.argv[2]); ARGS = sys.argv[3:]
os.makedirs(OUT, exist_ok=True)
cfg = json.load(open(ARGS[1]))
MIR = os.path.join(os.path.abspath(cfg["paths"]["exec_mirror"]), "exec_tree_409ea16")   # = bt_hist_sim31 L112 / simlib L95 `self.tree`
if MIR not in sys.path: sys.path.insert(0, MIR)
import scheduler.anchor_loop as AL           # noqa: E402  (the mirror's module; the engine will get this object from sys.modules)
assert os.path.realpath(AL.__file__).startswith(os.path.realpath(MIR)), AL.__file__
_orig = AL.apply_withhold_and_reshape


def _hooked(*a, **k):
    res = _orig(*a, **k)
    try:
        clamp, rs = res
        f = _s._getframe(1); A = f.f_locals.get("A")
        rep = copy.deepcopy(rs) if rs is not None else None
        ca = (rep or {}).get("clamped_after_reshape") or {}
        row = {"A": int(A) if A is not None else None, "pid": os.getpid(), "sizing_gross": (rep or {}).get("sizing_gross"),
               "net_before": (rep or {}).get("net_before"), "net_after": (rep or {}).get("net_after"), "n_popped": (rep or {}).get("n_popped"),
               "book_net_usdt": ca.get("book_net_usdt"), "net_shift_usdt": ca.get("net_shift_usdt"), "pinned_net_usdt": ca.get("pinned_net_usdt"),
               "clamped_names": ca.get("names"), "rs_none": rs is None}
        with open(f"{OUT}/HOOK_{os.getpid()}.jsonl", "a") as fh:
            fh.write(json.dumps(row, default=str) + "\n")
    except Exception as e:                                    # noqa: BLE001 — a hook error must never change the engine
        try:
            with open(f"{OUT}/HOOK_ERRORS_{os.getpid()}.txt", "a") as fh:
                fh.write(f"{type(e).__name__}: {str(e)[:200]}\n")
        except Exception:
            pass
    return res


AL.apply_withhold_and_reshape = _hooked
sys.argv = [BT] + ARGS
runpy.run_path(BT, run_name="__main__")
