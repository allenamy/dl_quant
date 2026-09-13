#!/usr/bin/env python3
"""mk_t4b_v2col80_device.py (PREREG_T4b §5). Reads the PARITY combo device parity_replay_2026-09-12/devices/combo_stage_replay.py
(sha f5ba9a82…, never modified), copies it and the parity king-stage device byte-identical into T4b/devices/, and writes
combo_stage_replay_v2col80.py = the same bytes with EXACTLY ONE line replaced (count asserted == 1): the V2MAIN panel's
current-row fund_ema. With env T4B_COL80_NPZ unset the new line evaluates the original expression; set, it reads the value
for this anchor and column from that npz (array "A<anchor>", xfer_ref symbol order). Writes the unified diff and a receipt."""
import difflib, hashlib, io, json, os, time
HERE = os.path.dirname(os.path.abspath(__file__)); PAR = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/parity_replay_2026-09-12/devices"
CSRC = PAR + "/combo_stage_replay.py"; CSRC_SHA = "f5ba9a8234ef0c01ee1aa5bdb0ebd87e8e7093c10b164e37f4fc10f97bc7f77b"
KSRC = PAR + "/shadow_loop_v3_replay.py"; KSRC_SHA = "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42"
def sha_b(b): return hashlib.sha256(b).hexdigest()
cb = open(CSRC, "rb").read(); assert sha_b(cb) == CSRC_SHA, "parity combo device changed"
kb = open(KSRC, "rb").read(); assert sha_b(kb) == KSRC_SHA, "parity king device changed"
OLD = '            fe[-1, j] = float(est["acc"])\n'
NEW = '            fe[-1, j] = float(est["acc"]) if not os.environ.get("T4B_COL80_NPZ") else float(np.load(os.environ["T4B_COL80_NPZ"])["A%d" % A][j])   # T4b: the only change\n'
src = cb.decode("utf-8"); assert src.count(OLD) == 1, src.count(OLD)
out = src.replace(OLD, NEW)
for name, data in (("combo_stage_replay.py", cb), ("shadow_loop_v3_replay.py", kb)):
    open(HERE + "/" + name, "wb").write(data)
io.open(HERE + "/combo_stage_replay_v2col80.py", "w", encoding="utf-8").write(out)
assert sha_b(open(HERE + "/combo_stage_replay.py", "rb").read()) == CSRC_SHA and sha_b(open(HERE + "/shadow_loop_v3_replay.py", "rb").read()) == KSRC_SHA
diff = list(difflib.unified_diff(src.splitlines(keepends=True), out.splitlines(keepends=True), fromfile="combo_stage_replay.py", tofile="combo_stage_replay_v2col80.py", n=2))
open(HERE + "/combo_stage_replay_v2col80.diff", "w").writelines(diff)
changed = [l for l in diff if (l.startswith("+") or l.startswith("-")) and not (l.startswith("+++") or l.startswith("---"))]
assert len(changed) == 2 and changed[0] == "-" + OLD and changed[1] == "+" + NEW, changed
rc = dict(parity_combo_device=CSRC, parity_combo_sha256=CSRC_SHA, parity_king_device=KSRC, parity_king_sha256=KSRC_SHA,
          v2_device=HERE + "/combo_stage_replay_v2col80.py", v2_device_sha256=sha_b(open(HERE + "/combo_stage_replay_v2col80.py", "rb").read()),
          diff_changed_lines=len(changed) // 2, replaced_line_old=OLD.rstrip("\n"), replaced_line_new=NEW.rstrip("\n"),
          generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), self_sha256=sha_b(open(os.path.abspath(__file__), "rb").read()))
json.dump(rc, open(os.path.dirname(HERE) + "/receipts/RECEIPT_T4b_mk_v2col80_device.json", "w"), indent=1); print(json.dumps(rc, indent=1))
