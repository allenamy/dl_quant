"""P4 item 1 -- MECHANISM. Runs the UNMODIFIED trainer (/workspace/pod_f10_train_ext.py, sha 93cc2cdf...)
under three torch determinism regimes, selected by DETMODE:
  off  : nothing changed (the in-service regime). Only prints the flag receipt.
  warn : torch.use_deterministic_algorithms(True, warn_only=True) -> every op WITHOUT a deterministic CUDA
         kernel emits a UserWarning naming itself. This is the ENUMERATION receipt.
  full : use_deterministic_algorithms(True) + cudnn.deterministic + benchmark off + TF32 off everywhere.
         Requires CUBLAS_WORKSPACE_CONFIG=:4096:8 in the environment (set by the caller).
  tf32 : ONLY TF32 off; nondeterministic kernels left in place. Separates "low precision" from "atomics".
The trainer file itself is NEVER modified: it is executed with runpy so __file__ (and therefore the
self_sha256 it stamps into its own report) is the real trainer path.
"""
import os, sys, runpy, warnings, torch

MODE = os.environ.get("DETMODE", "off")
warnings.simplefilter("always")
if MODE in ("warn", "full"):
    torch.use_deterministic_algorithms(True, warn_only=(MODE == "warn"))
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
if MODE in ("full", "tf32"):
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    try:
        torch.backends.cuda.matmul.fp32_precision = "ieee"
    except Exception as e:
        print("FP32PREC_SET_FAILED", repr(e), flush=True)

REC = {"DETMODE": MODE, "torch": torch.__version__, "cuda": torch.version.cuda,
       "cudnn_version": torch.backends.cudnn.version(),
       "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
       "matmul_allow_tf32": bool(torch.backends.cuda.matmul.allow_tf32),
       "cudnn_allow_tf32": bool(torch.backends.cudnn.allow_tf32),
       "cudnn_deterministic": bool(torch.backends.cudnn.deterministic),
       "cudnn_benchmark": bool(torch.backends.cudnn.benchmark),
       "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
       "CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
       "CUDA_LAUNCH_BLOCKING": os.environ.get("CUDA_LAUNCH_BLOCKING")}
try:
    REC["matmul_fp32_precision"] = str(torch.backends.cuda.matmul.fp32_precision)
except Exception:
    REC["matmul_fp32_precision"] = "n/a"
print("DET_ENV " + repr(REC), flush=True)
runpy.run_path("/workspace/pod_f10_train_ext.py", run_name="__main__")
