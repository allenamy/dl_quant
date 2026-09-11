"""r12 fix-up: (a) band bite rate restricted to the MEMBER set, measured as the observable
'this name did not move at all this anchor while the model wanted it to move';
(b) file-caliber matched turnover mean_t(turnover_file/gross_total) — the exact quantity the
r12_regime agent reports as 0.0540270 for the deployed cell (cross-instrument check)."""
import numpy as np, json, os, glob, calendar
R = "/workspace/uplift_2026-09-11/r12_smoothing"
TS_MAX = calendar.timegm((2026, 8, 30, 20, 0, 0)); WARM = 900
MT = np.load(R + "/dev/pod_backup_2026-08-21/wide_fea_hist_meta.npz", allow_pickle=True)
E = MT["E_ts"].astype(np.int64); members = MT["members"]
mrow = {int(t): members[i] for i, t in enumerate(E)}
out = {}
for f in sorted(glob.glob(R + "/arms/S_*_s42.npz")):
    tag = os.path.basename(f)[:-4]; Z = np.load(f, allow_pickle=True)
    cfg = json.loads(str(Z["config_json"])); rec = Z["rec"]; W = Z["W"]; T = Z["R12T"]
    ts = rec[:, 0].astype(np.int64); gt = rec[:, 5]
    m = (ts <= TS_MAX); m[:WARM] = False
    idx = np.where(m)[0]; idx = idx[idx > 0]
    nfroz = 0.0; nwant = 0.0; nmem = 0.0; nzero = 0.0
    for i in idx:
        mm = mrow[int(ts[i])]
        d_actual = np.abs(W[i, mm].astype(np.float64) - W[i - 1, mm].astype(np.float64))
        d_want = np.abs(T[i, mm].astype(np.float64) - W[i - 1, mm].astype(np.float64))
        want = d_want > 1e-12
        nmem += len(mm); nwant += want.sum(); nfroz += float((want & (d_actual <= 1e-12)).sum())
        nzero += float((d_actual <= 1e-12).sum())
    out[tag] = {"SMA": cfg["SMA"], "SBAND": cfg["SBAND"],
                "frac_member_names_frozen_given_want": nfroz / nwant,
                "frac_member_names_no_move": nzero / nmem,
                "turn_file_matched_meanratio": float((rec[m, 17] / gt[m]).mean()),
                "turn_file_raw_mean": float(rec[m, 17].mean())}
    print("%-22s a=%.2f b=%.1e frozen_given_want=%.4f no_move=%.4f turn_file_matched=%.6f" %
          (tag, cfg["SMA"], cfg["SBAND"], out[tag]["frac_member_names_frozen_given_want"],
           out[tag]["frac_member_names_no_move"], out[tag]["turn_file_matched_meanratio"]), flush=True)
json.dump(out, open(R + "/BITE12.json", "w"), indent=1); print("BITE_DONE")
