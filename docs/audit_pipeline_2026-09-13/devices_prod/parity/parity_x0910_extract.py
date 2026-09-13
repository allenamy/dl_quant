#!/usr/bin/env python3
"""parity_x0910_extract.py -- AUDIT_PROD P4/P10 input extraction on pod2 (CPU). READ-ONLY on every input; no statistic is computed.
Writes only /workspace/aud_prod_2026-09-13/parity/extract/{cache_slice_x0910.npz, king_x0910_rows.npz, dl_x0910_rows.npz, parity_x0910_extract.json}.

What is extracted (training-definition side of the train/serve parity audit):
  cache_slice_x0910.npz : pod 5m cache dlnative_5m_wide829_f16_holefix2_x0910.npz rows 2026-07-25 00:05Z .. 2026-09-11 00:00Z, all 829 names x 7 channels, float16 as stored
                          (streamed from the npz member data.npy; rows before the slice are skipped, never materialised)
  king_x0910_rows.npz   : king training features wide_fea_v4_x0910.npy (builder pod_fea_ext_clamp.py b9f9c728, r6 S6) for every meta anchor >= 2026-09-05 12Z:
                          the stored float16 rows FEA[i, members_i, :82] + members + E_ts + names
  dl_x0910_rows.npz     : DL training inputs of the same chain: dlw_targets_x0910.npz (pod_dlw_targets_raw.py d7c52823) E_row/E_ts/members/btcv/yrs for anchors
                          >= 2026-07-25 00Z; fea82 (dlw_hf3_x0910, pod_dlw_features_ext.py e86725cc) X/pair_a/pair_s and fea89 (f8_v4_x0910, pod_f8_build_ext.py f606bffa)
                          X for pairs whose anchor >= 2026-09-05 12Z; column names of both
Input shas are asserted against the r6 manifest / build reports (multi_asset/exports/research/uplift_2026-09-11/r6_MANIFEST_r6_extension.json, f8_build_report).
Launch: devices_prod/parity/parity_run_pod2.sh extract (verbatim command inside).
"""
import os, sys, json, time, hashlib, zipfile, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "env whitelist argv[1] required"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
T0 = time.time()
def log(*a): print("[%7.1fs]" % (time.time() - T0), *a, flush=True)
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
def U(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
R6 = "/workspace/uplift_2026-09-11/r6/out"
INPUTS = {
    "cache": ("/workspace/data/dlnative_5m_wide829_f16_holefix2_x0910.npz", "8115299410cd5e8df46ecc5ac7baf312d9f593d94f3b4c3dc46471bd37e00336"),
    "king_fea": (R6 + "/wide_fea_v4_x0910.npy", "048ea709eacbe30e1ddbe98c63577769ea3966213b2fc17462039c8c45d31a75"),
    "king_meta": (R6 + "/wide_fea_v4_meta_x0910.npz", "ec791d1f2fb455c3e73381b7f5f828384ed65dbd3c5e1ab3c62ea9f3d182f21d"),
    "dl_targets": (R6 + "/dlw_targets_x0910.npz", "5b628413d0c06d2a989c1ab624783238e7871a9f6a84675be372901a5fbb27de"),
    "fea82": (R6 + "/dlw_hf3_x0910/data/dlw_fea82.npz", "e837780390e4c77b97d6fce48dc46c489dc31668e0018f6e63859e2d0f43446b"),
    "fea89": (R6 + "/f8_v4_x0910/data/f8_fea89.npz", "d4a33cc3e5f4c0f7a494dd309a9dde06ca8f0ff68cec5c663afd8ae2bf21ec7d"),
    "fea82_report": (R6 + "/dlw_hf3_x0910/results/dlw_features_report.json", None),
    "fea89_report": (R6 + "/f8_v4_x0910/results/f8_build_report.json", None),
}
OUTD = "/workspace/aud_prod_2026-09-13/parity/extract"; os.makedirs(OUTD, exist_ok=True)
RC = {"self_sha256": sha(os.path.abspath(__file__)), "env": {"whitelist": sorted(WHITE), "actual": {k: os.environ[k] for k in sorted(os.environ)}},
      "python": sys.version.split()[0], "numpy": np.__version__, "argv": sys.argv, "inputs": {}, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
for k, (p, h) in INPUTS.items():
    g = sha(p); RC["inputs"][k] = {"path": p, "sha256": g}
    if h is not None: assert g == h, ("INPUT SHA MISMATCH", k, g)
rep82 = json.load(open(INPUTS["fea82_report"][0])); rep89 = json.load(open(INPUTS["fea89_report"][0]))
assert rep82["self_sha256"] == "e86725cc2768bb6265dd8fb2b3580629706166da012298768b1c0788e8f5a624" and rep82["fea_sha256"] == INPUTS["fea82"][1], "fea82 report binding"
assert rep89["self_sha256"] == "f606bffa620004f69ace3704ca19d8f3643b764e918f5eea5a4575b40587f07e" and rep89["fea89_sha256"] == INPUTS["fea89"][1] and rep89["fea82_sha256"] == INPUTS["fea82"][1], "fea89 report binding"
assert rep82["targets_sha256"] == INPUTS["dl_targets"][1] and rep89["targets_sha256"] == INPUTS["dl_targets"][1] and rep82["cache_sha256"] == INPUTS["cache"][1], "report input binding"
RC["report_bindings"] = {"fea82_builder": rep82["self_sha256"], "fea82_panel": rep82["panel_sha256"], "fea89_builder": rep89["self_sha256"]}
log("inputs verified")
T_CACHE0 = calendar.timegm((2026, 7, 25, 0, 5, 0)); T_ANCH0 = calendar.timegm((2026, 9, 5, 12, 0, 0)); T_HIST0 = calendar.timegm((2026, 7, 25, 0, 0, 0))

# ---- cache slice (streamed)
zf = zipfile.ZipFile(INPUTS["cache"][0])
with zf.open("symbols.npy") as f: CSYM = np.lib.format.read_array(f, allow_pickle=True)
with zf.open("ch.npy") as f: CCH = np.lib.format.read_array(f, allow_pickle=True)
with zf.open("ts.npy") as f: CTS = np.lib.format.read_array(f).astype(np.int64)
assert (np.diff(CTS) == 300).all(); r0 = int(np.searchsorted(CTS, T_CACHE0)); assert CTS[r0] == T_CACHE0
with zf.open("data.npy") as f:
    ver = np.lib.format.read_magic(f)
    shape, fortran, dtype = (np.lib.format.read_array_header_1_0(f) if ver == (1, 0) else np.lib.format.read_array_header_2_0(f))
    assert (not fortran) and dtype == np.float16 and shape[0] == len(CTS) and tuple(shape[1:]) == (829, 7), (shape, fortran, dtype)
    rowb = 829 * 7 * 2; skip = r0 * rowb
    while skip > 0:
        b = f.read(min(1 << 26, skip)); assert len(b) > 0; skip -= len(b)
    nrows = shape[0] - r0; buf = bytearray(nrows * rowb); mv = memoryview(buf); got = 0
    while got < len(buf):
        b = f.read(min(1 << 26, len(buf) - got)); assert len(b) > 0; mv[got:got + len(b)] = b; got += len(b)
    assert f.read(1) == b"", "trailing bytes after data.npy payload"
CD = np.frombuffer(buf, np.float16).reshape(nrows, 829, 7)
p_cache = OUTD + "/cache_slice_x0910.npz"
np.savez(p_cache, ts=CTS[r0:], data=CD, symbols=CSYM, ch=CCH)
RC["cache_slice"] = {"rows": int(nrows), "first": U(CTS[r0]), "last": U(CTS[-1]), "finite_cells": int(np.isfinite(CD).sum())}
del CD, buf, mv; log("cache slice", RC["cache_slice"])

# ---- king rows
KM = np.load(INPUTS["king_meta"][0], allow_pickle=True); KE = KM["E_ts"].astype(np.int64); KMS = KM["members"]; KNAMES = [str(n) for n in KM["names"]]
KF = np.load(INPUTS["king_fea"][0], mmap_mode="r"); assert KF.shape == (len(KE), 829, 82) and KF.dtype == np.float16, (KF.shape, KF.dtype)
ki = np.where(KE >= T_ANCH0)[0]
rows, mem_off, mems = [], [0], []
for i in ki:
    m = np.asarray(KMS[i], np.int64); mems.append(m); rows.append(np.array(KF[i][m, :], np.float16)); mem_off.append(mem_off[-1] + len(m))
p_king = OUTD + "/king_x0910_rows.npz"
np.savez(p_king, E_ts=KE[ki], meta_index=ki.astype(np.int64), offsets=np.array(mem_off, np.int64), members=np.concatenate(mems), X=np.concatenate(rows), names=np.array(KNAMES))
RC["king_rows"] = {"anchors": int(len(ki)), "first": U(KE[ki[0]]), "last": U(KE[ki[-1]]), "pairs": int(mem_off[-1]), "n_names": len(KNAMES)}
log("king rows", RC["king_rows"])

# ---- DL rows
TG = np.load(INPUTS["dl_targets"][0], allow_pickle=True); TE = TG["E_ts"].astype(np.int64); TMS = TG["members"]
ti = np.where(TE >= T_HIST0)[0]
t_off, t_mem = [0], []
for i in ti:
    m = np.asarray(TMS[i], np.int64); t_mem.append(m); t_off.append(t_off[-1] + len(m))
F82 = np.load(INPUTS["fea82"][0], allow_pickle=True); pa = F82["pair_a"].astype(np.int64); ps = F82["pair_s"].astype(np.int64)
assert np.all(np.diff(pa) >= 0) and pa.max() == len(TE) - 1
sel = TE[pa] >= T_ANCH0; X82 = np.array(F82["X"][sel], np.float16); n82 = [str(n) for n in F82["names"]]; del F82
F89 = np.load(INPUTS["fea89"][0], allow_pickle=True)
assert np.array_equal(F89["pair_a"].astype(np.int64), pa) and np.array_equal(F89["pair_s"].astype(np.int64), ps), "fea89 pairs != fea82 pairs"
X89 = np.array(F89["X"][sel], np.float32); n89 = [str(n) for n in F89["names"]]; meta89 = str(F89["meta_json"]); del F89
p_dl = OUTD + "/dl_x0910_rows.npz"
np.savez(p_dl, E_ts=TE[ti], E_row=TG["E_row"].astype(np.int64)[ti], target_index=ti.astype(np.int64), offsets=np.array(t_off, np.int64), members=np.concatenate(t_mem),
         btcv=TG["btcv"].astype(np.float32)[ti], yrs=TG["yrs"].astype(np.int64)[ti], pair_ts=TE[pa[sel]], pair_s=ps[sel], X82=X82, X89=X89, names82=np.array(n82), names89=np.array(n89),
         meta89_json=np.array(meta89), symbols=np.array([str(s) for s in TG["symbols"]]))
RC["dl_rows"] = {"target_anchors": int(len(ti)), "target_first": U(TE[ti[0]]), "target_last": U(TE[ti[-1]]), "pairs": int(sel.sum()), "pair_anchor_first": U(TE[pa[sel]].min()),
                 "pair_anchor_last": U(TE[pa[sel]].max()), "n82": len(n82), "n89": len(n89)}
log("dl rows", RC["dl_rows"])
RC["outputs"] = {os.path.basename(p): sha(p) for p in (p_cache, p_king, p_dl)}
RC["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); RC["wall_s"] = round(time.time() - T0, 1)
json.dump(RC, open(OUTD + "/parity_x0910_extract.json", "w"), indent=1)
log("DONE", json.dumps(RC["outputs"]))
