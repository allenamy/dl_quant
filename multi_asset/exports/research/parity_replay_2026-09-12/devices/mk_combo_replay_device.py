#!/usr/bin/env python3
"""Generate combo_stage_replay.py from the PRODUCTION fea171/combo_stage.py by once-only replacements:
(1) WS root from env WIDE_SHADOW_HOME (HERE = WS/fea171 = the replay's copy of models/states); (2) Telegram paging suppressed.
Everything else byte-identical. COMBO_LIVE=1 + COMBO_LIVE_DIR=<replay dir> puts the writer in its own rehearsal mode."""
import hashlib, io, json, os, sys, time
SRC = os.path.expanduser("~/wide_shadow/fea171/combo_stage.py"); OUT = sys.argv[1] if len(sys.argv) > 1 else "combo_stage_replay.py"
src = io.open(SRC, encoding="utf-8").read(); sha = hashlib.sha256(src.encode()).hexdigest()
out = src
a = 'HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; HERE = f"{WS}/fea171"'
assert out.count(a) == 1; out = out.replace(a, 'HOME = os.path.expanduser("~"); WS = os.environ["WIDE_SHADOW_HOME"]; HERE = f"{WS}/fea171"   # REPLAY')
i = out.find("    def _page(sev, msg):\n"); assert i > 0
j = out.find('            log("PAGE_FAIL", repr(_e)[:120])\n', i); assert j > 0; j += len('            log("PAGE_FAIL", repr(_e)[:120])\n')
assert out.count("    def _page(sev, msg):\n") == 1
out = out[:i] + '    def _page(sev, msg):\n        log(f"PAGE(SUPPRESSED, replay) {sev}: {str(msg)[:160]}")\n' + out[j:]
b = 'ai = int(np.searchsorted(rts, A, side="right")) - 1\nassert rts[ai] <= A < rts[ai] + 300, "锚未对齐滚动缓存"\n'
assert out.count(b) == 1
out = out.replace(b, b + 'if os.environ.get("REPLAY_TRUNCATE_CACHE") == "1":   # REPLAY: the live process at time A had no rows after A\n    rts = rts[:ai + 1]; RD = RD[:ai + 1]\n')
out = f'# REPLAY DEVICE generated {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} from production combo_stage.py sha256 {sha}; 3 replacements\n' + out
io.open(OUT, "w", encoding="utf-8").write(out)
print(json.dumps({"production_sha256": sha, "device": OUT, "device_sha256": hashlib.sha256(out.encode()).hexdigest()}))
