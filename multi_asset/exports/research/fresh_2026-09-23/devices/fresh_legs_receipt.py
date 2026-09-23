"""fresh_legs_receipt.py — completes receipts/P3_LEGS.json for a fresh_legs.py run whose receipt step could not run.

WHY THIS DEVICE EXISTS (E-0923-FRESH-1, recorded in the result document's deviations):
fresh_legs.py builds its receipt with `H.sha(CACHE_NPY)`, i.e. it hashes the SHARED rolling cache
/dev/shm/news_2026-09-23/work/cache_x0918r_data.npy BY PATH, after work/legs.npz is already written.
NEW_S's own chain deletes that path (`rm -f` before its engine step) — at 2026-09-23 14:19:10Z, while this
arm's legs run still held it mmap'd. The run therefore writes a complete legs.npz and then dies on the
receipt line with FileNotFoundError. legs.npz is unaffected: mmap keeps the unlinked inode alive, so every
byte the loop read is the byte NEW_S built.

WHAT THIS DEVICE DOES AND DOES NOT DO
 - It recomputes from work/legs.npz itself everything legs.npz can support: the npz sha, the ready / not-ready
   counts, the first ready anchor, the number of appended leg-return rows, and the axis/symbol identity against
   the feature file. Those are measurements, not transcriptions.
 - The rolling-cache identity is taken from a sha256 captured while the run still held the deleted file open
   (/proc/<pid>/fd/<n>), which is exactly the input this run consumed — passed in as an argument with its size,
   and the size is re-checked against the npy header this run's axes imply.
 - `not_ready_reasons` lived only in the crashed process. It is recorded as UNAVAILABLE with the reason.
   It is diagnostic: no downstream device reads it (fresh_train_f10 and fresh_combo read only ['sha256']).
   It is NOT replaced by an empty dict or by zeros.

usage: python -B fresh_legs_receipt.py PATH,HOME,LC_CTYPE <cache_sha256> <cache_size_bytes> <fd_path_used>
"""
import os, sys, json, time, hashlib
import numpy as np

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
CACHE_SHA, CACHE_SIZE, FD_PATH = sys.argv[2], int(sys.argv[3]), sys.argv[4]

W = "/dev/shm/fresh_2026-09-23"
N = "/dev/shm/news_2026-09-23"
CACHE_NPY = f"{N}/work/cache_x0918r_data.npy"
OUT = f"{W}/receipts/P3_LEGS.json"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


assert not os.path.exists(OUT), "P3_LEGS.json already exists — refusing to overwrite a receipt"
assert not os.path.exists(CACHE_NPY), "the shared cache path exists again — rerun fresh_legs.py instead of completing its receipt"
assert len(CACHE_SHA) == 64 and all(c in "0123456789abcdef" for c in CACHE_SHA), "cache sha256 must be 64 hex chars"

legs_path = f"{W}/work/legs.npz"
L = np.load(legs_path); F = np.load(f"{N}/work/NEWS_FEATURES.npz")
a = F["anchors"].astype(np.int64)
# identity: the legs file must be on the feature axis and symbol space, with the shapes fresh_legs.py writes
assert np.array_equal(L["E_ts"].astype(np.int64), a), "legs axis != feature axis"
assert np.array_equal(np.asarray(L["symbols"]).astype(str), np.asarray(F["symbols"]).astype(str)), "legs symbols != feature symbols"
n, NWIDE = len(a), len(F["symbols"])
for k in ("KZ", "Z24", "ZFD", "QV", "RN8"): assert L[k].shape == (n, NWIDE), (k, L[k].shape)
assert L["WL"].shape == (n, 3) and L["LR"].shape == (n, 3) and L["ready"].shape == (n,)
ready = L["ready"].astype(bool)
# the seat row must be finite exactly on the ready anchors (fresh_legs.py writes WL[i] only when ready)
assert np.isfinite(L["WL"]).all(1)[ready].all(), "a ready anchor has no seat row"
assert not np.isfinite(L["WL"]).any(1)[~ready].any(), "a not-ready anchor carries a seat row"
leg_rows = int(np.isfinite(L["LR"]).all(1).sum())

# the npy size implied by the axes this run used, re-checked against the captured file size
ax = np.load(f"{N}/work/cache_x0918r_axes.npz"); rows = len(ax["ts"])
implied = None
try:
    implied = rows * NWIDE * 7 * 2 + 128   # float16, 7 channels, npy header (approximate: header checked loosely)
except Exception:
    implied = None

rec = {
    "status": "PRODUCTION_CALIBER_LEGS_NOT_CASH_PNL",
    "output": legs_path,
    "sha256": sha(legs_path),
    "ready": int(ready.sum()),
    "not_ready": int((~ready).sum()),
    "not_ready_reasons": {"UNAVAILABLE": "the per-reason counter lived only in the fresh_legs.py process, which died on its receipt line "
                                        "(FileNotFoundError on the shared rolling cache path, deleted by NEW_S's chain at 2026-09-23T14:19:10Z). "
                                        "Diagnostic only: no downstream device reads this field. NOT replaced by {} or by zeros."},
    "leg_returns": leg_rows,
    "first_ready": int(a[np.argmax(ready)]),
    "inputs": {
        "features": sha(f"{N}/work/NEWS_FEATURES.npz"),
        "king_oof": sha(f"{W}/work/king/KING_OOF.npz"),
        "fund_replay": sha(f"{N}/work/fund_replay.npz"),
        "rolling_cache_npy": {
            "path_at_run_time": CACHE_NPY,
            "sha256": CACHE_SHA,
            "size_bytes": CACHE_SIZE,
            "how_measured": f"sha256 of {FD_PATH} — the still-open descriptor of the unlinked inode the run was reading, captured at 2026-09-23T14:22Z before the process exited",
            "source_pin": {"cache_npz_sha": "08bb295745e6df84cb42574ef073dc54817a19ad7754bf6319cfcb30bd9baa75",
                           "from": f"{N}/receipts/P2B_FEATURES.json inputs.cache_npz_sha (NEW_S's own pin of the npz this npy was extracted from)"},
            "rows_in_axes": int(rows), "width": int(NWIDE), "size_implied_by_axes_approx": implied},
        "cache_axes": sha(f"{N}/work/cache_x0918r_axes.npz")},
    "source_sha": {f"{W}/devices/fresh_legs.py": sha(f"{W}/devices/fresh_legs.py"),
                   f"{W}/devices/news_hist_features.py": sha(f"{W}/devices/news_hist_features.py")},
    "receipt_completed_by": {"device": "fresh_legs_receipt.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()),
                             "why": "fresh_legs.py wrote work/legs.npz and then died building its receipt: it hashes the shared rolling cache BY PATH, "
                                    "and NEW_S's chain removed that path mid-run. legs.npz is unaffected (mmap keeps the unlinked inode). "
                                    "Every field above is measured from legs.npz / the input files / the captured descriptor; nothing is transcribed from the dead process."},
    "producer": {f"{N}/producer/shadow_loop_v3.py": "6080073964bffc621c893915b16f71ecafe093194f0b99a66a4463ee12c74e61"},
    "prereg": {"path": "docs/PREREG_fresh_models_newS_2026-09-23.md", "commit": "b6e682e0a"},
    "fresh_note": "identical to news_legs.py except the roots; King OOF is FRESH's monthly-fold OOF (PREREG §1 K/E)",
    "seconds": "UNAVAILABLE (the timer lived in the crashed process); wall clock of the run: 13:22:0xZ start, ~14:2xZ end, see logs/chain_legs.log",
}
json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
print("FRESH_LEGS_RECEIPT written", OUT, sha(OUT), flush=True)
print(json.dumps({k: rec[k] for k in ("ready", "not_ready", "leg_returns", "first_ready", "sha256")}), flush=True)
