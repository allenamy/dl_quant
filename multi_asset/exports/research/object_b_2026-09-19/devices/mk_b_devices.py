#!/usr/bin/env python3
"""Object B (PREREG §1 / §3 S5–S6): generate the two combo-side devices from the IN-SERVICE fea171/combo_stage.py (sha 3520d363…) by exact,
once-only replacements asserted on the source. Run on the production host (read-only on ~/wide_shadow); writes only <out_dir>.

  combo_stage_replay_3520d363.py   the Phase-1 recipe (parity_replay_2026-09-12/devices/mk_combo_replay_device.py), unchanged:
      R1 WS from env WIDE_SHADOW_HOME; R2 Telegram paging suppressed; R3 REPLAY_TRUNCATE_CACHE=1 cuts the cache at A.
  f10_scorer_3520d363.py           the production file's lines 1..<the zf line> VERBATIM (+ R1 only), then an epilogue that dumps the
      per-member F10 scores (f10_pm over pm, okf) and exits 0. Everything the score depends on — 40-day cache tail, 171-feature
      pipeline (dlw_features.py + f8_higher_order_features.build(), need=True when the sandbox mini/ is empty), fund columns from
      aux ema/ledger_tail, model forward (L160-L176) — is the production text. The epilogue adds no computation.
usage: python3 mk_b_devices.py <out_dir> [<production combo_stage.py>]"""
import hashlib, io, json, os, sys, time

OUT = sys.argv[1]
SRC = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/wide_shadow/fea171/combo_stage.py")
PIN = "3520d36394fbe7b95a600af3becc32ca6bf754e53ce681e41d2a7d34887c6c99"
src = io.open(SRC, encoding="utf-8").read(); sha = hashlib.sha256(src.encode()).hexdigest()
assert sha == PIN, ("production combo_stage is not the pinned in-service version", sha)

R1a = 'HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; HERE = f"{WS}/fea171"'
R1b = 'HOME = os.path.expanduser("~"); WS = os.environ["WIDE_SHADOW_HOME"]; HERE = f"{WS}/fea171"   # REPLAY'


def once(s, a, b):
    n = s.count(a); assert n == 1, (n, a[:70]); return s.replace(a, b)


# ── combo replay device (Phase-1 recipe, byte-for-byte the same three replacements) ──
out = once(src, R1a, R1b)
i = out.find("    def _page(sev, msg):\n"); assert i > 0
j = out.find('            log("PAGE_FAIL", repr(_e)[:120])\n', i); assert j > 0; j += len('            log("PAGE_FAIL", repr(_e)[:120])\n')
assert out.count("    def _page(sev, msg):\n") == 1
out = out[:i] + '    def _page(sev, msg):\n        log(f"PAGE(SUPPRESSED, replay) {sev}: {str(msg)[:160]}")\n' + out[j:]
b = 'ai = int(np.searchsorted(rts, A, side="right")) - 1\nassert rts[ai] <= A < rts[ai] + 300, "锚未对齐滚动缓存"\n'
out = once(out, b, b + 'if os.environ.get("REPLAY_TRUNCATE_CACHE") == "1":   # REPLAY: the live process at time A had no rows after A\n    rts = rts[:ai + 1]; RD = RD[:ai + 1]\n')
combo = f'# REPLAY DEVICE generated {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} from production combo_stage.py sha256 {sha}; 3 replacements\n' + out

# ── F10 scorer device: verbatim prefix through the zf line, + R1, + dump epilogue ──
ZF = "zf = np.full(len(pm), np.nan); zf[okf] = rankdata(f10_pm[okf]) / max(okf.sum() - 1, 1) - 0.5\n"
k = src.find(ZF); assert k > 0 and src.count(ZF) == 1
prefix = src[:k + len(ZF)]
prefix = once(prefix, R1a, R1b)
n_prefix_lines = prefix.count("\n")
epi = ('# ═══ OBJECT-B SCORER EPILOGUE (generated; everything above is production text) ═══\n'
       'np.savez(os.environ["F10_SCORE_OUT"], anchor=np.int64(A), pm=pm.astype(np.int64), f10_pm=f10_pm.astype(np.float64), okf=okf,\n'
       '         model_sha=np.array(_F10_SHA), need_ran=np.array(bool(need)))\n'
       'log(f"F10_SCORER_DONE anchor {A} scored {int(okf.sum())}/{len(pm)} model {_F10_SHA[:12]} pipeline_ran {bool(need)}")\n'
       'sys.exit(0)\n')
scorer = (f'# OBJECT-B F10 SCORER generated {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} from production combo_stage.py sha256 {sha}: '
          f'lines 1..{n_prefix_lines} verbatim + R1 (WS from env) + dump epilogue\n') + prefix + epi

os.makedirs(OUT, exist_ok=True); rec = {"production_sha256": sha, "source": SRC}
for name, txt in (("combo_stage_replay_3520d363.py", combo), ("f10_scorer_3520d363.py", scorer)):
    io.open(os.path.join(OUT, name), "w", encoding="utf-8").write(txt)
    rec[name] = hashlib.sha256(txt.encode()).hexdigest()
rec["scorer_prefix_lines"] = n_prefix_lines
print(json.dumps(rec, indent=1))
