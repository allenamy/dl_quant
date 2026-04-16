import os, sys, tempfile, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_analyze_ridge_weights_produces_json():
    """Smoke test: script runs and writes a JSON with 'top_features' list."""
    with tempfile.TemporaryDirectory() as d:
        # Create 3 tiny fake NPZs
        for date in ["2024-01-01", "2024-01-02", "2024-01-03"]:
            rng = np.random.default_rng(42)
            N = 100
            X = rng.normal(size=(N, 300, 5)).astype(np.float32)
            y = (X[:, -1, 0] * 0.1 + rng.normal(size=N) * 0.001).astype(np.float32)
            np.savez_compressed(
                os.path.join(d, f"{date}.npz"),
                X=X,
                y=y,
                y_mask=np.ones(N, dtype=np.uint8),
                timestamps=np.arange(N, dtype=np.int64),
                features=np.array(["f0", "f1", "f2", "f3", "f4"], dtype=object),
            )

        out_path = os.path.join(d, "weights.json")
        # Import and call directly (script must expose `main(npz_dir, out_path)`)
        from scripts.analyze_ridge_weights import main
        main(npz_dir=d, out_path=out_path, top_k=5)

        with open(out_path) as f:
            report = json.load(f)
        assert "top_features" in report
        assert len(report["top_features"]) <= 5
        # Feature f0 has the planted signal — Ridge must put high weight on it
        feats = [r["feature"] for r in report["top_features"]]
        assert "f0" in feats[:2], f"planted-signal feature should be top-2, got {feats}"
    print("PASS: test_analyze_ridge_weights_produces_json")

if __name__ == "__main__":
    test_analyze_ridge_weights_produces_json()
