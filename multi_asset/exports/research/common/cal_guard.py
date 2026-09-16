#!/usr/bin/env python3
"""cal_guard.py — EVL-01 (c): refuse to launch a CAL-reading device unless CAL is in the enumerated env whitelist (FX-DATA).

The lead's ruling is **(a) + (c), never (b)**: the archived devices keep every byte, because SPEC section 7 pins `w10_sleeve.py`
at sha `b88e35a4` as the A0 reference arm and 38 committed device blobs write their self-sha into receipts — editing the default
would break a frozen specification and every reproduction-by-path at once. The protection therefore lives on the LAUNCH side. This
module changes no device byte and moves no sha.

It is the positive form of E-0826-D ("a re-run that forgot an env var"): instead of discovering afterwards that a run was missing a
variable, the run does not start.

Why the guard keys on **sha256 and not on a path**. The manifest (`data/cal_required_devices.json`, built by
`FX_DATA/devices/fx_evl01_manifest.py` from committed blobs, never the working tree) resolves **54 paths to 38 distinct blobs** —
one blob appears at **8** different paths, and the A0 device's own blob sits at 4 git paths *and* at a pod2 path that is not in git
at all. A path-keyed guard would miss the copies and would miss the device that actually runs.

What the guard does NOT do: it does not decide what CAL should be. It requires that the launcher states it. Choosing `log` for the
pod 5m cache lineage is a caliber question settled elsewhere (E-0904-F); a guard that silently supplied a value would be making
that choice for the operator, which is the same mistake in the other direction.
"""
import hashlib, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "data", "cal_required_devices.json")
MANIFEST_SHA256 = "a416ce3054adda6fc9970111d2fc528da4b5c8d990e9ef2bd28975cf2cd5894f"
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class CalGuardError(RuntimeError):
    """a launch the guard refuses"""


def _sha256_file(path):
    size = os.stat(path).st_size; h = hashlib.sha256(); n = 0
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b); n += len(b)
    d = h.hexdigest()
    if n != size or (size > 0 and d == EMPTY_SHA256):
        raise CalGuardError("unreadable or evicted file %s (read %d of %d bytes)" % (path, n, size))
    return d


def load_manifest(path=None, *, expected_sha256=MANIFEST_SHA256):
    p = MANIFEST if path is None else path
    got = _sha256_file(p)
    if expected_sha256 is not None and got != expected_sha256:
        raise CalGuardError("manifest sha %s != expected %s; rebuild it with fx_evl01_manifest.py and re-pin"
                            % (got[:16], expected_sha256[:16]))
    m = json.load(open(p))
    if not m.get("requiring_cal_sha256"):
        raise CalGuardError("manifest carries no device shas; refusing to treat that as 'nothing needs CAL'")
    return m


def requires_cal(device_path, *, manifest=None):
    """True iff this exact file is one of the pinned CAL-reading blobs. Identity is the sha, not the name."""
    m = manifest if manifest is not None else load_manifest()
    return _sha256_file(device_path) in set(m["requiring_cal_sha256"])


def check_launch(device_path, env, *, whitelist, manifest=None):
    """Refuse the launch unless CAL is BOTH in the enumerated whitelist and present in the env being passed.

    `whitelist` is the launcher's own enumerated env whitelist. Requiring CAL to appear in it, and not merely in the process
    environment, is the point: a variable that leaked in from an ambient shell is not a declared configuration.
    """
    if not isinstance(whitelist, (set, frozenset, list, tuple)):
        raise CalGuardError("whitelist must be an explicit collection of variable names, got %s" % type(whitelist).__name__)
    wl = set(whitelist)
    if not requires_cal(device_path, manifest=manifest):
        return {"device": device_path, "requires_cal": False, "ok": True,
                "note": "not a pinned CAL-reading blob; the guard has nothing to say about it"}
    missing = []
    if "CAL" not in wl:
        missing.append("CAL is not in the launcher's enumerated env whitelist")
    if "CAL" not in env:
        missing.append("CAL is not set in the environment being passed to the device")
    if missing:
        raise CalGuardError(
            "REFUSING TO LAUNCH %s (sha %s): it reads CAL with a non-log default, so a launch without CAL would apply "
            "expm1 to an already-simple y4. %s. Ruling: FIXPROGRAM EVL-01 (a)+(c) — the device is frozen, the launcher "
            "must declare CAL." % (os.path.basename(device_path), _sha256_file(device_path)[:16], "; ".join(missing)))
    return {"device": device_path, "device_sha256": _sha256_file(device_path), "requires_cal": True, "ok": True,
            "cal": env["CAL"], "whitelist": sorted(wl)}


def require_cal(env, *, who):
    """For NEW devices: CAL is required and has no default (FIXPROGRAM EVL-01 ruling, last clause)."""
    if "CAL" not in env:
        raise CalGuardError("%s requires CAL explicitly; new devices get no default (FIXPROGRAM EVL-01)" % who)
    return env["CAL"]
