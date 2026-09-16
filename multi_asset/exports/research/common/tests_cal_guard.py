#!/usr/bin/env python3
"""tests_cal_guard.py — red tests for the EVL-01 (c) launch-side guard (FX-DATA).

The lead's stated red test: launching one of the pinned devices WITHOUT CAL must be refused and the device named; launching it WITH
CAL=log must be allowed. The bitwise half of the positive control (output identical to an existing receipt) is the separate pod2 run
`run23_cal_guard_control.sh`, because it needs the real arm; these cells are the guard's own contract.

Run: python3 tests_cal_guard.py
"""
import os, sys, json, hashlib, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cal_guard as G

RES = []
def cell(name, fn):
    try:
        fn(); RES.append((name, True, ""))
    except AssertionError as e:
        RES.append((name, False, "assert: %s" % e))
    except Exception as e:
        RES.append((name, False, "%s: %s" % (type(e).__name__, e)))

def raises(exc, fn, needle=None):
    try:
        fn()
    except exc as e:
        assert needle is None or needle in str(e), "wrong message: %s" % e
        return
    raise AssertionError("did not raise %s" % exc.__name__)

M = G.load_manifest()
WL = {"PATH", "HOME", "CAL", "LEGS", "PHI"}
TMP = tempfile.mkdtemp()

def _pinned_copy():
    """a file whose bytes ARE one of the pinned blobs, so the guard must recognise it wherever it sits"""
    d = M["devices"][0]
    src = os.path.join("/Users/haosiyu/Desktop/quant_research", d["paths"][0])
    p = os.path.join(TMP, "renamed_on_purpose.py")
    with open(src, "rb") as a, open(p, "wb") as b: b.write(a.read())
    assert hashlib.sha256(open(p, "rb").read()).hexdigest() == d["sha256"], "fixture is not the pinned blob"
    return p, d

def _unpinned():
    p = os.path.join(TMP, "not_a_device.py")
    open(p, "w").write("print('hello')\n")
    return p

cell("manifest_sha_is_pinned", lambda: G.load_manifest(expected_sha256=G.MANIFEST_SHA256) and None)
cell("manifest_rejects_a_wrong_sha", lambda: raises(G.CalGuardError, lambda: G.load_manifest(expected_sha256="0" * 64), "rebuild it"))
cell("manifest_has_38_blobs_and_54_paths",
     lambda: None if (M["n_distinct_blobs"] == 38 and M["n_paths"] == 54) else (_ for _ in ()).throw(AssertionError(str((M["n_paths"], M["n_distinct_blobs"])))))
cell("a0_blob_is_covered", lambda: None if "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650" in M["requiring_cal_sha256"] else (_ for _ in ()).throw(AssertionError("A0 not covered")))

def _identity_is_the_sha():
    p, d = _pinned_copy()
    assert G.requires_cal(p, manifest=M) is True, "a pinned blob renamed to anything must still be recognised"
    assert len(d["paths"]) >= 1
cell("identity_is_the_sha_not_the_path", _identity_is_the_sha)

def _refuse_without_cal():
    p, _ = _pinned_copy()
    raises(G.CalGuardError, lambda: G.check_launch(p, {"PATH": "/bin"}, whitelist=WL), "REFUSING TO LAUNCH")
    raises(G.CalGuardError, lambda: G.check_launch(p, {"PATH": "/bin"}, whitelist=WL), "renamed_on_purpose.py")
cell("refuses_and_names_the_device_when_CAL_absent_from_env", _refuse_without_cal)

def _refuse_when_not_in_whitelist():
    p, _ = _pinned_copy()
    raises(G.CalGuardError, lambda: G.check_launch(p, {"CAL": "log"}, whitelist={"PATH", "HOME"}),
           "not in the launcher's enumerated env whitelist")
cell("refuses_when_CAL_only_leaked_from_the_ambient_env", _refuse_when_not_in_whitelist)

def _allow_with_cal_log():
    p, _ = _pinned_copy()
    o = G.check_launch(p, {"PATH": "/bin", "CAL": "log"}, whitelist=WL)
    assert o["ok"] and o["requires_cal"] and o["cal"] == "log", o
cell("allows_with_CAL_log_declared_in_the_whitelist", _allow_with_cal_log)

cell("silent_about_a_file_it_does_not_pin",
     lambda: None if G.check_launch(_unpinned(), {"PATH": "/bin"}, whitelist=WL)["requires_cal"] is False else (_ for _ in ()).throw(AssertionError()))
cell("whitelist_must_be_an_explicit_collection",
     lambda: raises(G.CalGuardError, lambda: G.check_launch(_pinned_copy()[0], {"CAL": "log"}, whitelist="CAL"), "explicit collection"))
cell("new_devices_get_no_default",
     lambda: raises(G.CalGuardError, lambda: G.require_cal({"PATH": "/bin"}, who="a new device"), "no default"))
cell("require_cal_returns_the_declared_value",
     lambda: None if G.require_cal({"CAL": "log"}, who="x") == "log" else (_ for _ in ()).throw(AssertionError()))

ok = sum(1 for _, o, _ in RES if o)
for n, o, m in RES:
    print("%-56s %s%s" % (n, "PASS" if o else "FAIL", "" if o else "   " + m))
print("SUMMARY %d/%d cells pass" % (ok, len(RES)))
sys.exit(0 if ok == len(RES) else 1)
