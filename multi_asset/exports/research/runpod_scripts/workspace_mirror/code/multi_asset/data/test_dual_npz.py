import numpy as np, subprocess


def test_dual_npz_alignment():
    subprocess.run(
        ["/root/miniconda3/envs/hsy_v5push/bin/python",
         "multi_asset/data/build_dual_npz.py", "--days", "2025-02-10"],
        check=True, cwd="/mnt/storage/private/work_hsy/quant_research_multi_asset")
    z = np.load(
        "/mnt/storage/private/work_hsy/quant_research_multi_asset/"
        "data/npz_dual/2025-02-10.npz", allow_pickle=True)
    assert z["X_raw_spot"].shape == z["X_raw"].shape, (
        z["X_raw_spot"].shape, z["X_raw"].shape)
    assert z["X"].shape[-1] == 64
    assert z["y_600"].shape[0] == z["X"].shape[0] == z["X_raw_spot"].shape[0]
    ts = z["timestamps"]
    assert (np.diff(ts) > 0).all() and ts.max() > 2e12   # us, increasing
    assert np.isfinite(z["X_raw_spot"]).mean() > 0.99
