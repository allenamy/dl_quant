"""NEWS P1 timing + column-restriction bitwise check for the as-is producer replay (one or a few anchors)."""
import os, sys, json, time, calendar
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import news_hist_features as H

W = H.W

def load_common():
    ax = np.load(f"{W}/work/cache_x0918r_axes.npz"); ts = ax["ts"].astype(np.int64)
    syms = [str(s) for s in ax["symbols"]]; chn = [str(c) for c in ax["ch"]]
    D = np.load(f"{W}/work/cache_x0918r_data.npy", mmap_mode="r")
    h = np.load("/workspace/axis_0919/x0918r/inputs/holefix2r_cells_x0918r.npz")
    o = np.lexsort((h["col"], h["row"])); holes = (h["row"][o].astype(np.int64), h["col"][o].astype(np.int64))
    mk = np.load("/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz")
    cfg = json.load(open(f"{W}/inputs/bundle_config.json"))
    crypto = np.load(f"{W}/receipts/P1_members_2025H2on.npz")["crypto"]
    return ts, syms, chn, D, holes, mk, cfg, crypto

def main():
    ts, syms, chn, D, holes, mk, cfg, crypto = load_common()
    anchors = [int(a) for a in sys.argv[1:]] or [calendar.timegm((2025, 9, 1, 0, 0, 0))]
    mts = mk["ts"].astype(np.int64)
    for A in anchors:
        cand = mk["mask"][int(np.searchsorted(mts, A))] & crypto
        t0 = time.time(); c0 = time.process_time()
        r = H.replay_anchor(A, D, ts, syms, chn, cand, {}, {}, cfg["params"], cfg, f"{W}/work", holes=holes)
        wall = time.time() - t0
        # children CPU (subprocesses) are not in process_time; report wall + self cpu
        print(json.dumps({"anchor": A, "utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(A)), "wall_s": round(wall, 1),
                          "self_cpu_s": round(time.process_time() - c0, 1), "n_members": int(len(r["m"])),
                          "X82": list(r["X82"].shape), "X89": list(r["X89"].shape), "king_X78": list(r["king_X78"].shape),
                          "x82_dtype": str(r["X82"].dtype), "x89_finite": float(np.isfinite(r["X89"]).mean())}), flush=True)
        np.savez_compressed(f"{W}/work/t_one_{A}.npz", **{k: v for k, v in r.items() if isinstance(v, np.ndarray)})

if __name__ == "__main__":
    main()
