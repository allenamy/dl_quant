"""fa_member_key.py — an INDEPENDENT array-bytes key for a family member's F10_OOF.npz, plus the schema assertion.

WHY THIS DEVICE EXISTS AS A FILE: the key was first produced by an inline command whose receipt described the
definition in prose -- "name | dtype.str | shape | C-order bytes". dlarch reproduced it, but only after trying SIX
readings: the `|` was descriptive, not a literal separator, and 5 of the 6 plausible readings give a different digest.
A key a third party cannot recompute is a password, not a check -- and the whole purpose of a second key is to answer
"did the DATA change or did the DEVICE change", which it cannot do if only one party can compute it.

So the definition now lives in the executable line below, and the receipt carries that line verbatim plus the
rejected readings, so a reproducer can self-check rather than guess.

usage: ... fa_member_key.py WL <out.json> <oof.npz> [<oof.npz> ...]
"""
import os, sys, json, hashlib, time
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT, FILES = sys.argv[2], sys.argv[3:]
EXPECTED_SCHEMA = ["E_ts", "P", "symbols"]

DEFN = ("h = sha256(); for k in sorted(z.files): a = ascontiguousarray(z[k]); "
        "h.update(k.encode()); h.update(str(a.dtype.str).encode()); h.update(str(a.shape).encode()); "
        "h.update(a.tobytes())  # NO separators; str(a.shape) is Python's default repr; keys sorted()")
REJECTED = {
    "literal_pipe_separators": "f'{k}|{dtype.str}|{shape}|' + bytes",
    "literal_pipe_with_list_shape": "same but shape via list()",
    "join_on_pipe": "'|'.join([k, dtype.str, str(shape)]) + bytes",
    "shape_joined_with_x": "shape via 'x'.join(...)",
    "bytes_only": "hash the raw bytes only, ignoring name/dtype/shape",
    "per_array_sha_then_concat": "sha each array, then hash the concatenation of those digests",
}


def arrays_key(p):
    z = np.load(p, allow_pickle=False)
    h = hashlib.sha256()
    for k in sorted(z.files):
        a = np.ascontiguousarray(z[k])
        h.update(k.encode()); h.update(str(a.dtype.str).encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest(), sorted(z.files)


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


rec = {"device": "fa_member_key.py", "self_sha256": sha_file(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "purpose": ("independent second key for family members, so that a later disagreement can distinguish "
                   "'the data changed' from 'one device changed'"),
       "definition_executable": DEFN,
       "readings_that_are_WRONG": REJECTED,
       "reproduced_by": "dlarch, 3/3 seeds, from the written definition (after eliminating the 5 wrong readings)",
       "expected_npz_schema": EXPECTED_SCHEMA,
       "schema_note": ("asserted here INDEPENDENTLY of dlarch's device: if only one party checks for schema drift, "
                       "that party's own error goes uncaught"),
       "members": {}}
bad = []
for p in FILES:
    if not os.path.exists(p):
        rec["members"][p] = {"status": "MISSING"}; bad.append(p); continue
    k, keys = arrays_key(p)
    ok = (keys == EXPECTED_SCHEMA)
    rec["members"][p] = {"my_arrays_key": k, "container_sha256": sha_file(p), "npz_keys": keys,
                         "schema_ok": bool(ok)}
    if not ok: bad.append(p)
rec["all_schema_ok"] = bool(not bad)
json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
assert os.path.exists(OUT), "receipt not written"
print("FA_MEMBER_KEY files=%d all_schema_ok=%s" % (len(FILES), rec["all_schema_ok"]), flush=True)
for p, v in rec["members"].items():
    if v.get("status"): print("  %-52s %s" % (os.path.basename(os.path.dirname(p)), v["status"])); continue
    print("  %-14s my_key %s  container %s  schema_ok %s"
          % (os.path.basename(os.path.dirname(p)), v["my_arrays_key"][:24], v["container_sha256"][:16], v["schema_ok"]), flush=True)
assert not bad, f"schema drift or missing files: {bad}"
