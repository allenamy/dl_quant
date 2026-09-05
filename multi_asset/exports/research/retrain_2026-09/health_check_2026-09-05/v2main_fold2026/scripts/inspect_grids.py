import numpy as np, time, json
def ft(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
TO = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True)
TE = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True)
print("old targets keys", TO.files); print("ext targets keys", TE.files)
Eo = TO["E_ts"].astype(np.int64); Ee = TE["E_ts"].astype(np.int64)
print("old nA", len(Eo), ft(Eo[0]), "->", ft(Eo[-1]), "| ext nA", len(Ee), ft(Ee[0]), "->", ft(Ee[-1]))
print("ext prefix == old:", np.array_equal(Ee[:len(Eo)], Eo), "| symbols equal:", [str(x) for x in TO["symbols"]] == [str(x) for x in TE["symbols"]], "n_sym", len(TE["symbols"]))
yo = TO["yrs"].astype(int); ye = TE["yrs"].astype(int)
print("old yrs counts", {int(y): int((yo == y).sum()) for y in np.unique(yo)})
print("ext yrs counts", {int(y): int((ye == y).sum()) for y in np.unique(ye)})
te = np.where(ye == 2026)[0]; first_te = int(te[0]); EMB = 60
print("ext 2026 fold: first_te idx", first_te, ft(Ee[first_te]), "last", ft(Ee[te[-1]]), "n_test", len(te))
print("  embargo: train idx < first_te-EMB =", first_te - EMB, "-> max train E_ts", ft(Ee[first_te - EMB - 1]), "; first_te-60 anchor ts", ft(Ee[first_te - EMB]))
print("  gap (first test − max train E_ts) hours:", (Ee[first_te] - Ee[first_te - EMB - 1]) / 3600)
# also y4s overlap equality old vs ext
y4o = TO["y4s"]; y4e = TE["y4s"]
print("y4s shapes", y4o.shape, y4e.shape, "| overlap equal:", np.array_equal(np.nan_to_num(y4o, nan=-999), np.nan_to_num(y4e[:len(Eo)], nan=-999)))
d = np.abs(np.nan_to_num(y4o) - np.nan_to_num(y4e[:len(Eo)])); print("  y4s overlap maxabs diff", float(d.max()), "n_diff>1e-12", int((d > 1e-12).sum()))
# meta grids
for nm, p in [("meta_newprod", "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz"), ("v2ext_meta", "/workspace/data/wide_fea_v2ext_meta.npz"), ("port_w10 meta", "/workspace/port_w10/pod_backup_2026-08-21/wide_fea_hist_meta.npz")]:
    M = np.load(p, allow_pickle=True); E = M["E_ts"].astype(np.int64)
    print(nm, "keys", M.files, "nA", len(E), ft(E[0]), "->", ft(E[-1]), "y4 shape", M["y4"].shape)
P = np.load("/workspace/port_w10/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz", allow_pickle=True); pts = P["ts"].astype(np.int64)
print("port panel ts", len(pts), ft(pts[0]), "->", ft(pts[-1]), "n_sym", len(P["symbols"]))
U = np.load("/workspace/review_scratch/health_check/masks/umask_UPIT.npz", allow_pickle=True); uts = U["ts"].astype(np.int64)
print("umask_UPIT ts", len(uts), ft(uts[0]), "->", ft(uts[-1]), "mask shape", U["mask"].shape)
# preds finite ranges
for nm, p, E in [("old f10_V2MAIN_s42 (port_w10)", "/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s42.npy", Eo), ("old f10_V2MAIN_s42 (/workspace/f8_2026-08-22)", "/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy", Eo), ("ext f10_V2MAIN_s42", "/workspace/f8_ext/preds/f10_V2MAIN_s42.npy", Ee), ("ext f10_V2MAIN_s2027", "/workspace/f8_ext/preds/f10_V2MAIN_s2027.npy", Ee)]:
    A = np.load(p); fr = np.where(np.isfinite(A).any(1))[0]
    print(nm, A.shape, A.dtype, "finite rows", len(fr), ft(E[fr[0]]), "->", ft(E[fr[-1]]))
import hashlib
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
print("port_w10 old pred sha", sha("/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s42.npy"), "| /workspace/f8_2026-08-22 old pred sha", sha("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy"))
print("port_w10 old pred s2027 sha", sha("/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy"), "| /workspace/f8_2026-08-22 s2027 sha", sha("/workspace/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy"))
print("port_w10 dlw_targets sha", sha("/workspace/port_w10/dlw_2026-08-22/data/dlw_targets.npz"), "| /workspace/data/dlw_targets sha", sha("/workspace/data/dlw_targets.npz"))
# legs
LO = np.load("/workspace/data/f10v2_legs.npz", allow_pickle=True); LE = np.load("/workspace/f8_ext/data/f10v2_legs.npz", allow_pickle=True)
print("legs old keys", LO.files, {k: LO[k].shape for k in LO.files if hasattr(LO[k], 'shape')}); print("legs ext keys", LE.files, {k: LE[k].shape for k in LE.files if hasattr(LE[k], 'shape')})
for k in ("Z24", "ZFD", "WL"):
    a = LO[k]; b = LE[k][:len(Eo)]
    print(f"  {k}: old-prefix equal (nan-aware) {np.array_equal(np.nan_to_num(a, nan=-999), np.nan_to_num(b, nan=-999))}; maxabs {float(np.nanmax(np.abs(a - b)))}")
wl = LE["WL"]; frw = np.where(np.isfinite(wl[:, 0]))[0]; print("ext WL finite rows", len(frw), ft(Ee[frw[0]]), "->", ft(Ee[frw[-1]]), "WL mean by year 2026:", np.nanmean(wl[ye == 2026], 0))
