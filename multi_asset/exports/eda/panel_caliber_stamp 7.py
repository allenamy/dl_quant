"""0C — the funding-caliber STAMP an artifact carries with it.

> created 2026-07-29 | Session: 0C | 状态: permanent | 作废条件: 从不 (面板产物的自带口径声明)

WHY THIS EXISTS — THE ROUTING KEY, NOT THE VERDICT
--------------------------------------------------
`assert_funding_dim` asserts that a panel carries the caliber it is SUPPOSED to carry. To do that it
must first answer "which caliber is this artifact supposed to be?" — and where that answer comes
from has now been wrong twice in four days:

  2026-07-25  one caliber asserted on every panel        -> stopped the shadow for 28h
  2026-07-27  routed by filename (`*_fundfix -> corrected`)  -> right today, wrong in KIND
  2026-07-27  routed by the registry's declared PATH      -> a declaration, but keyed to a NAME

The last one is the subject of the team-lead ruling of 2026-07-29:

    "闸门的选择依据必须是产物自己携带的口径戳, 不是文件名或路径 —— 后者会在下一次重命名时静默失效。"

A path key fails silently under exactly the operations that are cheapest to perform: `cp`, `mv`, a
changed output flag, a second copy kept "just in case". The artifact that moves keeps its contents
and loses its expectation; the file that takes its place inherits an expectation it was never built
to satisfy. That is the 07-25 defect with a different mechanism.

WHAT A STAMP IS — AND WHAT IT DELIBERATELY IS NOT
--------------------------------------------------
The stamp is the BUILDER'S DECLARATION OF INTENT, written into the artifact at the moment it is
produced, by the code that produced it:

    "I am the as-trained caliber, because funding_derive.real_funding_ema does not normalise, on
     purpose, so this panel matches the panel the frozen heads were fitted on."

It is **NOT a measurement**. If the builder stamped what it measured, the gate would compare a
measurement against itself and pass forever — a tautology wearing a guard's clothes. The whole
value is that intent and reality are recorded by different mechanisms:

    stamp  = what this artifact CLAIMS to be   (declared by the builder, travels inside the file)
    gap    = what this artifact IS             (measured by assert_funding_dim from the channels)
    verdict = they must agree

⇒ So a builder that silently changes caliber (the 07-25 `build_wide_panel.py` fix reaching the live
  splice, say) still says `as_trained` in its stamp while the channels measure `corrected` — and the
  gate goes RED. That is the case this exists for.

ARTIFACTS THAT CANNOT BE STAMPED
--------------------------------
`exports/wide_dl_full.npz` is the panel the frozen king/s2 heads were TRAINED on, built 2026-07-11.
Rewriting it to add a stamp would rewrite the one artifact the whole guard chain treats as
immutable, and its blessed `file_sha256_16` with it. So it is not stamped. Its caliber is declared
in `engine/live/factor_version_registry.py::UNSTAMPED_ARTIFACT_CALIBER`, keyed by **the sha256 of
its contents** — which is a property of the artifact itself, survives any rename, and cannot be
inherited by a different file. Content-hash identity is the stamp an immutable artifact already has.

⇒ Resolution order, in `assert_funding_dim.declared_caliber`:
      1. stamp carried inside the file          (rebuilt artifacts; rename-proof)
      2. content-sha256 declaration in registry (immutable artifacts; rename- and rebuild-proof)
      3. nothing                                -> CANNOT JUDGE (exit 2), never a default
  Nothing in that order consults a filename or a path. A path is only ever used to OPEN the file.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import zipfile

import numpy as np

STAMP_KEY = "caliber_stamp"
SCHEMA = "panel_caliber_stamp/v1"
CALIBERS = ("as_trained", "corrected")


class StampError(ValueError):
    """A stamp is present but unusable. Deliberately distinct from 'no stamp': a malformed
    declaration is a thing that went wrong, and reporting it as absent loses that fact."""


def make(caliber: str, declared_by: str, why: str) -> dict:
    """Builder-side: returns kwargs to splat into `np.savez` alongside the data arrays.

        np.savez(f, **out, **panel_caliber_stamp.make("as_trained", __file__, "..."))

    `why` is required and not decorative. The two calibers exist on purpose and the reason a given
    artifact holds one of them is the only thing that lets a later reader tell a deliberate state
    from a leftover — that sentence is exactly what was missing on 2026-07-25.
    """
    if caliber not in CALIBERS:
        raise ValueError(f"caliber must be one of {CALIBERS}, got {caliber!r}")
    if not why or not str(why).strip():
        raise ValueError("a stamp without a reason is a label; state why this artifact holds "
                         "this caliber")
    payload = {
        "schema": SCHEMA,
        "funding_caliber": caliber,
        "declared_by": str(declared_by),
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "why": str(why),
        "kind": ("DECLARATION OF INTENT by the builder — NOT a measurement. "
                 "assert_funding_dim measures the channels and must agree with this."),
    }
    return {STAMP_KEY: np.array(json.dumps(payload, ensure_ascii=False))}


def has_stamp(path: str) -> bool:
    """True iff the npz contains the stamp member. Reads the zip directory only — no array is
    decompressed, so this is O(1) on a 1 GB panel."""
    try:
        with zipfile.ZipFile(path) as z:
            return f"{STAMP_KEY}.npy" in z.namelist()
    except (OSError, zipfile.BadZipFile):
        return False


def read(path: str):
    """The stamp this artifact carries, or None if it carries none.

    Raises StampError when a stamp is present but cannot be trusted (unparseable, wrong schema,
    unknown caliber). A corrupt declaration must not read as an absent one: absent means "nobody
    ever said", corrupt means "somebody said something and it is broken", and only the second one
    names a defect.
    """
    if not has_stamp(path):
        return None
    try:
        with np.load(path, allow_pickle=False) as z:
            raw = str(z[STAMP_KEY])
    except Exception as e:                                    # noqa: BLE001 - reported, not hidden
        raise StampError(f"{path}: stamp member present but unreadable: {type(e).__name__}: {e}")
    try:
        d = json.loads(raw)
    except Exception as e:                                    # noqa: BLE001
        raise StampError(f"{path}: stamp is not JSON: {type(e).__name__}: {e}")
    if not isinstance(d, dict) or d.get("schema") != SCHEMA:
        raise StampError(f"{path}: stamp schema {d.get('schema') if isinstance(d, dict) else d!r} "
                         f"!= {SCHEMA}")
    if d.get("funding_caliber") not in CALIBERS:
        raise StampError(f"{path}: stamp declares caliber {d.get('funding_caliber')!r}, "
                         f"not one of {CALIBERS}")
    return d


def sha256_16(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 22):
            h.update(chunk)
    return h.hexdigest()[:16]


def stamp_existing(path: str, caliber: str, declared_by: str, why: str) -> str:
    """Append a stamp to an ALREADY-WRITTEN npz, in place, without touching its arrays.

    ★ USE ON ARTIFACTS YOU ARE ALLOWED TO MODIFY ONLY. This appends a member to the zip, which
      changes the file's sha256 — so it must never be pointed at a panel whose bit-identity another
      guard asserts (`exports/wide_dl_full.npz` is blessed by hash in panel_caliber_manifest.json).
      For those, declare the caliber by content hash in the registry instead; that is what
      UNSTAMPED_ARTIFACT_CALIBER is for.
    """
    if has_stamp(path):
        raise StampError(f"{path} already carries a stamp; re-stamping would overwrite a "
                         f"declaration made by whoever built it")
    kw = make(caliber, declared_by, why)
    with zipfile.ZipFile(path, "a", compression=zipfile.ZIP_STORED) as z:
        import io
        buf = io.BytesIO()
        np.lib.format.write_array(buf, kw[STAMP_KEY], allow_pickle=False)
        z.writestr(f"{STAMP_KEY}.npy", buf.getvalue())
    return path


def describe(path: str) -> str:
    """One-line human summary, for logs."""
    try:
        d = read(path)
    except StampError as e:
        return f"{os.path.basename(path)}: STAMP BROKEN ({e})"
    if d is None:
        return f"{os.path.basename(path)}: no stamp (sha256_16 {sha256_16(path)})"
    return (f"{os.path.basename(path)}: stamped {d['funding_caliber']} "
            f"by {d['declared_by']} at {d['written_utc']}")


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        print(describe(p))
