"""t3_export_pod2.py -- pod2 CPU export for PREREG_T3_markout_curve_2026-09-13.md §1 / §3.
(1) accounting meta meta_newprod_v4_x0910.npz: E_ts / y4 / qvk / members for E in [2026-07-31 20:00Z, 2026-09-10 20:00Z]
    (y4 = PROD compounded [E, E+4h], RAW, unclipped; members -> boolean mask, no pickle in the output);
(2) pinned 5m cache dlnative_5m_wide829_f16_holefix2_x0910.npz: channel `ret5` BY NAME for rows ts in
    [2026-08-22 08:00Z, 2026-09-11 00:00Z] (only used to back-project P_E over <=5 bars, guarded in the analysis);
(3) symbol axis from the cache, asserted equal to wide_panel_4h_v2ext_x0910 and dlw_v4raw_x0910 dlw_targets (same as r21).
Full-file sha256 of every input recorded. Read-only on every input. ENV WHITELIST = EMPTY SET (asserted)."""
import calendar, hashlib, json, os, sys, time
_FORBID = ("CAL", "PHI", "CEM_Q", "LEGS", "FTRIM", "R12_NULL", "R21_DOSE", "FSEED", "FPRED", "PANEL_IN", "JUDGE", "W10_", "POD_", "DLW_", "KING_", "SEAT_", "UMASK")
_hit = sorted(k for k in os.environ if any(k.startswith(p) for p in _FORBID))
assert not _hit, f"E-0826-D forbidden env present: {_hit}"
import numpy as np
T3 = "/workspace/uplift_r2_2026-09-13/T3"
PREREG = f"{T3}/PREREG_T3_markout_curve_2026-09-13.md"
PREREG_SHA = "c7be850055160d7eeafe10fb859470f442d3f0552333ba290d9496357be8f8f6"
META = "/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz"
META_SHA_EXPECTED = "a8eb359701c71acfe853a295eb055bdbb04e1c29b6534ccdf23aeaff69907245"
CACHE = "/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz"
CACHE_SHA_EXPECTED_r21 = "8115299410cd5e8df46ecc5ac7baf312d9f593d94f3b4c3dc46471bd37e00336"
PANEL = "/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"
DLW = "/workspace/uplift_2026-09-11/r6/out/dlw_v4raw_x0910/data/dlw_targets.npz"

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 26), b""): h.update(c)
    return h.hexdigest()

assert sha(PREREG) == PREREG_SHA, "prereg sha mismatch"
SELF = sha(os.path.abspath(__file__))
t0 = time.time()
sm = sha(META); sc = sha(CACHE)
assert sm == META_SHA_EXPECTED, f"meta sha {sm}"
print("sha done", round(time.time() - t0, 1), "s", flush=True)

C = np.load(CACHE, allow_pickle=True)
ch = [str(x) for x in C["ch"]]; assert "ret5" in ch, ch
ci = ch.index("ret5")
ts = C["ts"].astype(np.int64)
sym = np.array([str(s) for s in C["symbols"]])
P = np.load(PANEL, allow_pickle=True); T = np.load(DLW, allow_pickle=True)
assert np.array_equal(sym, np.array([str(s) for s in P["symbols"]])), "cache vs panel symbol axis"
assert np.array_equal(sym, np.array([str(s) for s in T["symbols"]])), "cache vs dlw symbol axis"
lo = calendar.timegm((2026, 8, 22, 8, 0, 0)); hi = calendar.timegm((2026, 9, 11, 0, 0, 0))
r0 = int(np.searchsorted(ts, lo)); r1 = int(np.searchsorted(ts, hi, side="right"))
assert ts[r0] == lo and ts[r1 - 1] == hi and np.all(np.diff(ts[r0:r1]) == 300), "cache row grid"
RET = np.asarray(C["data"][r0:r1, :, ci], np.float32)

M = np.load(META, allow_pickle=True)
E = M["E_ts"].astype(np.int64)
assert M["y4"].shape[1] == len(sym) == M["qvk"].shape[1]
e0 = calendar.timegm((2026, 7, 31, 20, 0, 0)); e1 = calendar.timegm((2026, 9, 10, 20, 0, 0))
es = np.where((E >= e0) & (E <= e1))[0]
assert E[es[0]] == e0 and E[es[-1]] == e1 and np.all(np.diff(E[es]) == 14400), "meta E grid"
Y4 = np.asarray(M["y4"][es], np.float32); QVK = np.asarray(M["qvk"][es], np.float32)
MEM = np.zeros((len(es), len(sym)), dtype=bool)
mem_obj = M["members"]
for k, i in enumerate(es):
    MEM[k, np.asarray(mem_obj[i], dtype=np.int64)] = True

out = f"{T3}/out/t3_slice.npz"
os.makedirs(f"{T3}/out", exist_ok=True)
np.savez_compressed(out, symbols=sym, cache_ts=ts[r0:r1], ret5=RET, ret5_channel_index=np.int64(ci), channels=np.array(ch),
                    E_ts=E[es], y4=Y4, qvk=QVK, members_mask=MEM)
rc = {"device": os.path.abspath(__file__), "self_sha256": SELF, "prereg_sha256": PREREG_SHA, "env_whitelist": [],
      "python": sys.version.split()[0], "numpy": np.__version__, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
      "meta": {"path": META, "sha256": sm, "E_first": time.strftime("%FT%TZ", time.gmtime(int(E[es[0]]))),
               "E_last": time.strftime("%FT%TZ", time.gmtime(int(E[es[-1]]))), "n_anchors": int(len(es)),
               "y4_finite_frac": float(np.isfinite(Y4).mean()), "qvk_finite_frac": float(np.isfinite(QVK).mean()),
               "members_per_anchor_mean": float(MEM.sum(1).mean())},
      "cache": {"path": CACHE, "sha256": sc, "sha256_equals_r21_record": sc == CACHE_SHA_EXPECTED_r21, "channels": ch, "ret5_index": ci,
                "rows": [r0, r1, r1 - r0], "ts_first": time.strftime("%FT%TZ", time.gmtime(int(ts[r0]))),
                "ts_last": time.strftime("%FT%TZ", time.gmtime(int(ts[r1 - 1]))),
                "ret5_abs_max_in_slice": float(np.nanmax(np.abs(RET))), "n_cells_abs_ge_0p2999": int(np.nansum(np.abs(RET) >= 0.2999))},
      "symbol_axes_equal_cache_panel_dlw": True, "slice_path": out, "slice_sha256": sha(out)}
json.dump(rc, open(f"{T3}/out/EXPORT_T3.json", "w"), indent=1)
print(json.dumps(rc, indent=1)); print("EXPORT_DONE")
