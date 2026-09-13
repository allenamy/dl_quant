#!/usr/bin/env python3
"""t4_facts_caliber.py — pod2, READ-ONLY, CALIBER IDENTIFICATION ONLY (no return, no IC, no book number).
Run BEFORE the T4 prereg is written, to decide the arm set (task item B: "a sensitivity that fixes column 81 if its
training/serving calibers differ (check them)") and to date the skew for the fact table (task item A).

F1  column 81 (fund_now) in the 9-01 king training file wide_fea_v2ext.npy: on member cells with a panel row,
    share stored == float16(nan->0(f_fund_now)) (raw rate) vs share stored == float16(nan->0(f_fund_now*8/iv))
    (normalised), counted only where the two casts differ.
F2  booster feature_infos identification. LightGBM records [min:max] of each training feature. For the 9-01 booster
    (8d79186b) the training cells are exactly pod_export_bundle_v3.py L38-49 (anchors with year < 2026, members with
    finite meta y4, >= 50 per anchor). Report min/max over those cells of: stored col 80 / float16(v0) / float16(v1),
    stored col 81 / float16(raw now) / float16(now*8/iv), and the (anchor, symbol, iv) of each extreme.
F3  the same ranges on the CANONICAL August panel wide_panel_4h_v1.npz (the 08-16 booster 29ffaf58 was trained on the
    August wide_fea_v2ext.npy, which was overwritten on 09-01 (retrain MANIFEST D1); its member set is approximated by
    the 9-01 meta for anchors < 2026 — labelled APPROXIMATE).
"""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
T4 = "/workspace/uplift_r2_2026-09-13/T4"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
t0 = time.time()
FEA_P = "/workspace/data/wide_fea_v2ext.npy"; META_P = "/workspace/data/wide_fea_v2ext_meta.npz"
PAN_P = "/workspace/data/wide_panel_4h_v2ext.npz"; PAN1_P = "/workspace/data/wide_panel_4h_v1.npz"
BOOST = {"8d79186b_0901": "/workspace/shadow_bundle_v3/slow2026.txt"}
INPUTS = {p: sha(p) for p in (FEA_P, META_P, PAN_P, PAN1_P, BOOST["8d79186b_0901"])}
assert INPUTS[BOOST["8d79186b_0901"]] == "8d79186b6380132cb67684acf1ebfcdb2c53261c850f46a4908b06bfa7a81282"
assert INPUTS[FEA_P] == "f88b07205bf19870aefd1ea6f8eaf6f14e78f3587c973f36514b43ea691d4097"
def finfo(path):
    fn = fi = None
    with open(path) as f:
        for l in f:
            if l.startswith("feature_names="): fn = l.strip().split("=", 1)[1].split(" ")
            if l.startswith("feature_infos="): fi = l.strip().split("=", 1)[1].split(" ")
            if fn and fi: break
    return {k: fi[k] for k in (76, 77)}
F = np.load(FEA_P, mmap_mode="r"); M = np.load(META_P, allow_pickle=True)
names = [str(x) for x in M["names"]]; c80 = names.index("fund_ema"); c81 = names.index("fund_now"); assert (c80, c81) == (80, 81)
E = M["E_ts"].astype(np.int64); MS = M["members"]; Y4 = M["y4"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E])
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert keep.index(80) == 76 and keep.index(81) == 77
def panel(p):
    P = np.load(p, allow_pickle=True)
    return dict(ts=P["ts"].astype(np.int64), sym=[str(s) for s in P["symbols"]], v0=P["f_fund_ema"], v1=P["f_fund_ema_v1"], now=P["f_fund_now"], iv=P["f_fund_iv"])
PV = panel(PAN_P); P1 = panel(PAN1_P)
assert PV["sym"] == P1["sym"]
row2 = {int(t): j for j, t in enumerate(PV["ts"])}; row1 = {int(t): j for j, t in enumerate(P1["ts"])}
f16 = lambda a: np.float16(np.nan_to_num(a, nan=0.0))
def ext_init(): return dict(mn=np.inf, mx=-np.inf, amn=None, amx=None)
def upd(st, vals, i, names_idx, ivs):
    if len(vals) == 0: return
    k = int(np.argmin(vals)); v = float(vals[k])
    if v < st["mn"]: st["mn"] = v; st["amn"] = [time.strftime("%Y-%m-%d %HZ", time.gmtime(int(E[i]))), PV["sym"][int(names_idx[k])], float(ivs[k])]
    k = int(np.argmax(vals)); v = float(vals[k])
    if v > st["mx"]: st["mx"] = v; st["amx"] = [time.strftime("%Y-%m-%d %HZ", time.gmtime(int(E[i]))), PV["sym"][int(names_idx[k])], float(ivs[k])]
KEYS = ["stored80", "v0_f16", "v1_f16", "stored81", "now_raw_f16", "now_norm_f16"]
R2 = {k: ext_init() for k in KEYS}; R1 = {k: ext_init() for k in ["v0_f16", "v1_f16", "now_raw_f16", "now_norm_f16"]}
F1 = dict(n_cells_differ=0, eq_raw=0, eq_norm=0, n_cells_all=0, eq_raw_all=0, n_no_panel_row_anchors=0)
n_train_cells = 0; n_train_anchors = 0; n_anchor1_missing = 0
for i in range(len(E)):
    m = np.asarray(MS[i], dtype=np.int64); ok = np.isfinite(Y4[i, m])
    j = row2.get(int(E[i]))
    if j is None: F1["n_no_panel_row_anchors"] += 1; continue
    st80 = np.asarray(F[i, m, 80]); st81 = np.asarray(F[i, m, 81])
    raw = f16(PV["now"][j, m]); iv = PV["iv"][j, m]; ivn = np.where(np.isfinite(iv) & (iv > 0), iv, 8.0)
    nrm = f16(PV["now"][j, m] * (8.0 / ivn))
    dif = raw != nrm
    F1["n_cells_all"] += len(m); F1["eq_raw_all"] += int((st81 == raw).sum())
    F1["n_cells_differ"] += int(dif.sum()); F1["eq_raw"] += int((st81[dif] == raw[dif]).sum()); F1["eq_norm"] += int((st81[dif] == nrm[dif]).sum())
    if yrs[i] >= 2026 or ok.sum() < 50: continue
    mt = m[ok]; n_train_anchors += 1; n_train_cells += len(mt)
    ivt = PV["iv"][j, mt]; ivt8 = np.where(np.isfinite(ivt) & (ivt > 0), ivt, 8.0)
    cols = dict(stored80=np.asarray(F[i, mt, 80], np.float32), v0_f16=f16(PV["v0"][j, mt]).astype(np.float32), v1_f16=f16(PV["v1"][j, mt]).astype(np.float32),
                stored81=np.asarray(F[i, mt, 81], np.float32), now_raw_f16=f16(PV["now"][j, mt]).astype(np.float32), now_norm_f16=f16(PV["now"][j, mt] * (8.0 / ivt8)).astype(np.float32))
    for k in KEYS: upd(R2[k], cols[k], i, mt, ivt)
    j1 = row1.get(int(E[i]))
    if j1 is None: n_anchor1_missing += 1; continue
    iv1 = P1["iv"][j1, mt]; iv18 = np.where(np.isfinite(iv1) & (iv1 > 0), iv1, 8.0)
    c1 = dict(v0_f16=f16(P1["v0"][j1, mt]).astype(np.float32), v1_f16=f16(P1["v1"][j1, mt]).astype(np.float32), now_raw_f16=f16(P1["now"][j1, mt]).astype(np.float32), now_norm_f16=f16(P1["now"][j1, mt] * (8.0 / iv18)).astype(np.float32))
    for k in c1: upd(R1[k], c1[k], i, mt, iv1)
F1["share_eq_raw_on_differing_cells"] = F1["eq_raw"] / max(F1["n_cells_differ"], 1); F1["share_eq_norm_on_differing_cells"] = F1["eq_norm"] / max(F1["n_cells_differ"], 1)
F1["share_eq_raw_all_member_cells"] = F1["eq_raw_all"] / max(F1["n_cells_all"], 1)
F1["training_caliber_col81"] = ("raw" if F1["share_eq_raw_on_differing_cells"] >= 0.99 and F1["share_eq_norm_on_differing_cells"] <= 0.01 else ("normalised" if F1["share_eq_norm_on_differing_cells"] >= 0.99 else "NOT DECIDABLE"))
OUT = dict(F1_col81_training_caliber_wide_fea_v2ext=F1,
           F2_booster_0901=dict(feature_infos=finfo(BOOST["8d79186b_0901"]), train_anchors=n_train_anchors, train_cells=n_train_cells, ranges_v2ext_panel=R2),
           F3_canonical_aug_panel_APPROX_members=dict(ranges_wide_panel_4h_v1=R1, anchors_without_v1_panel_row=n_anchor1_missing))
RC = dict(self_sha256=sha(os.path.abspath(__file__)), inputs=INPUTS, result=OUT, env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}),
          built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(T4 + "/receipts/RECEIPT_T4_facts_caliber.json", "w"), indent=1, default=str)
print(json.dumps(OUT, indent=1, default=str)); print("DONE_t4_facts_caliber", RC["wall_s"])
