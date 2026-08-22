#!/usr/bin/env python3
"""tests_target_live_output — shadow_loop_v3.write_target_live (DESIGN_wide_live_deployment §3.1; v3 2026-08-22).

*** MOCK ONLY: a temp WIDE_SHADOW_HOME, synthetic weights, a synthetic npz. Never touches
    ~/wide_shadow/state, never starts the loop, never loads the bundle/booster, no network. ***

WHAT IT PROVES
  [1] shadow_loop_v3.py == shadow_loop_v2.py + the three declared blocks (WA (b) exit-on-leave with
      EXIT_NON_MEMBERS=True and keep = universe ∧ members, WA (a) tail scoring, the `universe` list):
      the only REMOVED lines are the five the declared hunks replace.
  [2] the file contract: <anchor>.json + .sha256 written; every field present and right (weights =
      the carried-forward vector's non-zero names, gross_norm = sum|w|, weights_sha = sha256 of the
      npz bytes, `universe` = symbols_live list with universe_sha = the SHARED recipe over it,
      booster_sha, written_utc, schema, producer); no tmp residue; sidecar is `shasum -c` compatible.
  [3] ★ the PAIR: the live reader (dl_quant_live/live/external_book.read_target) ACCEPTS this
      producer's output as-is, recomputes the same universe_sha over the list, SPLITS the weights
      into the in-universe book and the outside tail, and refuses a v2-style file (no list) — the
      contract cannot drift on one side without this going red.
  [8] v3 switches and pure functions: EXIT_ON_LEAVE / EXIT_NON_MEMBERS / TAIL_SCORE on; keep-mask =
      universe ∧ members in the source; exit_out_of_universe and score_tail_positions behave as WA's
      test_shadow_tail_fix T1/T2 specify (re-run here against the v3 module).
  [4] atomicity: a failed os.replace leaves NO final file (tmp+rename); a second write for the same
      anchor replaces both files and the reader sees the new content.
  [5] the call site in run_anchor: right after the npz write, wrapped in try/except (the shadow's own
      behaviour can never be altered by a failure here), logged as target_live / target_live_error.
  [6] keyless property intact: v2 still refuses to start with exchange credentials in env.
  [7] reader-side mutants through the producer's files: a flipped byte / missing sidecar are refused.

Run:  DL_QUANT_LIVE_LIVE=<path to the live repo's live/ dir (patched)>  python3 tests_target_live_output.py
      (default ~/dl_quant_live/live — i.e. AFTER the live patch is applied; the staging RUN uses the staged copy)
Exit 0 = all pass.
"""
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp(prefix="tlo_")
os.environ["WIDE_SHADOW_HOME"] = TMP                 # STATE_DIR -> TMP/state, never the real tree
os.environ["WIDE_SHADOW_BUNDLE"] = os.path.join(TMP, "bundle_unused")
sys.path.insert(0, HERE)
import numpy as np                                   # noqa: E402
import shadow_loop_v3 as SL                          # noqa: E402

LIVE_LIVE = os.environ.get("DL_QUANT_LIVE_LIVE", os.path.expanduser("~/dl_quant_live/live"))
sys.path.insert(0, LIVE_LIVE)
import external_book as EXT                          # noqa: E402  (the live-side reader; book_config beside it)

FAILS, N = [], [0]


def check(name, cond, detail=""):
    N[0] += 1
    print(f"  {'OK  ' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail else ''}", flush=True)
    if not cond:
        FAILS.append(name)


print("[1] v3 == v2 + the three declared blocks; only the five replaced lines are removed")
V2 = os.path.join(HERE, "shadow_loop_v2.py")
a = open(V2, encoding="utf-8").read().splitlines(True)
b = open(os.path.join(HERE, "shadow_loop_v3.py"), encoding="utf-8").read().splitlines(True)
d = list(difflib.unified_diff(a, b, n=0))
removed = [l[1:].strip() for l in d if l.startswith("-") and not l.startswith("---")]
added = [l[1:] for l in d if l.startswith("+") and not l.startswith("+++")]
ALLOWED_REMOVED = {
    'aux["H"] = {k: v for k, v in sig[last_t]["w"].items()}',                                   # WA (b) bootstrap
    'append_log({"e": "score", "anchor_ts": st.last_anchor, "gross_bps": round(gross, 3),',     # WA (a) score row
    '"net_bps": round(net, 3), "carry_bps": prev["carry_bps"], "cost_bps": prev["cost_bps"]})',
    '"universe_sha": universe_sha(live), "n_universe": len(live),',                              # v3 universe list
    '"producer": "shadow_loop_v2",',                                                              # v3 stamp
}
check("1a the ONLY removed lines are the five the declared hunks replace", set(removed) <= ALLOWED_REMOVED,
      sorted(set(removed) - ALLOWED_REMOVED)[:3])
joined = "".join(added)
for marker in ("EXIT_ON_LEAVE = True", "EXIT_NON_MEMBERS = True", "def exit_out_of_universe(",
               "keep &= _mm", "def score_tail_positions(", "TAIL_SCORE = True", '"universe": live,',
               '"producer": "shadow_loop_v3"', "forced_exit_n", "net_bps_total"):
    check(f"1b v3 carries {marker!r}", marker in joined)
check("1c the write_target_live helper and its call site survive from v2", "def write_target_live(" in "".join(b)
      and "_tl = write_target_live(" in "".join(b))

print("\n[2] the file contract")
PANEL = [f"S{i:02d}USDT" for i in range(10)]
LIVE = PANEL[:6]
CFG = {"symbols_panel": PANEL, "symbols_live": LIVE, "params": {"anchor_offset_min": 6},
       "_booster_sha": "deadbeef" * 8}
ANCHOR = 1787356800
sm = np.zeros(len(PANEL))
sm[0], sm[2], sm[5], sm[7] = 0.3, -0.2, 0.1, -0.2          # float64, as the shadow carries H
wnz = np.where(np.abs(sm) > 1e-9)[0]
os.makedirs(os.path.join(TMP, "state", "weights"), exist_ok=True)
NPZ = os.path.join(TMP, "state", "weights", f"{ANCHOR}.npz")
np.savez_compressed(NPZ, idx=wnz.astype(np.int32), val=sm[wnz].astype(np.float32), members=np.arange(8, dtype=np.int32))
os.environ.pop("SHADOW_OFFSET_MIN", None)
r = SL.write_target_live(CFG, ANCHOR, sm, wnz, NPZ)
OUT = os.path.join(TMP, "state", "target_live")
P = os.path.join(OUT, f"{ANCHOR}.json")
check("2a json + sidecar exist where the reader expects them; no tmp residue",
      os.path.exists(P) and os.path.exists(P + ".sha256") and not [f for f in os.listdir(OUT) if f.endswith(".tmp")],
      os.listdir(OUT))
raw = open(P, "rb").read()
doc = json.loads(raw)
check("2b schema / anchor_ts / producer / written_utc", doc["schema"] == "wide_target_v1" and doc["anchor_ts"] == ANCHOR
      and doc["producer"] == "shadow_loop_v3" and time.strptime(doc["written_utc"], "%Y-%m-%dT%H:%M:%SZ"))
check("2c weights = non-zero names of the carried-forward vector, float64 values",
      doc["weights"] == {"S00USDT": 0.3, "S02USDT": -0.2, "S05USDT": 0.1, "S07USDT": -0.2}, doc["weights"])
# ★ tolerance, not ==: Python ≥3.12 sum() is Neumaier-compensated, 3.9's is naive — the producer
#   (venv 3.14) and the reader (/usr/bin/python3 3.9) may differ in the last ulp; the reader's own
#   gross_norm check is relative 1e-6 for exactly this reason.
check("2d gross_norm = sum|w| (to 1e-12), n_names", abs(doc["gross_norm"] - 0.8) < 1e-12 and doc["n_names"] == 4)
check("2e weights_sha = sha256 of the npz bytes on disk", doc["weights_sha"] == hashlib.sha256(open(NPZ, "rb").read()).hexdigest())
check("2f booster_sha from the bundle MANIFEST value", doc["booster_sha"] == "deadbeef" * 8)
check("2g universe_sha = the SHARED recipe over symbols_live (n_universe carried)",
      doc["universe_sha"] == EXT.universe_sha(LIVE) and doc["n_universe"] == 6)
check("★ 2g2 the universe LIST travels in the file, order-preserving, and its sha IS universe_sha",
      doc["universe"] == LIVE and EXT.universe_sha(doc["universe"]) == doc["universe_sha"])
side = open(P + ".sha256").read()
check("2h sidecar = sha256(json bytes) + basename", side.split()[0] == hashlib.sha256(raw).hexdigest() and side.split()[1] == f"{ANCHOR}.json")
sc = subprocess.run(["shasum", "-a", "256", "-c", f"{ANCHOR}.json.sha256"], cwd=OUT, capture_output=True, text=True)
check("2i `shasum -a 256 -c` accepts the sidecar", sc.returncode == 0 and "OK" in sc.stdout, sc.stdout + sc.stderr)
check("2j the return carries the receipt (path, n, gross_norm, shas)", r["path"] == P and r["n_names"] == 4 and abs(r["gross_norm"] - 0.8) < 1e-9)
check("2k anchor_offset_min recorded from env/params", doc["anchor_offset_min"] == 6)

print("\n[3] ★ the PAIR: the live reader accepts the producer's output")
cfg = EXT.config({"book_source": "external", "target_leverage": 2.0,
                  "external_book": {"path": OUT, "max_age_min": 10, "anchor_offset_min": 23, "poll_grace_min": 0,
                                    "gross_mult": 1.0, "require_anchor_match": True, "universe_sha_pin": None,
                                    "booster_sha_pin": None, "min_notional_mult": 2.0, "on_unavailable": "ladder",
                                    "schema": "wide_target_v1"}})
check("3a the external config validates", cfg["source"] == "external", cfg.get("error"))
e = EXT.read_target(cfg, now=time.time(), nominal_ts=ANCHOR)
check("★ 3b read_target ACCEPTS the file as written", e["ok"] is True, (e.get("reason"), e.get("detail")))
check("3c ...and SPLITS: w = in-universe book (S07 ∉ symbols_live is the reported tail), gross_norm / shas decoded",
      e["w"] == {k: v for k, v in doc["weights"].items() if k in LIVE} and e["outside_names"] == ["S07USDT"]
      and e["n_outside_universe"] == 1 and abs(e["gross_in"] - 0.6) < 1e-12 and abs(e["gross_outside_frac"] - 0.2 / 0.8) < 1e-12
      and e["gross_norm"] == doc["gross_norm"] and e["weights_sha"] == doc["weights_sha"]
      and e["universe_sha"] == doc["universe_sha"] and e["booster_sha"] == doc["booster_sha"], (e.get("outside_names"), e.get("gross_in")))
# a v2-style file (no universe list) is REFUSED by the reader — the amendment is enforced both ways
_v2doc = dict(doc); _v2doc.pop("universe")
_raw2 = json.dumps(_v2doc, sort_keys=True, separators=(",", ":")).encode()
_P2 = os.path.join(OUT, f"{ANCHOR + 14400}.json")
open(_P2, "wb").write(_raw2); open(_P2 + ".sha256", "w").write(f"{hashlib.sha256(_raw2).hexdigest()}  x\n")
_e2 = EXT.read_target(cfg, now=time.time(), nominal_ts=ANCHOR + 14400)
check("★ 3c2 a v2-style file (no universe list) is refused as schema — both sides enforce the amendment",
      _e2["ok"] is False and _e2["reason"] == "schema" and "universe" in _e2["detail"], (_e2.get("reason"), _e2.get("detail")))
os.remove(_P2); os.remove(_P2 + ".sha256")
cfg_pin = EXT.config({"book_source": "external", "target_leverage": 2.0,
                      "external_book": {"path": OUT, "universe_sha_pin": EXT.universe_sha(LIVE), "booster_sha_pin": "deadbeef" * 8}})
check("3d pins computed by the reader's recipe match the producer's stamps",
      EXT.read_target(cfg_pin, now=time.time(), nominal_ts=ANCHOR)["ok"] is True)
vec = EXT.target_vector(e, sorted(doc["weights"]))
check("3e target_vector is unit-gross over the IN-universe book (S07 maps to 0)", abs(float(np.abs(vec).sum()) - 1.0) < 1e-12
      and vec[sorted(doc["weights"]).index("S07USDT")] == 0.0)

print("\n[4] atomicity + overwrite")
_replace = SL.os.replace
calls = {"n": 0}
def _boom(src, dst):
    calls["n"] += 1
    raise OSError("disk full (simulated)")
shutil.rmtree(OUT); os.makedirs(OUT)
SL.os.replace = _boom
try:
    try:
        SL.write_target_live(CFG, ANCHOR, sm, wnz, NPZ)
        raised = False
    except OSError:
        raised = True
finally:
    SL.os.replace = _replace
check("4a a failed rename raises and leaves NO final json/sidecar (tmp + rename)",
      raised and not os.path.exists(P) and not os.path.exists(P + ".sha256"), os.listdir(OUT))
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))                      # the .tmp residue of the simulated crash
SL.write_target_live(CFG, ANCHOR, sm, wnz, NPZ)
sm2 = sm.copy(); sm2[0] = 0.4
SL.write_target_live(CFG, ANCHOR, sm2, wnz, NPZ)
e2 = EXT.read_target(cfg, now=time.time(), nominal_ts=ANCHOR)
check("4b a second write for the same anchor replaces both files; the reader sees the NEW content",
      e2["ok"] and e2["w"]["S00USDT"] == 0.4 and abs(e2["gross_norm"] - 0.9) < 1e-12, e2.get("w"))
d1 = json.loads(open(P, "rb").read()); d1.pop("written_utc")
SL.write_target_live(CFG, ANCHOR, sm2, wnz, NPZ)
d2 = json.loads(open(P, "rb").read()); d2.pop("written_utc")
check("4c deterministic apart from written_utc (same inputs ⇒ same payload)", d1 == d2)

print("\n[5] the call site in run_anchor")
src = open(os.path.join(HERE, "shadow_loop_v3.py"), encoding="utf-8").read()
i_npz = src.find("np.savez_compressed(f\"{STATE_DIR}/weights/{anchor}.npz\"")
i_call = src.find("_tl = write_target_live(cfg, anchor, sm, wnz,")
i_sha = src.find("wsha = hashlib.sha256(json.dumps(st.prev_rec[\"sm\"])")
check("5a called right after the npz write and before the signal log line", 0 < i_npz < i_call < i_sha, (i_npz, i_call, i_sha))
seg = src[i_call - 200:i_call + 400]
check("5b wrapped in try/except; failure logged as target_live_error, success as target_live",
      "try:" in seg and "except Exception as _ex:" in seg and '"target_live_error"' in seg and '"e": "target_live"' in seg)
check("5c out dir defaults to STATE_DIR/target_live (beside weights/)", 'out_dir or f"{STATE_DIR}/target_live"' in src)

print("\n[6] keyless property intact")
check("6a main() still calls assert_no_keys() first", "def main():\n    assert_no_keys()" in src)
env = dict(os.environ, BINANCE_KEY="x", WIDE_SHADOW_HOME=TMP)
pr = subprocess.run([sys.executable, "-c", "import shadow_loop_v3 as S; S.assert_no_keys()"], cwd=HERE, env=env, capture_output=True, text=True)
check("6b assert_no_keys refuses with a credential in env (rc 2)", pr.returncode == 2 and "REFUSE_TO_START" in pr.stdout, pr.stdout[:80])

print("\n[7] reader-side mutants through the producer's files")
b = bytearray(open(P, "rb").read()); b[len(b) // 3] ^= 0x01; open(P, "wb").write(bytes(b))
check("7a one flipped byte ⇒ reader refuses (sha_mismatch)", EXT.read_target(cfg, now=time.time(), nominal_ts=ANCHOR)["reason"] == "sha_mismatch")
SL.write_target_live(CFG, ANCHOR, sm2, wnz, NPZ)
os.remove(P + ".sha256")
check("7b missing sidecar ⇒ reader refuses (sidecar_missing)", EXT.read_target(cfg, now=time.time(), nominal_ts=ANCHOR)["reason"] == "sidecar_missing")
SL.write_target_live(CFG, ANCHOR, sm2, wnz, NPZ)
check("7c restored ⇒ accepted again (the refusals above were the mutations)", EXT.read_target(cfg, now=time.time(), nominal_ts=ANCHOR)["ok"] is True)

print("\n[8] v3 switches and pure functions (WA test_shadow_tail_fix T1/T2 re-run against the v3 module)")
check("8a switches: EXIT_ON_LEAVE / EXIT_NON_MEMBERS / TAIL_SCORE on, forced cost 4.7",
      SL.EXIT_ON_LEAVE is True and SL.EXIT_NON_MEMBERS is True and SL.TAIL_SCORE is True and SL.FORCED_EXIT_COST_BPS == 4.7)
check("8b keep-mask = universe ∧ members in the source (WA's replacement fixed to an intersection)",
      "keep &= _mm" in src and "keep[:] = False; keep[m] = True" not in src)
_sm = np.array([0.01, -0.002, 0.0, 0.0015, -0.03]); _keep = np.array([True, False, True, False, True])
_sm2, _forced, _n = SL.exit_out_of_universe(_sm, _sm.copy(), _keep)
check("8c exit_out_of_universe zeroes only non-kept names; forced = 0.0035, n = 2",
      np.array_equal(_sm2, np.array([0.01, 0.0, 0.0, 0.0, -0.03])) and abs(_forced - 0.0035) < 1e-12 and _n == 2)
_T = 1787356800
def _fake(path, params, weight):
    if path.endswith("klines"):
        if params["symbol"] == "BADUSDT":
            return [[(_T - 3600) * 1000, 0, 0, 0, "1.0"]]
        return [[(_T - 3600 + k * 3600) * 1000, "0", "0", "0", ("100.0" if k == 0 else ("110.0" if k == 4 else "105.0"))] for k in range(5)]
    if path.endswith("fundingRate"):
        return [{"fundingTime": (_T + 4 * 3600) * 1000, "fundingRate": "0.0001"}, {"fundingTime": _T * 1000, "fundingRate": "0.9"}]
    return {"_err": "x"}
_r = SL.score_tail_positions(None, ["GOODUSDT", "BADUSDT"], {0: 0.002, 1: -0.001}, _T, fetch=_fake)
check("8d score_tail_positions: gross 2.0 bps, carry 0.002 bps (window-edge settlement excluded), bad name = unknown not 0",
      abs(_r["tail_gross_bps"] - 2.0) < 1e-9 and abs(_r["tail_carry_bps"] - 0.002) < 1e-9 and _r["tail_n"] == 1
      and abs(_r["tail_unknown_gross"] - 0.001) < 1e-12, _r)

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}   ({N[0]} checks)")
sys.exit(1 if FAILS else 0)
