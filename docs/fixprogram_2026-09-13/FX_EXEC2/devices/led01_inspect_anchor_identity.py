#!/usr/bin/python3
"""LED-01 req. 5 (research-repo reader): prove the inspect_anchor.py fills-key change is an identity on history and a
fix on a collision. (1) Runs the ORIGINAL and the FIXED script (argv[1], argv[2]) with their executor root rewritten to a
READ-ONLY ledger copy (argv[3]) for each anchor slot in argv[5:], and diffs every output line that is computed from the
executor ledger (the '### anchor', 'orders n', 'post-only', 'requote_arm', 'placement arms', 'chase arms', 'fills n',
'readback', 'anchors row', 'daily_nav' lines). (2) Applies the two fills-key expressions to a synthetic cross-symbol
collision. Writes only argv[4] (receipt JSON).
Usage: /usr/bin/python3 led01_inspect_anchor_identity.py <orig.py> <fixed.py> <state_copy_root> <receipt.json> <A>..."""
import json, os, subprocess, sys, tempfile, hashlib
ORIG, FIXED, STATE_ROOT, OUT = sys.argv[1:5]
ANCHORS = [int(a) for a in sys.argv[5:]]
PREFIXES = ("### anchor", "orders n", "post-only", "requote_arm", "placement arms", "chase arms", "fills n", "readback",
            "  venue gross", "anchors row", "daily_nav")
tmp = tempfile.mkdtemp(prefix="led01_insp_")
fake_live = os.path.join(tmp, "dl_quant_live"); os.makedirs(fake_live)
os.symlink(STATE_ROOT, os.path.join(fake_live, "state"))
def patched(src_path, name):
    s = open(src_path, encoding="utf-8").read()
    assert s.count('L = "/Users/haosiyu/dl_quant_live"') == 1, src_path
    p = os.path.join(tmp, name); open(p, "w", encoding="utf-8").write(s.replace('L = "/Users/haosiyu/dl_quant_live"', f'L = "{fake_live}"'))
    return p
po, pf = patched(ORIG, "orig.py"), patched(FIXED, "fixed.py")
res = {"orig_sha256": hashlib.sha256(open(ORIG, "rb").read()).hexdigest(),
       "fixed_sha256": hashlib.sha256(open(FIXED, "rb").read()).hexdigest(), "state_root": STATE_ROOT, "anchors": {}}
for A in ANCHORS:
    outs = {}
    for tag, p in (("orig", po), ("fixed", pf)):
        r = subprocess.run(["/usr/bin/python3", "-B", p, str(A)], capture_output=True, text=True, timeout=300)
        lines = [l for l in r.stdout.splitlines() if l.startswith(PREFIXES)]
        outs[tag] = {"rc": r.returncode, "lines": lines, "stderr_tail": r.stderr[-300:]}
    res["anchors"][str(A)] = {"identical_ledger_lines": outs["orig"]["lines"] == outs["fixed"]["lines"],
                              "rc": [outs["orig"]["rc"], outs["fixed"]["rc"]],
                              "fills_line": [l for l in outs["fixed"]["lines"] if l.startswith("fills n")],
                              "orig": outs["orig"], "fixed": outs["fixed"]}
rows = [{"symbol": "AAAUSDT", "trade_id": 777, "fill_ts": 1.0}, {"symbol": "BBBUSDT", "trade_id": 777, "fill_ts": 2.0}]
old_keys = {r.get("trade_id") or (r["symbol"], r["fill_ts"]) for r in rows}
new_keys = {(r.get("symbol"), r.get("trade_id")) for r in rows}
res["collision"] = {"old_distinct": len(old_keys), "new_distinct": len(new_keys)}
json.dump(res, open(OUT, "w"), indent=1)
print("LED01_INSPECT_IDENTITY", {a: (v["identical_ledger_lines"], v["rc"], v["fills_line"][:1]) for a, v in res["anchors"].items()},
      "collision old/new distinct", res["collision"]["old_distinct"], res["collision"]["new_distinct"])
