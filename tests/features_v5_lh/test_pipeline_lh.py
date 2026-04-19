import numpy as np
import tempfile
import pathlib
from src.features_v5_lh.pipeline_lh import build_lh_npz_from_v4


def test_stride_and_input_len_transform():
    """Given V4 NPZ with window=600 stride=60 -> build LH NPZ with input_len=1800.

    For input_len=1800, pipeline needs 3 non-overlapping V4 windows → start=20
    → M = N - 20 LH windows produced.
    """
    tmpdir = tempfile.mkdtemp()
    src_npz = pathlib.Path(tmpdir) / "2024-01-01.npz"
    # Create synthetic V4-shaped NPZ
    N = 100  # windows for one day
    np.savez(
        str(src_npz),
        X=np.random.randn(N, 600, 5).astype(np.float32),
        X_raw=np.random.randn(N, 600, 20, 4).astype(np.float16),
        features=np.array(["f0", "f1", "f2", "f3", "f4"], dtype=object),
        regime_prior=np.random.randn(N, 6).astype(np.float32),
        timestamps=np.arange(N, dtype=np.int64) * 60 * 1_000_000,
        y_180=np.random.randn(N).astype(np.float32),
        y_mask_180=np.ones(N, dtype=np.uint8),
        y_600=np.random.randn(N).astype(np.float32),
        y_mask_600=np.ones(N, dtype=np.uint8),
    )
    dst_npz = pathlib.Path(tmpdir) / "2024-01-01_lh.npz"
    build_lh_npz_from_v4(src_npz, dst_npz, input_len=1800, kept_feature_indices=[0, 1, 3])
    out = np.load(str(dst_npz), allow_pickle=True)
    # Expect N - start = 100 - 20 = 80 LH windows
    assert out["X"].shape == (80, 1800, 3)
    assert out["X_raw"].shape == (80, 1800, 20, 4)
    assert "y_180" in out.files and "y_600" in out.files
    assert out["X"].dtype == np.float32


def test_stitch_is_three_nonoverlapping_windows():
    """LH window at anchor i = concat(V4[i-20], V4[i-10], V4[i]) full-length.

    Each V4 window is 600 one-second samples. LH input_len=1800 means the LH
    window is exactly three non-overlapping V4 windows end-to-end. We use a
    distinct scalar per V4 window so we can verify stitching preserves both
    window identity and ordering.
    """
    tmpdir = tempfile.mkdtemp()
    src_npz = pathlib.Path(tmpdir) / "day.npz"
    N = 50  # 50 V4 windows → M = N - 20 = 30 LH windows
    X = (np.arange(N)[:, None, None] * 1000 +
         np.arange(600)[None, :, None]).astype(np.float32)
    X = np.broadcast_to(X, (N, 600, 2)).copy()
    np.savez(
        str(src_npz),
        X=X,
        X_raw=np.random.randn(N, 600, 20, 4).astype(np.float16),
        features=np.array(["a", "b"], dtype=object),
        regime_prior=np.random.randn(N, 6).astype(np.float32),
        timestamps=np.arange(N, dtype=np.int64) * 60 * 1_000_000,
        y_180=np.random.randn(N).astype(np.float32),
        y_mask_180=np.ones(N, dtype=np.uint8),
        y_600=np.random.randn(N).astype(np.float32),
        y_mask_600=np.ones(N, dtype=np.uint8),
    )
    dst_npz = pathlib.Path(tmpdir) / "day_lh.npz"
    build_lh_npz_from_v4(src_npz, dst_npz, input_len=1800, kept_feature_indices=[0, 1])
    out = np.load(str(dst_npz))

    # First LH window (lh_idx=0, anchor=20): LH[0, :600] == V4[0], LH[0, 600:1200] == V4[10], LH[0, 1200:1800] == V4[20]
    assert np.allclose(out["X"][0, 0:600, :], X[0, :, :])
    assert np.allclose(out["X"][0, 600:1200, :], X[10, :, :])
    assert np.allclose(out["X"][0, 1200:1800, :], X[20, :, :])
    # Last LH timestep equals last timestep of anchor V4 window (lookahead-safe check)
    assert np.allclose(out["X"][0, -1, :], X[20, -1, :])
    # Last LH window (lh_idx=29, anchor=49): LH[29, 1200:1800] == V4[49]
    assert np.allclose(out["X"][29, 1200:1800, :], X[49, :, :])
    # Labels sliced from start
    assert out["y_600"].shape == (30,)
    assert np.allclose(out["y_600"], np.load(str(src_npz))["y_600"][20:])


def test_empty_output_when_day_too_short():
    """If source has fewer windows than start offset, output is empty but valid."""
    tmpdir = tempfile.mkdtemp()
    src_npz = pathlib.Path(tmpdir) / "short.npz"
    N = 10  # too short (needs >20 for input_len=1800)
    np.savez(
        str(src_npz),
        X=np.random.randn(N, 600, 3).astype(np.float32),
        X_raw=np.random.randn(N, 600, 20, 4).astype(np.float16),
        features=np.array(["a", "b", "c"], dtype=object),
        regime_prior=np.random.randn(N, 6).astype(np.float32),
        timestamps=np.arange(N, dtype=np.int64),
        y_600=np.random.randn(N).astype(np.float32),
        y_mask_600=np.ones(N, dtype=np.uint8),
    )
    dst_npz = pathlib.Path(tmpdir) / "short_lh.npz"
    build_lh_npz_from_v4(src_npz, dst_npz, input_len=1800, kept_feature_indices=[0, 1])
    out = np.load(str(dst_npz), allow_pickle=True)
    assert out["X"].shape[0] == 0
    assert out["y_600"].shape[0] == 0
