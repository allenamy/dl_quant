"""Population-stable categorical draws for future paired training experiments.

Not wired into frozen trainers or production. Callers must first apply causal
admission and give each window a stable identity, not its current column index.
Do not include the treatment-arm name in a shared stream identifier.

For independent U_i, E_i=-log(U_i) is Exp(1); argmin(E_i / w_i) has probability
w_i/sum(w). Shared identities retain E_i when another window is added. Thus a
new winner can only be a newly added window, if old relative weights stay fixed.
Hash-derived uniforms are a deterministic pseudorandom implementation, not a
proof of real-world statistical independence. Finite-precision math is pinned
by the recorded runtime and tested on each actual population before use.
"""
import hashlib
import json
import math

SCHEMA = 'stable_window_exponential_race_v1'


def sample_ids(ids, weights, *, seed, stream, draw_ids):
    ids, weights, draw_ids = list(ids), list(weights), list(draw_ids)
    if not ids or len(ids) != len(weights):
        raise ValueError('empty or mismatched population')
    if any(type(s) is not str or not s.strip() for s in ids) or len(set(ids)) != len(ids):
        raise ValueError('window identities must be unique nonempty strings')
    if any(type(w) not in (int, float) or not math.isfinite(w) or w < 0 for w in weights) or not any(w > 0 for w in weights):
        raise ValueError('weights must be finite, nonnegative, with positive mass')
    if type(seed) is not int or seed < 0 or type(stream) is not str or not stream.strip():
        raise ValueError('invalid random stream identity')
    if not draw_ids or any(type(d) is not int or d < 0 for d in draw_ids) or len(set(draw_ids)) != len(draw_ids):
        raise ValueError('draw identities must be unique nonnegative integers')
    population = sorted((s, math.log(w)) for s, w in zip(ids, weights) if w > 0)
    result = []
    for draw in draw_ids:
        races = []
        for symbol, log_weight in population:
            payload = json.dumps([SCHEMA, seed, stream, draw, symbol], ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            bits = int.from_bytes(hashlib.sha256(payload).digest()[:8], 'big') >> 12
            # Exactly representable midpoint of a 52-bit bin, strictly inside (0,1).
            uniform = (bits + .5) / (2 ** 52)
            score = math.log(-math.log(uniform)) - log_weight
            races.append((score, symbol))
        result.append(min(races)[1])
    return tuple(result)
