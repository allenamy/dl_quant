> **创建:** 2026-09-27 13:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2,按 lead 裁定) | **状态:** 溯源补录;不改任何运行 | **作废条件:** 本目录的 nc_legs.py 或 nc_hist_features.py 再改动(须更新本表)

# nc_legs / nc_hist_features:仓库版本与 pod2 实际执行版本

fresh2 的部署核对工具 `common/pod2_deploy_verify.sh`(9043ea94e)查出了这件事。pod2 上三个目录实际执行的是同一份字节:`/dev/shm/nc_2026-09-23/devices`、`/dev/shm/news2_2026-09-23/devices`(news2 根)、mretrain 部署目录。**这份字节此前不在仓库里。**

lead 裁定:把实际执行的版本原样入库,文件名带 sha;现有文件不覆盖。

| 文件 | sha256 | 性质 |
|---|---|---|
| `nc_legs.py` | fab4056f2ce75cf0b42f03559070e8b6eb37ae7ce45761a4183fde933d38c981 | 仓库版本(未动) |
| `nc_legs.executed_18387627.py` | 18387627f8426a45135b348dd4508281b4811894c91eb50af87751760609c0a0 | pod2 实际执行,原样 |
| `nc_hist_features.py` | a1c26c6210c21ee83854e5c7107369663f2bbbbdc29ffeb2c79e50c737d53e1c | 仓库版本(未动) |
| `nc_hist_features.executed_3eee6e88.py` | 3eee6e8842eb86cf203c8eb86c55e7c33d8a18532c080fda0376c317d7cda343 | pod2 实际执行,原样 |

两份执行版的字节与 pod2 `/dev/shm/news2_2026-09-23/devices/` 下的逐字节相同(sha 在 pod2 上实测);也与 `mretrain_2026-09-26/devices/` 下 fresh2 入库的副本相同。

## 哪些运行用了哪一版
pod2 上这两个文件的 mtime 都是 2026-09-23 23:06:26Z(stat 实测),此后没有再改。所以此后经 news2 根 `/dev/shm/news2_2026-09-23/devices/` 调用 nc_legs.py 的运行,用的都是**执行版**(18387627 / 3eee6e88):
- 线 D 的恒等运行(`dacd303af`):用执行版逐位复现了在役 legs 9ee5886f。9ee5886f **最初那次构建**用的是否就是这份字节,**没有核查**。当时的运行同样取自 news2 根,但那一刻的文件 sha 没有记录;
- 线 D 的 legs_d10 104af853(`4b341d7fd`);
- 十月 legs 383e3ddc 及其控制(复现 104af853,`d775400181939e498b1031c52c8b12a4b01bb084`);
- 描述性重读的 legs 37c0b5d3(`85f2a340b988fc07d661f3c29391295887cab235`);
- fresh2 的 KSR 链(mretrain 部署目录)。

仓库版本(fab4056f / a1c26c62)有没有在任何产出收据的运行里被执行过,**本次没有核查**。

## 两版的差异
**nc_legs.py**:只差收据写在哪里。执行版写在 legs.npz 旁边,名为 `NC_LEGS_RECEIPT.json`;仓库版写到 `{W}/receipts/NC_LEGS.json`。计算部分相同。
```
85,86c85
<     os.makedirs(f"{W}/receipts", exist_ok=True)
<     json.dump(rec, open(f"{W}/receipts/NC_LEGS.json", "w"), indent=1)          # the name news2_stage_inputs.py binds
---
>     json.dump(rec, open(os.path.join(os.path.dirname(out), "NC_LEGS_RECEIPT.json"), "w"), indent=1)
```

**nc_hist_features.py**:仓库版比执行版多两处。
1. `_king_block(mutate=...)`:门的变异臂所用的文本替换。
2. `'c7': fin5.sum(0)`:lead 09-23 的改动。执行版在这里是 `'c7': c7`。

据改动时的注释,这两种写法在基础臂上相等:`c7 := fin5.sum(0)`,等于 D5/D6 筛选里的 c7。执行版这条链逐位复现了在役 legs 9ee5886f,这一点与注释一致。
```
45,46c45
< def _king_block(mutate=None):
<     """mutate: optional [(old, new)] text replacements ..."""
---
> def _king_block():
49,52c48
<     txt = src.decode()
<     for old, new in (mutate or []):
<         assert txt.count(old) == 1, ("mutation anchor", old[:60]); txt = txt.replace(old, new)
<     lines = txt.split("\n")
---
>     lines = src.decode().split("\n")
59c55
< ... 'c7': fin5.sum(0), ...   # c7 := fin5.sum(0): equal to the D5/D6 screen's c7, and defined in every arm (lead 2026-09-23)
---
> ... 'c7': c7, ...
```

## 以后
十月链在每次 pod2 起跑前,都用 `pod2_deploy_verify.sh` 核对三处 sha 是否相同:仓库 HEAD、工作树、pod2。核对范围是 runbook 点名的装置及其 import 闭包。
