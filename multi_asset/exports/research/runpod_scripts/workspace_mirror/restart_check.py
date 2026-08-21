#!/usr/bin/env python3
"""RunPod 重开后【第一件要跑的东西】—— 环境自检。

放在 /workspace/restart_check.py (volume, 停机保留)。
用法: python3 /workspace/restart_check.py

★ 为什么需要它: 停机会清空 container disk(overlay, 30G)。/workspace 是 volume 会保留,
  但**解释器与依赖若装在容器层就会回到镜像的初始状态**。而其中最阴的一条是:
  记忆 `feedback_verify_cudnn_not_just_cuda` —— dev 版 torch 可能【有 CUDA 没 cuDNN】,
  Conv1d 慢 100-500 倍, 而 `torch.cuda.is_available()` 照样返回 True。
  ⇒ **只查 CUDA 不够, 必须真跑一次 Conv1d 计时。**
"""
import sys, os, time, json, subprocess

FAIL = []
WARN = []


def ok(msg):   print(f"  ✓ {msg}")
def bad(msg):  FAIL.append(msg); print(f"  ✗ {msg}")
def warn(msg): WARN.append(msg); print(f"  ! {msg}")


print("═" * 70)
print("① 解释器与依赖")
print(f"  python {sys.version.split()[0]}  @ {sys.executable}")
for mod, need in [("numpy", True), ("pandas", True), ("torch", True),
                  ("sklearn", False), ("scipy", False)]:
    try:
        m = __import__(mod)
        ok(f"{mod} {getattr(m, '__version__', '?')}")
    except ImportError:
        (bad if need else warn)(f"{mod} 缺失")

print("\n② volume 与关键件")
if not os.path.ismount("/workspace"):
    bad("/workspace 不是挂载点 —— volume 没挂上, 停手")
else:
    ok("/workspace 已挂载")
import shutil
t, u, f = shutil.disk_usage("/workspace")
print(f"  容量 {t/2**30:.0f}G  已用 {u/2**30:.0f}G  余 {f/2**30:.0f}G")
if u/2**30 < 100:
    bad(f"已用仅 {u/2**30:.0f}G —— 预期约 145G, volume 可能是空的(被 terminate 过?)")
for p in ["/workspace/data/wide_dl_pm32_hz.npz", "/workspace/exports_train",
          "/workspace/code/multi_asset", "/workspace/champion_run.sh"]:
    (ok if os.path.exists(p) else bad)(f"{p}")

print("\n③ GPU")
try:
    import torch
    print(f"  torch {torch.__version__}  cuda_available={torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        bad("CUDA 不可用")
    else:
        ok(f"GPU: {torch.cuda.get_device_name(0)}  "
           f"{torch.cuda.get_device_properties(0).total_memory/2**30:.0f}G")
        cud = torch.backends.cudnn.is_available()
        ver = torch.backends.cudnn.version()
        (ok if cud else bad)(f"cuDNN available={cud} version={ver}")

        # ★★ 真跑一次 Conv1d —— 这才是能抓住"有CUDA没cuDNN"的那个测试
        x = torch.randn(256, 64, 168, device="cuda")
        conv = torch.nn.Conv1d(64, 64, 3, padding=1).cuda()
        for _ in range(3):
            conv(x)
        torch.cuda.synchronize()
        t0 = time.time()
        for _ in range(50):
            conv(x)
        torch.cuda.synchronize()
        ms = (time.time() - t0) / 50 * 1000
        print(f"  Conv1d(256×64×168, k3) × 50: {ms:.2f} ms/次")
        if ms > 5.0:
            bad(f"Conv1d {ms:.1f} ms —— 正常应 <2ms。★ 这是 cuDNN 缺失的签名(慢 100-500×), "
                f"而 cuda_available 仍会是 True。不要开始训练。")
        elif ms > 2.0:
            warn(f"Conv1d {ms:.1f} ms 偏慢, 记录但不阻塞")
        else:
            ok(f"Conv1d {ms:.2f} ms —— 正常")
except Exception as e:
    bad(f"torch 检查异常: {type(e).__name__}: {e}")

print("\n④ 面板可读性(不只是文件存在)")
try:
    import numpy as np
    z = np.load("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
    print(f"  keys: {len(z.files)}  ts {z['ts'].shape}  MEMBER110 {z['MEMBER110'].shape}")
    fin = np.isfinite(z["Y4"]).mean()
    (ok if fin > 0.05 else bad)(f"Y4 有限格 {fin:.4f}")
except Exception as e:
    bad(f"面板读取失败: {type(e).__name__}: {e}")

print("\n⑤ 冠军配方三陷阱(只查脚本是否仍固化, 不训练)")
try:
    s = open("/workspace/champion_run.sh").read()
    for k, lbl in [("--xattn", "xattn 显式开"), ("--lam_orth 0", "lam_orth 显式 0"),
                   ("PANEL=", "面板必须显式传")]:
        (ok if k in s else bad)(lbl)
except Exception as e:
    bad(f"champion_run.sh 读取失败: {e}")

print("\n" + "═" * 70)
if FAIL:
    print(f"★★ FAIL {len(FAIL)} 项 —— 不要开始训练:")
    for x in FAIL: print(f"   · {x}")
    sys.exit(1)
print(f"★ 全部通过{f' (WARN {len(WARN)})' if WARN else ''} —— 可以开工。")
for x in WARN: print(f"   ! {x}")
