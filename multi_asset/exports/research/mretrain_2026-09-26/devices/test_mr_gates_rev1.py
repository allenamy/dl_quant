"""test_mr_gates_rev1.py — red tests of mr_gates.oof_equal (rule §7 revision 1: King OOF identity on every array except the
provenance text model_sha256). Copies of the A0_m0 OOF are written to a scratch dir (never the original); the baseline must be
green first. Prints one line per case and TEST_MR_GATES_REV1 ALL_OK=True|False; rc 0 only when every case matched.
usage: python test_mr_gates_rev1.py <devices_dir> <KING_OOF.npz> <scratch_dir>"""
import os, sys, shutil
import numpy as np
D, SRC, T = sys.argv[1:4]
sys.path.insert(0, D); import mr_gates as G
os.makedirs(T, exist_ok=False)
z = np.load(SRC, allow_pickle=False); base = {k: z[k].copy() for k in z.files}
assert "model_sha256" in base and "P" in base, sorted(base)


def write(name, arrs):
    p = os.path.join(T, name + ".npz"); np.savez(p, **arrs); return p


def case(name, mutate, expect):
    arrs = {k: v.copy() for k, v in base.items()}; mutate(arrs)
    ok, det = G.oof_equal(ref, write(name, arrs)); got = "PASS" if ok else "FAIL"
    print(f"CASE {name} expect={expect} got={got} {'OK' if got == expect else 'MISMATCH'} :: {det}", flush=True)
    return got == expect


def p_ulp(a):
    i = np.flatnonzero(np.isfinite(a["P"].ravel()))[12345]; v = a["P"].ravel(); v[i] = np.nextafter(v[i], np.float32(np.inf)); a["P"] = v.reshape(base["P"].shape)


def model_sha(a):
    m = a["model_sha256"].copy(); m[m != ""] = "0" * 64; a["model_sha256"] = m


ref = write("ref", base)
res = [case("B0_identical_copy", lambda a: None, "PASS")]
if not res[0]: print("TEST_MR_GATES_REV1 ALL_OK=False (baseline not green)"); shutil.rmtree(T); sys.exit(1)
res += [case("B1_only_model_sha256_differs", model_sha, "PASS"),
        case("R1_one_P_element_one_ulp", p_ulp, "FAIL"),
        case("R2_P_differs_and_model_sha256_differs", lambda a: (p_ulp(a), model_sha(a)), "FAIL"),
        case("R3_E_ts_shifted", lambda a: a.__setitem__("E_ts", a["E_ts"] + 14400), "FAIL"),
        case("R4_symbols_renamed", lambda a: a["symbols"].__setitem__(0, "XXXUSDT"), "FAIL"),
        case("R5_P_dtype_float64", lambda a: a.__setitem__("P", a["P"].astype(np.float64)), "FAIL"),
        case("R6_extra_array", lambda a: a.__setitem__("extra", np.zeros(3)), "FAIL"),
        case("R7_model_sha256_missing", lambda a: a.pop("model_sha256"), "FAIL")]
shutil.rmtree(T)
print("TEST_MR_GATES_REV1 ALL_OK=%s cases=%d scratch_removed" % (all(res), len(res)), flush=True)
sys.exit(0 if all(res) else 1)
