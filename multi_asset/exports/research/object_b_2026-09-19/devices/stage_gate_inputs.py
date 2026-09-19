#!/usr/bin/env python3
"""Stage the GATE F inputs from the production host (read-only) to pod2 /workspace/object_b_2026-09-19/gate_inputs (PREREG §3 S5).
Every file's sha256 is computed here BEFORE the copy; the pod side recomputes and must match (STAGE_MANIFEST.json holds the pod-side shas,
STAGE_MANIFEST_mac.json the Mac-side ones). Snapshot dirs are checked against their own SHA256SUMS first. target_live files that fall in the
object-A tar window (<= 2026-09-18 20Z) are checked against the tar manifest (production_overlap_archive_MANIFEST.json, tar 33910c01).
usage: python3 stage_gate_inputs.py <out_manifest_mac.json>"""
import hashlib, json, os, subprocess, sys, time

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; DQ = f"{HOME}/dl_quant_live"
POD = "pod2"; ST = "/workspace/object_b_2026-09-19/gate_inputs"
HERE = os.path.dirname(os.path.abspath(__file__)); RCPT = os.path.join(os.path.dirname(HERE), "..", "certified_path_design_2026-09-19", "receipts")
TAR_MAN = os.path.normpath(os.path.join(RCPT, "production_overlap_archive_MANIFEST.json"))
H4 = 14400
ANCH = sorted(int(d) for d in os.listdir(f"{WS}/state/snap") if d.isdigit() and os.path.exists(f"{WS}/state/snap/{d}/COMPLETE"))


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


files = []   # (src_abs, rel_in_stage)
for A in ANCH:
    d = f"{WS}/state/snap/{A}"
    r = subprocess.run(["shasum", "-a", "256", "-c", "--quiet", "SHA256SUMS"], cwd=d, capture_output=True, text=True)
    assert r.returncode == 0, (A, r.stdout, r.stderr)
    for f in ("aux.json", "rolling.npz", "leg_returns_live.json", "SHA256SUMS"): files.append((f"{d}/{f}", f"snap/{A}/{f}"))
    for sub, suf in (("target_live", ".json"), ("target_live", ".json.sha256"), ("target_live_king", ".json"), ("target_live_king", ".json.sha256"), ("target_combo", ".json")):
        files.append((f"{WS}/state/{sub}/{A}{suf}", f"archive/{sub}/{A}{suf}"))
    for Aw in (A - H4, A):
        files.append((f"{WS}/state/weights/{Aw}.npz", f"archive/weights/{Aw}.npz"))
    for leg in ("f10", "kc", "fc"):
        files.append((f"{WS}/fea171/state_H_{leg}_{A - H4}.npz", f"archive/fea171/state_H_{leg}_{A - H4}.npz"))
for n in ("dlw_features.py", "f8_higher_order_features.py", "xfer_ref.npz", "xfer_syms.npz"): files.append((f"{WS}/fea171/{n}", f"fea171/{n}"))
files.append((f"{WS}/fea171/f10_live_s42_np.npz", "model/f10_live_s42_np.npz"))
for n in ("external_book.py", "book_config.py"): files.append((f"{DQ}/live/{n}", f"reader/{n}"))
seen = {}; uniq = []
for s, r in files:
    if r in seen: continue
    seen[r] = s; uniq.append((s, r))
mac = {r: sha(s) for s, r in uniq}
# bind the tar window
tarman = {f["path"]: f["sha256"] for f in json.load(open(TAR_MAN))["files"]}
bind = {}
for r, h in mac.items():
    if r.startswith("archive/target_live/") or r.startswith("archive/target_live_king/") or r.startswith("archive/target_combo/"):
        k = r[len("archive/"):]
        if k in tarman: bind[r] = (tarman[k] == h)
assert all(bind.values()), {k: v for k, v in bind.items() if not v}
# stream to pod2 grouped by source root
subprocess.run(["ssh", POD, f"mkdir -p {ST}"], check=True)
for s, r in uniq:
    pass
import tarfile, io
buf = io.BytesIO(); tf = tarfile.open(fileobj=buf, mode="w")
for s, r in uniq: tf.add(s, arcname=r)
tf.close()
p = subprocess.run(["ssh", POD, f"tar --no-same-owner -xf - -C {ST}"], input=buf.getvalue(), capture_output=True)
print("tar rc", p.returncode, p.stderr.decode(errors="replace")[:600])   # success is decided by the sha re-verification below, not by tar's rc
doc = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "anchors": ANCH, "n_files": len(uniq), "files": mac, "sources": {r: s for s, r in uniq},
       "tar_33910c01_bound": {k: v for k, v in bind.items()}, "n_tar_bound": len(bind), "self_sha256": sha(os.path.abspath(__file__))}
json.dump(doc, open(sys.argv[1], "w"), indent=1)
# pod-side recompute
code = ("import hashlib,json,os;ST=%r;m=json.load(open(%r));"
        "got={r:hashlib.sha256(open(os.path.join(ST,r),'rb').read()).hexdigest() for r in m};"
        "bad=[r for r in m if got[r]!=m[r]];json.dump({'files':got,'mac_equal':not bad,'bad':bad},open(os.path.join(ST,'STAGE_MANIFEST.json'),'w'),indent=1);"
        "print('POD_VERIFY', 'OK' if not bad else 'BAD', len(got), bad[:5])") % (ST, f"{ST}/STAGE_MANIFEST_mac_files.json")
subprocess.run(["ssh", POD, f"cat > {ST}/STAGE_MANIFEST_mac_files.json"], input=json.dumps(mac).encode(), check=True)
subprocess.run(["ssh", POD, f"/workspace/venv/bin/python -c \"{code}\""], check=True)
print("STAGED", len(uniq), "files; anchors", ANCH[0], "..", ANCH[-1], "; tar-bound", len(bind))
