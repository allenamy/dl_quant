"""GATE S-BITWISE (signal layer): the injected PARITY matrix must re-rank to the device's own fund z
BITWISE on every panel row, and the round-1 ORDINAL builder must FAIL the same test (a gate that
cannot fail is not a gate)."""
import numpy as np, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xib_signal import xz, RZ
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
FE1 = np.asarray(PW["f_fund_ema_v1"], float); B = np.isfinite(FE1)
ZF_new = RZ(FE1, B)


def rz_old(M):
    out = np.full(M.shape, np.nan)
    for i in range(M.shape[0]):
        v = M[i]; ok = np.isfinite(v); n = ok.sum()
        if n >= 10: out[i, ok] = np.argsort(np.argsort(v[ok])) / max(n - 1, 1) - 0.5
    return out


ZF_old = rz_old(np.where(B, FE1, np.nan))


def eq(a, b):
    na = np.isnan(a); nb = np.isnan(b)
    return np.array_equal(na, nb) and np.array_equal(a[~na], b[~nb])


def rerank_fail_rows(Z, cast=None):
    bad = []
    for i in range(Z.shape[0]):
        z = Z[i] if cast is None else Z[i].astype(cast).astype(np.float64)
        if not eq(xz(z), xz(FE1[i])): bad.append(i)
    return bad


bn = rerank_fail_rows(ZF_new); bo = rerank_fail_rows(ZF_old); b32 = rerank_fail_rows(ZF_new, np.float32)
R = {"gate": "S_BITWISE_signal", "rows": int(FE1.shape[0]),
     "NEW_rankdata_rows_failing_rerank_identity": len(bn), "NEW_first_bad": bn[:5],
     "OLD_argsort_rows_failing_rerank_identity": len(bo), "OLD_first_bad": bo[:5],
     "NEW_float32_roundtrip_rows_failing": len(b32),
     "PASS": bool(len(bn) == 0 and len(bo) > 0)}
print(json.dumps(R, indent=1))
json.dump(R, open(os.environ.get("SIGGATE_OUT", "/workspace/uplift_2026-09-11/infra2/GATE_signal_parity.json"), "w"), indent=1)
sys.exit(0 if R["PASS"] else 3)
