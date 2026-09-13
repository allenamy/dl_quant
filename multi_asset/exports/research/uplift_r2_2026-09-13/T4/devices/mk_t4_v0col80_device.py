#!/usr/bin/env python3
"""mk_t4_v0col80_device.py (PREREG_T4 §6). Reads the PARITY device parity_replay_2026-09-12/devices/shadow_loop_v3_replay.py
(sha 4d3bc157…, never modified), copies it byte-identical into T4/devices/ (so the T4 driver imports the as-served device
from its own directory), and writes shadow_loop_v3_replay_v0col80.py = the same bytes with EXACTLY ONE line replaced
(count asserted == 1). Also copies combo_stage_replay.py byte-identical (sha f5ba9a82…). Writes the unified diff and a receipt.
The replaced line calls T4_COL80_ROW(st, anchor), a name the driver injects into the module (absent => NameError, fail loud)."""
import difflib, hashlib, io, json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); PAR = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/parity_replay_2026-09-12/devices"
SRC = PAR + "/shadow_loop_v3_replay.py"; SRC_SHA = "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42"
CSRC = PAR + "/combo_stage_replay.py"; CSRC_SHA = "f5ba9a8234ef0c01ee1aa5bdb0ebd87e8e7093c10b164e37f4fc10f97bc7f77b"
PREREG = os.path.dirname(HERE) + "/PREREG_T4_king_feature_skew_2026-09-13.md"; PREREG_SHA = "0f94b754c9ca4c6e65c3f2a63146dab7036f37862abd2210cbbfcef661aab4dd"
def sha_b(b): return hashlib.sha256(b).hexdigest()
assert sha_b(open(PREREG, "rb").read()) == PREREG_SHA
src_b = open(SRC, "rb").read(); assert sha_b(src_b) == SRC_SHA, "parity device changed"
csrc_b = open(CSRC, "rb").read(); assert sha_b(csrc_b) == CSRC_SHA, "parity combo device changed"
OLD = "    FE_ANCH[:, 80] = np.nan_to_num(fe_v[m], nan=0)\n"
NEW = "    FE_ANCH[:, 80] = np.nan_to_num(np.where(np.isfinite(fe_v[m]), T4_COL80_ROW(st, anchor)[m], np.nan), nan=0)   # T4: the only change\n"
src = src_b.decode("utf-8"); assert src.count(OLD) == 1, src.count(OLD)
out = src.replace(OLD, NEW)
served_p = HERE + "/shadow_loop_v3_replay.py"; v0_p = HERE + "/shadow_loop_v3_replay_v0col80.py"; combo_p = HERE + "/combo_stage_replay.py"
open(served_p, "wb").write(src_b); open(combo_p, "wb").write(csrc_b); io.open(v0_p, "w", encoding="utf-8").write(out)
assert sha_b(open(served_p, "rb").read()) == SRC_SHA and sha_b(open(combo_p, "rb").read()) == CSRC_SHA
diff = list(difflib.unified_diff(src.splitlines(keepends=True), out.splitlines(keepends=True), fromfile="shadow_loop_v3_replay.py", tofile="shadow_loop_v3_replay_v0col80.py", n=2))
open(HERE + "/shadow_loop_v3_replay_v0col80.diff", "w").writelines(diff)
changed = [l for l in diff if (l.startswith("+") or l.startswith("-")) and not (l.startswith("+++") or l.startswith("---"))]
assert len(changed) == 2 and changed[0] == "-" + OLD and changed[1] == "+" + NEW, changed
rc = dict(parity_device=SRC, parity_device_sha256=SRC_SHA, served_copy=served_p, served_copy_sha256=SRC_SHA, combo_copy=combo_p, combo_copy_sha256=CSRC_SHA,
          v0_device=v0_p, v0_device_sha256=sha_b(open(v0_p, "rb").read()), diff_changed_lines=len(changed) // 2, replaced_line_old=OLD.rstrip("\n"), replaced_line_new=NEW.rstrip("\n"),
          prereg_sha256=PREREG_SHA, generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), self_sha256=sha_b(open(os.path.abspath(__file__), "rb").read()))
json.dump(rc, open(os.path.dirname(HERE) + "/receipts/RECEIPT_T4_mk_v0col80_device.json", "w"), indent=1); print(json.dumps(rc, indent=1))
