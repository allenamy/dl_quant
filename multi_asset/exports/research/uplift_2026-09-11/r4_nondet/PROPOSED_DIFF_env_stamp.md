# PROPOSED DIFF (NOT APPLIED) — stamp the full env into the F10 training report

> **创建:** 2026-09-11 | **Session:** b9646a9e (P4) | **状态:** 提案, 未应用 (pod `/workspace/*.py` 在我的写域外)
> **作废条件:** 训练器被 v4 链替换, 或 `V2` 开关被删除/改为无默认

## 缺陷

`/workspace/pod_f10_train_ext.py` (sha256 `93cc2cdf925a1dada9190a5d86664d28c811d9ba0ecf3eaf377d54fc554f2598`)

```python
L91:  V2 = int(os.environ.get("V2", "0"))
```

`V2=1` 是在役 V2MAIN 的合成链(L214-217: `r = wl[0]*r + wl[1]*Z24 + wl[2]*ZFD`, msharpe 腿权 × [model, rev24, fund])。
**默认是 0** ⇒ 忘记传 `V2=1` 会静默训练出**另一个对象**, 而不是报错。

同一配方的部署重训脚本 `/workspace/pod_f10_refit_ext.py` (sha `ea3675b8012ea266646571f6e1550f248d894cae832b190a8beab27befab9fb7`)
把同一条合成链**硬接**(L25/L62-63, 无 env 开关)⇒ 在役权重永远是 V2 对象; 只有研究侧的走查训练有这个陷阱。

报告 json 记录 `arm/seed/cost/ldd/afix/epochs/lr/win/burn/stride/embargo/self_sha256/targets_sha256/fea82_sha256/fea89_sha256`
—— **不含 V2**, 也不含 `LDC/CTXA/REC/PLE/NCOL/EXTRA/LPP`。因此"逐字复现归档 json 的配方"这件事**在 json 里做不到**。

## 提案(两处, 各一行级)

```diff
@@ L133 rep = {...}
 rep = {"arm": ARM, "seed": SEED, "cost": COST, "ldd": LDD, "afix": AFIX, "epochs": EPOCHS,
        "lr": LR, "win": WIN, "burn": BURN, "stride": STRIDE, "embargo": EMB,
+       "env": {k: os.environ.get(k) for k in
+               ("V2", "LDC", "CTXA", "REC", "PLE", "NCOL", "EXTRA", "LPP", "F10_DLW", "F10_OUT")},
+       "legs_sha256": (sha(f"{OUT}/data/f10v2_legs.npz") if V2 else None),
+       "torch": torch.__version__, "cudnn": torch.backends.cudnn.version(),
+       "gpu": (torch.cuda.get_device_name(0) if torch.cuda.is_available() else None),
        "self_sha256": sha(os.path.abspath(__file__)),
```

外加一条**枚举断言**(E-0826-D 族), 放在 L91 之后:

```diff
 V2 = int(os.environ.get("V2", "0"))
+# E-0826-D: 未声明的 env 不许静默改变对象。任何非白名单的 F10_* / 已知开关必须显式传。
+_KNOWN = {"V2","LDC","CTXA","REC","PLE","NCOL","EXTRA","LPP","ARM","SEED","COST","LDD","AFIX",
+          "EPOCHS","LR","F10_DLW","F10_OUT"}
+assert os.environ.get("V2") is not None, \
+    "V2 must be set explicitly (V2=1 = in-service composed chain, V2=0 = model-only). No default."
```

`legs_sha256` 是第四个输入 `f10v2_legs.npz`(V2 链的 Z24/ZFD/WL), 当前**完全没有被 hash 进报告** ——
即使 V2 被记下来了, 换了这个文件仍然看不出来。

## 成本

零训练时间成本(都是元数据)。断言会**让任何没传 V2 的旧调用失败** —— 这正是目的; 需要一次性
把 pod 上的调用方都补上 `V2=1`(`pod_accept.sh` L8 / `pod_ple_seq.sh` L14,37,40 / `f11_chain.sh` L16 /
`gpu_queue.sh` L6 已经都传了; 少的是研究侧临时脚本)。

## 归属

这是 **E-0826-D「复跑漏 env」** 的一个新实例, 也是 **E-0825-H「按名字推断语义」** 的一个新实例
(`ARM=V2MAIN` 这个名字里的 "V2" 不是 `V2=1` 这个开关; 前者是臂名字符串, 后者是链开关)。
