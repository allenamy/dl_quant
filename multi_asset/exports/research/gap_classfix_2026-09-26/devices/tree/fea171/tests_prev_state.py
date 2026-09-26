"""U-arm of ACCEPTANCE_gap_classfix_2026-09-26 §2: prev_state on synthetic state directories, run against TWO implementations:
  NEW = prev_state.latest_state            (must pass every case)
  OLD = the exact A-14400 predicate of combo_stage.py 12a76de8 L310-316 (copied verbatim below; must FAIL the gap / corrupt cases,
        otherwise the cases cannot tell the two apart and the arm is void)
Exit 0 iff NEW passes all AND OLD fails every case marked discriminating. Prints the matrix and a final verdict line."""
import io, os, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prev_state as PS

NW, A = 450, 1790438400
rng = np.random.default_rng(7)


def state_bytes(anchor, idx, val, compressed=False, **extra):
    b = io.BytesIO()
    (np.savez_compressed if compressed else np.savez)(b, **({"anchor": anchor} if anchor is not None else {}), idx=idx, val=val, **extra)
    return b.getvalue()


def good(anchor):
    idx = np.sort(rng.choice(NW, 300, replace=False)).astype(np.int64)
    return idx, rng.normal(0, 3.5e-3, 300)          # gross ~0.84, the live kc/fc scale


def old_lookup(d, leg, A_, NW_):
    """combo_stage.py 12a76de8 L310-316 verbatim (fallback = zeros, tag 'fallback')."""
    HERE = d; A = A_; NW = NW_
    def _load_state2(pth, fallback, tag):
        if os.path.exists(pth):
            zz = np.load(pth)
            if int(zz["anchor"]) == A - 14400:
                v = np.zeros(NW); v[zz["idx"].astype(np.int64)] = zz["val"].astype(np.float64)
                return v, "own"
        return fallback.copy(), tag
    v, s = _load_state2(f"{HERE}/state_H_{leg}_{A-14400}.npz", np.zeros(NW), "fallback")
    return {"vec": v, "source": s}


def new_lookup(d, leg, A_, NW_):
    return PS.latest_state(f"{d}/state_H_{leg}_{{a}}.npz", A_, NW_)


def write(d, name, raw):
    with open(os.path.join(d, name), "wb") as f:
        f.write(raw)


def case_files(d, anchors, bad=None):
    """valid kc files at `anchors`; bad = (anchor, raw bytes) replaces that anchor's file."""
    ref = {}
    for a in anchors:
        idx, val = good(a); ref[a] = (idx, val)
        write(d, f"state_H_kc_{a}.npz", state_bytes(a, idx, val))
    if bad:
        write(d, f"state_H_kc_{bad[0]}.npz", bad[1])
    return ref


def vec(ref, a):
    v = np.zeros(NW); v[ref[a][0]] = ref[a][1]; return v


CASES = []   # (name, discriminating, fn(lookup) -> None or failure text)
def case(name, disc):
    def deco(fn): CASES.append((name, disc, fn)); return fn
    return deco


def expect(d, lookup, want_src, want_anchor, ref):
    got = lookup(d, "kc", A, NW)
    if got["source"] != want_src:
        return f"source {got['source']!r} != {want_src!r}"
    if want_anchor is None:
        return None if got["vec"] is None or not np.any(got["vec"]) else "expected no state"
    if got["vec"] is None or not np.array_equal(got["vec"], vec(ref, want_anchor)):
        return f"vector != state at {want_anchor}"
    return None


@case("no_gap_own", False)
def _(lookup, d):
    ref = case_files(d, [A - 14400 * k for k in (1, 2, 3)])
    return expect(d, lookup, "own", A - 14400, ref)


for _k in (1, 2, 6):
    @case(f"gap{_k}", True)
    def _(lookup, d, k=_k):
        ref = case_files(d, [A - 14400 * j for j in range(k + 1, k + 4)])
        return expect(d, lookup, f"own_gap{k}", A - 14400 * (k + 1), ref)


@case("gap7_beyond_bound", True)
def _(lookup, d):
    ref = case_files(d, [A - 14400 * j for j in (8, 9)])
    r = expect(d, lookup, "own_gap7_beyond_bound", A - 14400 * 8, ref)
    if r is None and lookup is new_lookup and not PS.needs_page(new_lookup(d, "kc", A, NW)):
        return "beyond bound must page"
    return r


@case("corrupt_garbage", True)
def _(lookup, d):
    ref = case_files(d, [A - 28800, A - 43200], bad=(A - 14400, b"\x00garbage" * 50))
    try:
        return expect(d, lookup, "own_gap1_rejected1", A - 28800, ref)
    except Exception as e:                                 # OLD raises on an unreadable file
        return f"raised {type(e).__name__}"


@case("anchor_key_mismatch", True)
def _(lookup, d):
    idx, val = good(0)
    ref = case_files(d, [A - 28800], bad=(A - 14400, state_bytes(A - 28800, idx, val)))
    return expect(d, lookup, "own_gap1_rejected1", A - 28800, ref)


@case("idx_out_of_range", True)
def _(lookup, d):
    idx, val = good(0); idx = idx.copy(); idx[-1] = NW
    ref = case_files(d, [A - 28800], bad=(A - 14400, state_bytes(A - 14400, idx, val)))
    try:
        return expect(d, lookup, "own_gap1_rejected1", A - 28800, ref)
    except Exception as e:
        return f"raised {type(e).__name__}"


@case("nonfinite_val", True)
def _(lookup, d):
    idx, val = good(0); val = val.copy(); val[3] = np.nan
    ref = case_files(d, [A - 28800], bad=(A - 14400, state_bytes(A - 14400, idx, val)))
    return expect(d, lookup, "own_gap1_rejected1", A - 28800, ref)


@case("duplicate_idx", True)
def _(lookup, d):
    idx, val = good(0); idx = idx.copy(); idx[1] = idx[0]
    ref = case_files(d, [A - 28800], bad=(A - 14400, state_bytes(A - 14400, idx, val)))
    return expect(d, lookup, "own_gap1_rejected1", A - 28800, ref)


@case("degenerate_ramp_state", True)
def _(lookup, d):
    idx, val = good(0)
    ref = case_files(d, [A - 28800], bad=(A - 14400, state_bytes(A - 14400, idx, val * 0.1)))   # a zero-started ramp, gross ~0.08
    return expect(d, lookup, "own_gap1_rejected1", A - 28800, ref)


@case("missing_key", True)
def _(lookup, d):
    idx, _v = good(0)
    b = io.BytesIO(); np.savez(b, anchor=A - 14400, idx=idx)
    ref = case_files(d, [A - 28800], bad=(A - 14400, b.getvalue()))
    try:
        return expect(d, lookup, "own_gap1_rejected1", A - 28800, ref)
    except Exception as e:
        return f"raised {type(e).__name__}"


@case("pickled_object_array", True)
def _(lookup, d):
    b = io.BytesIO(); np.savez(b, anchor=A - 14400, idx=np.array([1, 2], object), val=np.array([0.1, 0.2]))
    ref = case_files(d, [A - 28800], bad=(A - 14400, b.getvalue()))
    try:
        return expect(d, lookup, "own_gap1_rejected1", A - 28800, ref)
    except Exception as e:
        return f"raised {type(e).__name__}"


@case("future_and_offgrid_ignored", False)
def _(lookup, d):
    ref = case_files(d, [A - 14400, A, A + 14400])
    idx, val = good(0)
    write(d, f"state_H_kc_{A - 100}.npz", state_bytes(A - 100, idx, val))   # off the 4 h grid: never a candidate
    write(d, "state_H_kc.npz", state_bytes(A - 14400, idx, val))            # legacy single file: not matched by the pattern
    write(d, f"state_H_kcx_{A - 14400}.npz", state_bytes(A - 14400, idx, val))
    return expect(d, lookup, "own", A - 14400, ref)


@case("no_state_at_all", True)
def _(lookup, d):
    got = lookup(d, "kc", A, NW)
    if lookup is old_lookup:
        return "OLD returns a silent zero fallback (source 'fallback', no page)"
    if got["vec"] is not None or not PS.needs_page(got):
        return "no state must return None and page"
    return None


@case("weights_mode_no_anchor_key_int32_float32", False)
def _(lookup, d):
    if lookup is old_lookup:
        return None                                       # OLD's weights predicate is L59 (not _load_state2); covered by C0 in the replay
    idx = np.sort(rng.choice(NW, 250, replace=False)).astype(np.int32); val = rng.normal(0, 3e-3, 250).astype(np.float32)
    os.makedirs(f"{d}/weights")
    write(d, f"weights/{A - 43200}.npz", state_bytes(None, idx, val, compressed=True, members=np.arange(400, dtype=np.int32)))
    got = PS.latest_state(f"{d}/weights/{{a}}.npz", A, NW, anchor_key=False)
    H = np.zeros(NW); H[idx.astype(np.int64)] = val.astype(np.float64)     # the L59 idiom of 12a76de8
    if got["source"] != "own_gap2" or not np.array_equal(got["vec"], H):
        return f"weights lookup {got['source']} / equal={got['vec'] is not None and np.array_equal(got['vec'], H)}"
    return None


def main():
    rows, bad_new, undiscriminating = [], [], []
    for name, disc, fn in CASES:
        res = {}
        for tag, lk in (("NEW", new_lookup), ("OLD", old_lookup)):
            with tempfile.TemporaryDirectory() as d:
                try:
                    res[tag] = fn(lk, d)
                except Exception as e:                    # noqa: BLE001
                    res[tag] = f"raised {type(e).__name__}: {e}"
        rows.append((name, disc, res["NEW"], res["OLD"]))
        if res["NEW"] is not None: bad_new.append(name)
        if disc and res["OLD"] is None: undiscriminating.append(name)
    for name, disc, n, o in rows:
        print(f"{name:42s} disc={int(disc)}  NEW={'PASS' if n is None else 'FAIL ' + n}  OLD={'PASS' if o is None else 'RED  ' + o}")
    ok = not bad_new and not undiscriminating
    print(f"PREV_STATE_TESTS {'PASS' if ok else 'FAIL'} cases={len(rows)} new_fail={bad_new} old_not_red_on_discriminating={undiscriminating} "
          f"old_red={sum(1 for r in rows if r[3] is not None)}/{sum(1 for r in rows if r[1])}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
