import numpy as np, hashlib, sys
P = sys.argv[1]; TARGET = sys.argv[2]
with np.load(P, allow_pickle=False) as z:
    d = {k: np.ascontiguousarray(z[k]) for k in sorted(z.files)}

def h(parts):
    m = hashlib.sha256()
    for p in parts:
        m.update(p if isinstance(p, bytes) else str(p).encode())
    return m.hexdigest()

variants = {
    "name, dtype.str, str(shape), bytes  (no separators)": lambda k, a: [k, a.dtype.str, str(a.shape), a.tobytes()],
    "f'{k}|{dtype.str}|{shape}|' then bytes":              lambda k, a: ["%s|%s|%s|" % (k, a.dtype.str, a.shape), a.tobytes()],
    "f'{k}|{dtype.str}|{list(shape)}|' then bytes":        lambda k, a: ["%s|%s|%s|" % (k, a.dtype.str, list(a.shape)), a.tobytes()],
    "'|'.join([k,dtype.str,str(shape)]) then bytes":       lambda k, a: ["|".join([k, a.dtype.str, str(a.shape)]), a.tobytes()],
    "k + dtype.str + 'x'.join(shape) + bytes":             lambda k, a: [k, a.dtype.str, "x".join(map(str, a.shape)), a.tobytes()],
    "bytes only (schema ignored)":                          lambda k, a: [a.tobytes()],
    "per-array sha then sha of concatenation":              None,
}
print("target prefix :", TARGET)
hit = False
for lab, f in variants.items():
    if f is None:
        inner = "".join(hashlib.sha256(a.tobytes()).hexdigest() for a in d.values())
        v = hashlib.sha256(inner.encode()).hexdigest()
    else:
        parts = []
        for k, a in d.items():
            parts.extend(f(k, a))
        v = h(parts)
    m = v.startswith(TARGET)
    hit |= m
    print(("  MATCH " if m else "  no    ") + v[:16] + "  " + lab)
print()
print("keys present:", list(d))
print("REPRODUCED_FROM_WRITTEN_DEFINITION =", hit)
