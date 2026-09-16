> **创建:** 2026-09-16 | **Session:** codex-codereview | **状态:** final(只读逐代码审查; 未 checkout / 未 add / 未 commit / 未跑任何装置) | **作废条件:** 本件所钉任一 commit sha 或文件 blob sha 变化、或 `INVENTORY_codex_branches_2026-09-16.md` 的分支拓扑被更正。

# 独立研究员(codex)六项修复的逐代码审查

**前置**: `docs/fixprogram_2026-09-13/INVENTORY_codex_branches_2026-09-16.md`(分类清点, 已完成)。本件只做**代码正确性**, 不重做分类。

**方法**: 全程 `git show <sha>:<path>` / `git ls-tree` / `git grep <sha>` / `git cat-file`。**没有 checkout, 没有跑任何被审代码。** 所有"我核实了"都是**读源码逐行对照 + 算术自洽核算**, 不是重跑。

**两栏纪律**: 「它声称」= 从它的提交信息/DESIGN/REPORT 抄的原话。「我核实了」= 我打开源码/产物逐行对上的。**没打开的一律进「它声称」。**

---

## 0. 先说结论(三句)

1. **C1 是这六项里唯一做到"修前状态被行为性证明为坏"的。** 它不是靠断言, 是靠 `repair.py:62` 那条**旧值逐位重放控制** —— 把缺失月重设为 NaN 后重算通道, 要求与冻结缓存**逐字节相同**。这等于用被修对象自己的字节证明了"修前确实是 NaN 洞", 比任何测试断言都强。代价量级出自它的 committed 收据 `completed/build2/RESULT.json` 字段 `old_next_return_f16`(**不是我读了面板**, 见 C1 §(b)(c)): 2026-03-01 00:05 那一格通道 0 记着 **−0.1687**, 真值 **−0.0183**。
2. **C7 的缺陷机制成立、修法正确、但红测不存在。** `LOCAL_CONTROLS.json` 断言"旧 11 测 1 failure + 1 error", 但**那次运行的输出在 11 条分支上一份都没有**(`old_actual_chunk: "07cc30"` 这个句柄 `git grep` 全树无对应物)。更要命的是: 它自己在 `test_e60_funding.py:7,12` 留了 `E60_ENGINE_SOURCE` / `E60_RUNNER_SOURCE` 两个**专门用来做变异对照的环境变量钩子**, 全树**零次使用**。修前修后同一套 14 测的对比从未跑过。
3. **C5 不是"补 4 个点"这么小。** 那 4 个点是 2026-07-24 00:20/00:55/04:20/04:55 UTC 的 AERGO 估值缺失, 而**旧运行正好停在 2026-07-23** —— 我用 `dynamic_cash.py:366-370` 的 `_Unknown(MISSING_HELD_*_MARK)` 路径 + 时间戳算术独立确认了这一点。**608 日里的最后 38 日(含 2026-08 那个 −5.96% / MDD 15.53% 的月份)完全建立在这 4 个数上。** 它自己的尾扫 `tail_candidates1/STDOUT.json` 同时报了全轴还有 **2,943 个**同类缺失格、候选集内 **95 个**, 只修了 4 个 —— **选谁修的判据就是"谁挡住了运行"**。

---

## C1 · 三个月 raw 档缺失回填

### 改动的确切代码

- commit **`f849852eb3d2e30c9360285d81b1dafe2e0e0d00`**(2026-09-15 00:36, 分支 `codex/raw-month-repair-20260915`)
- 核心文件 `multi_asset/exports/research/codex_causal_fullchain_2026-09-14/data/canonical_month_repair_20260914/repair.py`(190 行)

逐字引关键几行:

```python
 50:    old_raw=raw.copy();old_raw[lo:hi]=np.nan
 51:    old_ch,_=to_channels(old_raw[:,None,:],np.array([np.nan]));new_ch,_=to_channels(raw[:,None,:],np.array([np.nan]))
```
```python
 62:            if not same_bits(old[a-row0:b-row0,j],p['old_channels'][k:k+b-a]):raise ValueError('old channel raw replay mismatch '+p['symbol'])
```
```python
 66:        if row0<=last+1<row0+len(old):
 67:            updated[last+1-row0,j,0]=p['new_channels'][p['hi'],0];ret_rows+=1
 68:    delta=old.view(np.uint16)!=updated.view(np.uint16)
 ...
 75:    if np.any(delta&~allowed):raise ValueError('outside support mutation')
```
```python
159:            if not same_bits(targets[key][idx,p['j']],old[key]):raise ValueError('old raw target replay '+p['symbol']+' '+key)
```
```python
176:                for p in patches:b[p['target_indices'],p['j']]=a[p['target_indices'],p['j']]
177:            if not same_bits(a,b):raise ValueError('target outside support changed '+key)
```

### 它声称的机制

`REPAIR_REPORT_20260915.md`(同 commit)原话:
> 「All **24,768 missing raw bars** and three next observed ret5 connections were repaired. Exactly **173,368 channel cells changed** inside declared support; every outside-support cell remains **bitwise equal**.」

`ORIGINAL_FULL_AXIS_AUDIT_20260915.md` 原话:
> 「The old cache retains previous-month final closed bar at the named month's 00:00 boundary, then lacks all bars from 00:05 through next-month 00:00. These gaps are original raw acquisition/inventory omissions, not economic lifecycle transitions.」

### ★ 机制是否成立 —— 我核实了, **成立**(2026-09-16 lead 追问后重写本节, 把「机制」与「代价量级」分开, 并补全出处)

#### (a) 机制: 我核实了, 在**生产算术源码**里

`multi_asset/exports/research/codex_causal_fullchain_2026-09-14/data/canonical_data.py`(在 `a90dc829` 树里, 35 行), 逐字引:
```python
 18:    prior_indices=np.maximum.accumulate(np.where(present,rows,-1),axis=0)
 19:    before=np.vstack([np.full((1,r.shape[1]),-1),prior_indices[:-1]])
 20:    prev=np.where(before>=0,c[np.maximum(before,0),np.arange(r.shape[1])[None,:]],pc[None,:])
 23:        values[:,:,0]=np.where(present&(prev>0),c/prev-1,np.nan)
```
`prev` 是**最近一根 present 行的 close 的前缀累积**, 不是"上一根时间行"。⇒ **NaN 段之后第一根 present bar 的通道 0 = close / 洞之前最后一个 close − 1**, 即一整段跨洞收益被写进一根 5 分钟 bar。这不是从单测反推的, 是生产函数本身。(单测 `test_repair.py:37` `assertEqual(old[30,1,0],np.float16(130/119-1))` 与之一致, 作为旁证。)

同文件 `:5` 与 `:32-33`:
```python
  5: CLIPS=[(-.3,.3),(0,.5),(0,1),(0,25),(0,20),(-5,15),(0,1)]
 32:    for k,(lo,hi) in enumerate(CLIPS):
 33:        v=values[:,:,k];good=np.isfinite(v);out[:,:,k][good]=np.clip(v[good],lo,hi).astype(np.float16)
```
⇒ **通道 0 的裁剪带确实是 ±0.30**, 这是我在 codex 自己的 `canonical_data.py` 里读到的, **不是从我们 `[[cache_ret5_channel_clipped_at_0p30_2026_09_12]]` 那条记忆搬过来的**(上一版报告写成了后者, 属于把我方事实外推到对方链路, 现更正)。

#### (b) 代价量级: 出处在这里 —— **committed 收据, 不是我读了面板**

数字的唯一来源:
**路径** `multi_asset/exports/research/codex_causal_fullchain_2026-09-14/data/canonical_month_repair_20260914/completed/build2/RESULT.json`
**提交** `a90dc8294575725567d5d4b9621728eaa92f9f92` · **blob** `d2851f79de0396a91eb3a8f86858e1062e09d4bb` (24,496 bytes)
**字段** `repaired_months[i].old_next_return_f16` / `.new_next_return_f16`

复跑命令(逐字):
```
git show a90dc829:multi_asset/exports/research/codex_causal_fullchain_2026-09-14/data/canonical_month_repair_20260914/completed/build2/RESULT.json \
  | python3 -c "import json,sys;[print({k:m[k] for k in ('symbol','next_recomputed_return_ts','previous_close','last_inserted_close','next_close','old_next_return_f16','new_next_return_f16')}) for m in json.load(sys.stdin)['repaired_months']]"
```
输出(逐字):
```
{'symbol': '1000000BOBUSDT', 'next_recomputed_return_ts': 1772323500, 'previous_close': 0.01482, 'last_inserted_close': 0.01255, 'next_close': 0.01232, 'old_next_return_f16': -0.168701171875, 'new_next_return_f16': -0.0183258056640625}
{'symbol': 'BMTUSDT',        'next_recomputed_return_ts': 1772323500, 'previous_close': 0.01829, 'last_inserted_close': 0.01535, 'next_close': 0.01545, 'old_next_return_f16': -0.1552734375,  'new_next_return_f16': 0.0065155029296875}
{'symbol': 'MTLUSDT',        'next_recomputed_return_ts': 1777593900, 'previous_close': 0.2699,  'last_inserted_close': 0.2946,  'next_close': 0.2951,  'old_next_return_f16': 0.0933837890625, 'new_next_return_f16': 0.001697540283203125}
```
> **为什么 grep 没打到**: 字段叫 `old_next_return_f16`(不是 `old_ret5`/`ret5_old`/`first_after_gap`); 值以**分数**存(`-0.168701171875`), 所以 `grep "16\.8|1\.83|15\.53|0\.65"` 无论如何匹配不到。是我在报告里把它们百分号化了才变得不可追溯 —— 这是我的表述问题。

我自己的算术复核(6/6 全中, float16 舍入后逐位相同):
`0.01232/0.01482−1 = −0.168690958` → `np.float16` = `−0.168701171875` = 收据值 ✓;`0.01232/0.01255−1` → `−0.0183258056640625` ✓;BMT `−0.1552734375` / `+0.0065155029296875` ✓;MTL `+0.0933837890625` / `+0.001697540283203125` ✓。三个旧值 `|x| < 0.30` ⇒ **都不触裁剪**。

#### (c) ★ 这是"读到的"还是"推算的" —— 准确答案: **隔一层的读, 带逐位闸门**

**我没有打开过 `channels7.npz`**(它在 pod2, 本地没有)。收据里的 `old_next_return_f16` 是 codex **自己重放**出来的值 —— `repair.py:150` 写的是 `float(patch['old_channels'][patch['hi'],0])`, 而 `old_channels = to_channels(old_raw)`(L50-51)。

但这个重放值与冻结面板的对应格之间**有一条逐位闸门**, 我把索引映射逐步验过:
- `prepare_patch` 返回 `first_global=g`、`last_global=g+hi-lo-1` ⇒ 全局行 `last_global+1 = g+hi-lo` 对应局部索引 `lo+(g+hi-lo)-g = **hi**` —— 正是收据取值的那个下标。
- `patch_chunk` L59 `a=max(row0,first-1); b=min(row0+len(old),last+2)` ⇒ 比对的全局区间是 `[first-1, last+2)`, **含 `last+1`**。
- L62 `if not same_bits(old[...,j], p['old_channels'][k:k+b-a]):raise` ⇒ 对该区间**全 7 通道**要求与冻结缓存**逐字节相同**, 否则整跑炸。
- build2 实际 `status = "PASS_RAW_REPAIR_AND_BITWISE_SUPPORT_PROOF"`(同一份 RESULT.json), 执行收据 `completed/build2_execution/EXIT.json`。

⇒ 准确表述: **「该值等于冻结面板对应格, 条件是 build2 那次运行确实执行了 L62 并退出 0」。** 这比"我直接读了面板"弱一格, 比"我按收盘价推算"强很多。**报告任何下游引用都应该用这句话, 不要写成"我在面板里读到"。**

#### (d) 那这个坏值进没进特征 —— **我只核到一半**
- **进了 `channels7.npz` 的通道 0**: `canonical_data.py:33` 把 clip 后的值写进 `out`, 而 `out` 就是 7 通道数组。✓ 已核。
- **是否进到 F10/King 实际吃的特征列**: **未核。** `FULL_FEATURES_VERIFIED_INPUTS.json` 把 `data/canonical3/channels7.npz` 列为特征面板、`producer/build_features.py` 列为构建器, 但**我没有打开 `build_features.py` 确认通道 0 被消费**。上一版报告写的"直接进了特征面板"应降级为: **进了面板文件的通道 0; 是否被特征列消费未验。**

#### (e) 分开记账
- **机制**: 成立, 源码级已证(`canonical_data.py:18-23`)。**这一条我认满分。**
- **代价量级**: 三名 × 各 1 格通道 0 被写成跨月收益(BOB 真值 −1.83% 写成 −16.87%;BMT 真值 **+0.65%** 写成 **−15.53%**, 符号相反;MTL 真值 +0.17% 写成 +9.34%), 加 519 个锚的标签被 mask 掉。**这是下界。** 理由: `canonical_data.py:20,23` 的前推**对任何 NaN 段一视同仁, 不问成因** —— 无论那段是档案缺失、停牌还是真下市, 重连那根 bar 的通道 0 都会写成跨段收益。`ORIGINAL_FULL_AXIS_AUDIT_SUMMARY.json` 报 `price_gaps: {symbols:162, gaps:163, kinds:{INTERNAL:134, TERMINAL:29}}`(阈值 ≥7 天), ⇒ **至少 134 个内部价格洞各有一个同类重连格, 一个都没修**; 且 <7 天的短洞根本不在这个盘点里。**但要说清: 这 134 个里有多少是"该修的档案缺失"、多少是"合法停牌(重连收益是真实的)", 我没有分。** 所以我只能说"同一算术产物普遍存在", **不能**说"还有 134 个同等严重的缺陷"。

**标签侧同样成立**: `target_values`(L79-86)的 y = close(E+48 bar)/close(E)−1 = close(E+4h)/close(E)−1, 与 CLAUDE.md 的 RAW 口径一致; 洞里 c0/c1 为 NaN ⇒ `label_mask` 为 False ⇒ 那 519 个锚**原本整个被 mask 掉**(不是被写坏)。所以标签侧是"少了 519 个训练样本", 通道侧是"多了 3 个假的极端收益"。两种伤害不同, 报告没区分, 我在此分开记。

### ★ 修法是否正确 —— 我核实了, **正确, 且边界处理逐条对**

| 边界 | 代码 | 我的判断 |
|---|---|---|
| 洞的支撑集由谁定义 | `prepare_patch` L46-49: `lo/hi` 由**下载档自身的月时钟** `missing_ts` 定, 再与全局 `ts` 对齐校验 | ✓ **不是**由"哪里数值不同"自定义 —— 避开了「用被检对象自己的产物定义检查范围」 |
| 前后文是否够 | L47 `if lo<2 or hi>=len(raw_ts)` | ✓ 保证 ret5 有前一根、重连有后一根 |
| 重连那一根只改 ret5 | L67 只写 `[...,j,0]`; L74 `allowed[r,p['j'],0]=True` | ✓ 与 `to_channels` 一阶(ret5)语义一致 |
| NaN 比较 | L68 `old.view(np.uint16)!=updated.view(np.uint16)`; `same_bits` L32 用 `tobytes()` | ✓ 位比较, NaN-safe, 不是 `==` |
| 支撑区外未变 | L75 raise; L177 target 侧同 | ✓ **硬 raise, 不是报个数字** |
| 缺失不补零 | L82-83 `y=np.full(...,np.nan); y[valid]=...` | ✓ 无效端点 ⇒ NaN, 不是 0 |
| 计数溢出 | L84 `counts=np.zeros(len(ar),np.uint8)`, 最大 49 | ✓ |
| 写盘是否真写对 | L180 写 → L182 `stream_repair(...,True)` 重开 zip **逐字节比对** → L183 两次收据必须相同 | ✓ 序列化读回, 不是只算 hash |
| 输入是否中途变 | L126-128 pin before, L184-185 pin after 比对 | ✓ |

**曾疑欠写, 现已排除**(2026-09-16 补核): L67 只修 `last+1` 的通道 0。若 `to_channels` 里有任何窗口 >1 根的通道, `last+1..last+k` 的其他通道也该变, 而 `allowed` 会禁止写、`delta` 又因为没写而看不到差 —— **支撑区外控制抓不到"欠写"**。我现在打开了 `data/canonical_data.py`(`a90dc829` 树里, 35 行)逐行读: 通道 1/2 只用本行 `(h-l)/c`、`(c-l)/(h-l)`(`:24-25`), 通道 3/4/5/6 只用本行 `q/n/t`(`:27-31`), **只有通道 0 跨行**(`:20,23` 的 `prev`)。⇒ **确实只有通道 0 需要在 `last+1` 改, 不欠写。** 这条从"核了行为没核实现"升级为"实现已核"。

**一处未解释的残差**: 24,768 bar × 7 通道 + 3 个 ret5 = **173,379** 个允许变的格, 实测 `changed_channel_cells = 173,368`, 少 **11** 格。方向是安全的(变得比允许的少), 但这 11 格为何前后位相同, 报告没说, 我也没能定位。

### 红测: **有, 而且是行为证据**

两层:
1. **对被修对象本体的行为证据**: `repair.py:62` / `:159` —— 把缺月重设 NaN 重算, 要求与**冻结缓存/冻结标签逐字节相同**。跑通了(build2 `status: PASS_RAW_REPAIR_AND_BITWISE_SUPPORT_PROOF`), 就等于**实测证明了修前那些格确实是 NaN 且四周字节与重放一致**。这不是断言, 是拿真实字节做的。
2. **对修复装置的变异对照**: `test_repair.py:39` 逐字引
   ```python
    39:   with self.assertRaisesRegex(ValueError,'old channel'):patch_chunk(updated,0,[p])
   ```
   把已打过补丁的数组再喂一次 ⇒ 旧值重放门必须炸。**基线绿被显式断言**(L32 的第一次 `patch_chunk` 成功, L33-38 逐项验了输出), 所以这个变异对照**不是空转**。`GREEN_LOCAL.log` 实跑 3 测 OK。

### 逐位控制: **有, 三处, 且是硬 raise**
`repair.py:75`(通道支撑区外)、`:177`(标签支撑区外)、`:183`(写/验两遍收据相同)。报告自报的 171,752,832 个 raw 标量格逐位相等是 `audit_raw_overlay.py` 的独立第二阶段, **我没打开那个文件**。

### 收据是否真在库里
我用 `git cat-file -s` 逐个验了(不是看文件名):
`source_evidence/three_month_http1/MTLUSDT-5m-2026-04.zip` = blob `273b594b`, **252,516 bytes**;
`source_evidence/scan1_RESULT.json` = blob `5f06a9a9`, **1,176,044 bytes**;
`completed/build2/RESULT.json` = blob `d2851f79`, 24,496 bytes。
**官方 ZIP 原件和 CHECKSUM 都真在 git 里**, 没有被 `.gitignore` 静默丢掉。

### 判决: **采纳**
这是六项里唯一一项我会说"可以直接当受据用"的。**但采纳的是它的证明, 不是它的产物** —— 修好的 `channels7.npz`(`afd0ffa9…`)在 pod2, 不在任何分支。我们能拿走的是: (a) 这个缺陷确实存在且已量化(3 个假极端收益 + 519 个被 mask 掉的锚), (b) `repair.py` 这套"旧值逐位重放 + 支撑区外硬 raise + 写读两遍"的做法, 值得抄进我们自己的补洞链。

---

## C2 · 2024-12 历史档还原

### 改动的确切代码
- commit **`a90dc8294575725567d5d4b9621728eaa92f9f92`**(2026-09-15 00:44, 同分支)
- `.../data/history_december_restore_20260915/restore_exact.py`(53 行)

```python
 21:   if p.parent!=R/'data/history1/output/archives' or p.name not in [expected,expected+'.CHECKSUM'] or p.resolve()!=p:raise ValueError('original path guard')
 23:   if p.exists() and (before[relative]!=item['sha256'] or p.stat().st_size!=item['bytes']):raise ValueError('existing original differs; cannot overwrite')
 30:   if not m.isfile() or m.size!=items[m.name]['bytes'] or hashlib.sha256(t.extractfile(m).read()).hexdigest()!=items[m.name]['sha256']:raise ValueError('payload member bytes')
 40:   try:os.link(part,p)
 46:   if after[relative]!=item['sha256'] or p.stat().st_size!=item['bytes']:raise ValueError('restored original readback')
```

### 它声称的机制
`RESTORE_REPORT_20260915.md` 原话:
> 「this is **restoration of identical bytes**, not a new download or revised data source.」
> 「All 740 original paths were **absent** during the recorded preview.」

### ★ 机制是否成立 —— 我核实了, **成立, 但它不是"我们的数据缺陷"**

`REMOTE_BEFORE.json`(同 commit)逐条列了 740 个 `"state": "ABSENT"`; `completed/restore1/RESULT.json` 报 `restored_files = 740`, **`already_same_files = 0`** —— 即恢复前 740 个全不在。

**但恢复源是它自己的本地备份 TAR**: `COMPLETION_READBACK.json` 里 `.../data/local_archive/history_original_16132.tar` sha `a2514f23…`, before/after 相同; 选择范围由 `ROWS.jsonl` 里 `month=2024-12 且 status=VERIFIED_RAW` 决定 —— **这些档当初是下载并验证过的**, 所以 canonical3 建面板时它们在。它们是**后来从 pod 磁盘上消失的**。同一批提交里的 `REPAIR_REPORT_20260915.md` 原话「build1 failed on the original **Pod quota**」和 `CONSUMER_HANDOFF` 的「build1 reached 262,144 rows before **disk quota failure**」把原因写得很清楚。

⇒ **C2 修的是 codex 自己的 pod 环境, 不是我们的数据真值。** 它没有改变任何已算出的数, 只是让那部分重新可算。清点员的"可得性修复"标签方向对; 我把它收紧为: **这不是一项对我们有内容的修复。**

### ★ 修法是否正确 —— 我核实了, **正确**
- L21 路径白名单 + `p.resolve()!=p` **拒符号链接**;
- L30 **先全量校验整个 payload 再发布任何一个原件**(两阶段), 不是边验边写;
- L37-38 写 `.part` → `fsync` → 校 sha → L40 `os.link` **原子且不能覆盖已存在路径**;
- L44-46 事后对 740 个**独立重哈希**; L47 断言既存文件未变。
- **一处小账目瑕疵**: L40-43, 若 `os.link` 抛 `FileExistsError` 且 sha 相符, 代码不 re-raise, 随后仍 `restored.append(relative)` —— 把"竞态已存在"计进了"已还原"。不影响正确性, 影响计数语义。本次 `already_same_files=0` 所以没触发。

### 红测: **无, 且不需要**
这不是行为修复, 是文件搬运。它的"证明"是 740 份 before/after sha, 那已经是最强的形式。

### 逐位控制: **有**
`original_sha_before` / `original_sha_after` 各 740 条 + 4 个输入 pin before/after。

### 判决: **不采纳**(不是"错", 是"对我们没有内容")
建议在总账里把 C2 从"真值修复 4 项"里移出, 记为 **"研究员自有环境的磁盘恢复"**。否则"4 项干净真值修复"这个说法会被高估。

---

## C3 · BOB / BMT / MTL 三名 raw 标签重算

### 改动的确切代码
与 C1 同一 commit `f849852e`、同一文件 `repair.py` 的 L152-178 段(标签阶段)。

```python
157:        first=ts[p['first_global']];last=ts[p['last_global']];idx=np.flatnonzero((anchors<=last)&(anchors+14400>=first));old=target_values(...);new=target_values(...)
159:            if not same_bits(targets[key][idx,p['j']],old[key]):raise ValueError('old raw target replay '+p['symbol']+' '+key)
161:            targets[key][idx,p['j']]=new[key]
```

### 它声称的机制
> 「Raw float64 endpoint targets, label masks and inclusive 49-bar counts changed for **169 BOB, 169 BMT and 181 MTL anchors: 519 cells in each target array**.」

### ★ 机制是否成立 —— 我核实了, **成立, 且数字我独立复核对得上**

`target_values` 用 `c0=raw[ar,0]`、`c1=raw[ar+48,0]`, `ar+48` 对应 +14400 秒 = +4h(L81 显式断言 `ts[ar+48]==anchors+14400`)。洞在整月 ⇒ 每个受影响锚至少有一个端点落在洞里 ⇒ `valid=False` ⇒ y=NaN, mask=False。

我自己算锚数: 2026-02 有 28 天 × 6 锚/天 = 168, 加跨月首锚 = **169** ✓ (BOB/BMT 各 169); 2026-04 有 30 天 × 6 = 180, +1 = **181** ✓ (MTL)。169+169+181 = **519** ✓。`completed/build2/RESULT.json` 的 `targets[].changed_cells` 逐名报 `{y_raw_endpoint:169, label_mask:169, valid_close_count49:169}` / `{…181…}`, 与我的独立算术一致。

再核 bar 数: 2026-02 = 28×288 = 8,064/名 ×2 = 16,128; 2026-04 = 30×288 = 8,640。合计 **24,768** ✓ 与报的 `repaired_raw_rows` 逐字相同。`CONSUMER_HANDOFF` 的「February 16,126; March 2; April 8,639; May 1」= 24,768 ✓ (差的 2 和 1 是跨月 00:00 那根落进下个容器)。

### ★ 修法是否正确 —— 我核实了, **正确**
- **支撑集由时间几何定义, 不由差值定义**: L157 `(anchors<=last)&(anchors+14400>=first)` 是"锚的 [E, E+4h] 窗口与洞相交", 闭区间两端都对。✓
- **旧值重放门**: L159 —— 要求冻结标签在这些格上**逐位等于**从 NaN 化 raw 重算的值。这同样是行为性的修前证明。
- **支撑外逐位控制**: L171-178, 把新数组在受影响格上**回填旧值**再与旧数组 `same_bits` —— 干净, 且 `E_ts`/`symbols`/`label_end` 要求**整数组**位等。
- **NaN 安全计数**: L160 用 `np.frombuffer(..., dtype=f'V{itemsize}')` 做字节比较, 不是 `!=`。✓

### 红测 / 逐位控制
同 C1(`test_repair.py:41-49` 的 `test_target_support_and_raw64_endpoint` 显式验了 `valid_close_count49` 在有洞/无洞两种输入下分别是 `[49,1,48]` 和 `[49,49,49]`, 并有 `assertRaisesRegex(ValueError,'grid')` 的负控)。

### 判决: **采纳**
本质上是 C1 的标签侧, 同一套控制。**要点**: 这 519 个锚原来是被 `label_mask` 排除的样本, 不是被写错的样本。所以 C3 的效应是"多了 519 个训练/评估样本", 应按**样本量变化**入账, 不能与"数值被改正"混报。

---

## C5 · AERGO 四个缺失估值点

### 改动的确切代码
- commit **`8990ebd3ba1ac47a2861cdf30c5f8cbb6626cd97`**(分支 `codex/fullchain-continuation-20260914`); 源码实体在 **`6e6f5dc6`**(`codex/public-funding-evidence-20260915`)
- `multi_asset/exports/research/codex_causal_fullchain_2026-09-14/book/dynamic_frame_inputs_20260915/current_rule_mark_valuation_20260915/mark_valuation.py`(63 行)

```python
  9: TARGETS=(('NAV_SNAPSHOT',1784852400000),('READBACK',1784854500000),('NAV_SNAPSHOT',1784866800000),('READBACK',1784868900000))
 56:   need(e.get('price_asof_ms')==when and e.get('prices',{}).get(SYMBOL,'ABSENT')is None,'only original missing exact-clock valuation')
 58:   ix=(when-FIRST)//300000-1;r=verified._rows[ix];need(r[6]+1==when,'no stale or future mark')
 60:   restored=dict(new);restored['prices']=dict(new['prices']);restored['prices'][SYMBOL]=None;del restored['valuation_sources'];need(canonical(restored)==before,'only exact valuation and explicit source metadata changed')
 63:  need(seen==set(TARGETS),'all four fixed valuation events retained, no silent partial overlay')
```

### 它声称的机制
`docs/RESULT_current_strategy_replay_2026-09-15.md` 第 83 行原话:
> 「AERGO 缺估值只补了 4 个原先为空的时点, 来源是官方原始 markPriceKlines 的已闭 bar。没有把 mark 当成可成交价格、成交量或修改原结算假设; 前 570 个独立日界经济字段完全相同。**这个定向修复不等于历史原始数据已无缺口。**」

### ★ 机制是否成立 —— 我核实了, **成立, 而且它的杠杆比文字给人的印象大得多**

**修前的具体失败路径**, 我在 `dynamic_cash.py`(blob sha `8d8ddf8a002a9de7a613ce61c6bb0a18e7acd2cf12690cd5080d1326c2e4b9ce`, 分支 `6e6f5dc6`)L366-370 找到:
```python
366:            value = e['prices'].get(sym)
367:            marks[sym] = float(value) if _positive(value) else None
368:            if p['qty'] != 0:
369:                if marks[sym] is None:
370:                    raise _Unknown(reason, symbol=sym, instrument_id=p['instrument_id'])
```
**持有非零 + 该名无价 ⇒ 整条路径 `UNMEASURABLE`, 之后 `apply` 直接 `raise ValueError('unmeasurable path cannot continue by guessing')`(L297-298)。** 不是跳过一个点, 是整个回放就此终止。

我把四个时间戳解码:
`1784852400000` = **2026-07-24T00:20:00Z**, `1784854500000` = 00:55Z, `1784866800000` = 04:20Z, `1784868900000` = 04:55Z; AERGO 的 `CLOSE=1784874600000` = **06:30Z**。

上一版报告停在 **2026-07-23**(清点员引的 `ADDENDUM_2026-09-15.md`: 2.62 / 569 日)。**⇒ 旧运行正是撞在 2026-07-24 00:20 这一格上。这 4 个数是 570 日 → 608 日的唯一闸门。** 多出来的 38 日里包含 2026-08 那个 −5.9586% / MDD 15.5319% 的月份。

**公平起见, 必须说清方向**: 补了之后夏普从 2.62/569 掉到 **2.523/608**。**这个补丁让交付数字变差了**, 所以它不是一次自利的挑选。这一条对它有利, 我照录。

**但选择范围本身有问题。** `tail_candidates1/STDOUT.json`(同分支)原文字段:
> `"all_axis_active_missing_cells": 2943, "candidate_missing_cells": 95,`
> `"candidate_definition": "UNION_OLD_BLOCK_HELD_AND_FUTURE_PUBLICATION_NONZERO; NOT_PROOF_OF_FUTURE_HOLDINGS_OR_ALL_PNS_KEY_DOMAIN"`

⇒ 2026-07-24 之后全轴还有 **2,943** 个同类缺失估值格; 候选集(定义 = **旧阻断点持有过的名 ∪ 未来出版权重非零的名**)内 **95** 个; **修了 4 个**。**候选集的定义本身是"书持有/书想持有"** —— 这正是 `[[textual_instrument_for_a_behavioural_property]]` 同族的"用被检对象自己的产物定义检查范围"。第二条候选行是 `GRVTUSDT`, `instrument_id` = **`GRVTUSDT#legacy-unaudited`** —— 如果那天书恰好持有 GRVT, 608 日同样跑不出来。**交付的窗口长度取决于一个偶然。**

### ★ 修法是否正确 —— 我核实了, **这 4 个点的实现是六项里最严的**

| 检查 | 代码 | 判断 |
|---|---|---|
| 只填原本为空的 | L56 `.get(SYMBOL,'ABSENT') is None` | ✓ 哨兵写法同时拒绝"键不存在"和"已有值"两种情形 —— **不会过修** |
| 无前视 | L58 `need(r[6]+1==when,…)`; L19 `r[6]==r[0]+299999` | ✓ 我代入首个目标算过: `ix=3`, `r[0]=1784852100000`, `r[6]+1=1784852400000` = 事件时刻。**用的是恰好在该时刻收盘的那根 bar**, 严格向后看 |
| 只改这一个字段 | L60 逐事件把价格还原为 `None`、删掉 `valuation_sources`, 要求 `canonical(restored)==before` | ✓ **逐事件 canonical-JSON 逐位控制**, 不是总量 hash |
| 缺失不静默跳过 | L63 `need(seen==set(TARGETS),…)` | ✓ 少找到一个就炸 |
| 不污染成交面 | L57 拒已有 `valuation_sources`; `report()` 写 `ordinary_execution_observations_changed=False` | ✓ 且 `test_day_and_risk_observations_unchanged`(L58)实测 DAY/RISK_ATTEMPT 事件字节不变 |
| 源真实性 | L33 三份 blob sha; L35 `rec['status']==200` 且 `authenticated is False`; L37 body sha/长度 | ✓ |
| 网格完整 | L17 恰 78 行(< limit 100, 未截断); L19 逐行毫秒网格; L23 OHLC 一致性 | ✓ |

**一处口径不一致(已披露但值得记)**: 这 4 个点用的是 **markPriceKlines(标记价)**, 而其余全部估值用的是普通 K 线 close。`report()` 里自写 `scope='CURRENT_SNAPSHOT_MARK_ONLY_NOT_ORDINARY_TRADE_OR_HISTORICAL_FEED_CERTIFICATION'`。NAV 和 **PNS(逐名止损)** 都吃这个价 —— 所以是混源估值。披露了, 但混源这件事本身没有对照。

### ★ 红测 —— **"RED1" 是假红**
`RED1/EXIT.json` = `{"actual_exit": 1}`, `RED1/STDERR.log` 逐字:
```
ImportError: Failed to import test module: test_mark_valuation
...
ModuleNotFoundError: No module named 'mark_valuation'
```
**这个"红"是"模块还没写"**, 不是"缺陷被测出来"。它自己在 `HANDOFF.md` 里也承认「原 RED1(模块尚不存在)」。**按 `[[textual_instrument_for_a_behavioural_property]]`, 这不是红测。**

**但变异对照是真的。** `test_mark_valuation.py` 有 18 个测试, 其中 8 个是有断言绿基线(`test_actual78_and_only4_frames_change`, L19-26, 显式断言四个价 `.02210142/.02273/.02297/.02275592`)之上的定向变异:
`test_known_price_conflict`(L43-44, 把已有价改成 1. ⇒ 必炸)、`test_wrong_asof`(L45-46, `price_asof_ms+1` ⇒ 必炸)、`test_missing_target`(L47)、`test_duplicate_target`(L48-49)、`test_future_grid`(L52-53, `x[3][6]+=1` ⇒ 必炸)、`test_prior_close`、`test_wrong_generation`、`test_closed_generation`。**这些是合格的变异对照。**

**一处装置/收据错位**: `GREEN1/STDERR.log` 实跑 **17** 个测试, 但入库的 `test_mark_valuation.py` 有 **18** 个 —— 缺的是 `test_full_original_and_upgraded_stream_identity`(L27-31)。**绿收据认证的不是入库的这份文件**(`[[patch_on_disk_is_not_patch_running]]`)。`native_controls_readback1/RESULT.json` 报的是 `CURRENT_NATIVE51_FULL_READBACK_1`(51 项控制, `actual_child_exit: 0`), 但**它没有逐测名单**, 我无法确认那 51 项里包含第 18 个测试。

### 逐位控制: **有, 而且是最细粒度的一种**
L60 的逐事件 canonical 还原比对。`HANDOFF.md` 另报「全 1,653,238 个输入事件中只有四个估值事件变化」+ 原/升级后两个流 SHA —— **这两个 SHA 我没有独立重算**。

### 判决: **采纳但需改**
补法本身我会照抄。**必须改的是记账方式**: 不能记成"补了 4 个点", 要记成 **"一次可得性放宽, 它单独决定了 608 日窗口的最后 38 日, 且同类缺口全轴还剩 2,939 个未处理、其中候选集内 91 个"**。同时要把 markPriceKlines 混源这件事作为一条独立限制留在账上。

---

## C6 · generation / HOLD 目标与资金费修复

### 改动的确切代码
- commits **`6a8be1ba5ab0cabf5a3ae28d7de01640f615cfd2`** / **`3c040da257207ccd40ed2eeb290e2026388a4842`**(分支 `codex/causal-producer-generation-20260914`)
- 我能读到的实体只有 `.../producer/generation_windows.py`(93 行)+ `.../producer/probe_generation_components.py`(48 行)。

```python
 47:        if item is None:
 48:            ids.append(str(s)+'#UNRESOLVED');status.append('LEGACY_CONTINUITY_UNAUDITED');continue
 50:        known=[e for e in item['transitions'] if e['announced_at_ms']<=observed and e['effective_ms']<=observed]
 61:        if not is_active:mask[j]=np.ones(len(ts),bool)
 62:        elif birth is not None:
 65:            bad=ms-300000<birth
 66:            if bad.any():mask[j]=bad
 67:            first=((birth+300000+299999)//300000)*300000
 68:            if np.any(ms==first):retmask[j]=ms==first
```

### ★ 这一项**主要部分无法审查** —— 源码不在任何分支

清点员引的原话是 `training_input_scope1/REPORT.md`:
> 「generation/HOLD **目标**修复在 **`build_targets.py`**, funding generation/HOLD 修复在 **`build_funding.py`**」

我对全部 11 条分支逐条查过:
```
8990ebd3→0  6e6f5dc6→0  4dca09cf→0  9fb7a527→0  86dd0c8f→0  9528b908→0
a90dc829→0  5517eeeb→0  43643e83→0  fed0f391→0  d0d82862→0
```
(判据: `git ls-tree -r --name-only <sha> | grep -cE "(^|/)(build_targets|build_funding)\.py$"`)

**`build_targets.py` 和 `build_funding.py` 在 11 条分支上一份都没有。** ⇒ **C6 里"目标"和"资金费"两半, 我逐代码审不了, 只能审特征面板遮罩那一半。** 这与 `[[dead_contracts_frozen_rows_in_research_data]]` 和 `[[funding_settlement_interval_unit_bug]]` 正好是同一个病灶位置, 所以这个缺口不是小事。

### 我能审的那一半(`generation_windows.py`): 机制成立, 但覆盖面极小

**覆盖面**: `receipts/GENERATION_PROBE_SUMMARY.json` 原文
> `"status_counts": {"ACTIVE_KNOWN_START": 4, "LEGACY_CONTINUITY_UNAUDITED": 825}`

**829 名里只有 4 名(AERGO/AIA/LIT/PUMP)得到任何世代修复; 825 名走 L47-48 的 `continue`, 原样不动。** `masked_row_count` 实测只有 `AIAUSDT: 9351, LITUSDT: 1362`。

**PIT 门是真的**: L50 只采纳"公告时刻 ≤ 观测时刻 **且** 生效时刻 ≤ 观测时刻"的事件。`DESIGN` 说 `O=E+960`(E+16 分)。
**边界算术我验过**: L67 `first=((birth+300000+299999)//300000)*300000`。birth 落在 5m 边界上时 `first=birth+300000`; birth 在 `300000k+100000` 时 `first=300000(k+2)` —— 两种情形都**恰好等于 L65 遮罩后的第一根完整 bar**。✓ 该 bar 的 ret5 会引用旧世代最后一根 close, 所以 L68 把它重置为 NaN 是对的。
**失败闭合**: L53 / L56 在 CLOSE 不匹配当前 instrument、OPEN 与活跃 instrument 重叠时 `raise`。✓
**排序**: L51 同一 `effective_ms` 下 CLOSE 排在 OPEN 前。✓ 同刻重新上市处理正确。

**它自己点名的未闭合口子**(`GENERATION_FEATURE_DESIGN.md` 原话, 我照抄):
> 「log_qv 的极小正值理论上可在 f16 下溢, 不能据公式推全部原 qv 精确正性; 必须先在 2025–26 所有 E×829 上 ... 逐格核验」
> 「实际活动代理在 2025–26 完整 3648×829 共 3,024,192 格与 book 原活动逐位差 0; **2025 前条件限制保留**」

⇒ 活动门 `current_bar_activity`(L80-85, 用通道 1/3/4 的 `isfinite & >0`)**只在 2025–26 被对照过, 2022–2024 没有** —— 而那正是训练轴的主体。代码自己的 docstring L81 写着「**Cache proxy requires separate raw-mask calibration before formal use.**」—— **自述未就绪。**

### ★ 变异对照: 三条里 **一条强、一条弱、一条是空对空**

`probe_generation_components.py` + `receipts/GENERATION_PROBE_SUMMARY.json`:

| check | 它做了什么(我读的代码) | 我的判断 |
|---|---|---|
| `all_active_no_boundary`(L32) | 空 calendar + 全员当根活跃, 旧 `compute_anchor` vs 新 `compute_generation_anchor`, **全 payload 逐位相同**, `n=400` | ✓ **强**。基线非空(真 P2 数据、400 成员), 证明"不触发修复时新路径是逐位 no-op" |
| `current_bar_gate`(L40-43) | 把一名的通道 4 置 0, 断言 `member in old['payload']['pair_s']` **且** `member not in new[...]`, 并记录补位者 `entered:[619]` | ✓ **强**。两臂都断言了, 不是单边 |
| `old_generation_values_ignored`(L35-36) | 合成 CLOSE/OPEN 后, 把 `changed[ts*1000<=birth, member, :]=123` 再算, 要求位差 0 | ⚠ **弱**。扰动的格**正好就是遮罩掉的格**, 所以它证明"遮罩生效", **不能区分"遮罩范围对"和"遮罩把一切都盖了"**。缺一个反向正控(扰动 birth 之后的格 ⇒ 输出**必须**变) |
| `future_announcements_ignored`(L37-39) | 未来公告时刻 +100000ms, 要求位差 0 | ❌ **空对空**。两臂的公告都在未来 ⇒ L50 的 `known` 两次都是空表 ⇒ 两次都不遮罩 ⇒ 位等是**恒真**。正确的对照应是"未来公告 calendar 的 payload == 空 calendar 的 payload", 而 `noop`(L32)已经算出来了, 它却没拿来比 |

**`test_generation_windows.py` 只有 6 个 `def test_`**(我 grep 计数), 而 DESIGN 声称「当前 39 项单元测试覆盖窗口/活动基础边界」—— 那 39 项分布在 `tests/` 的 11 个文件里, 我没有逐个打开。

### 真值 / 人口能不能拆开 —— 我的答复
清点员说"这两件在同一批提交里, 我没能分开"。**在遮罩这一层, 它本来就分不开**: `view[rows,j,:]=np.nan` 同时改了该名的取值(变 NaN)和它在截面 rank 分母里的资格。**可分的地方在消费端**: 同一份遮罩面板, 下游可以 (a) 把 NaN 名保留在秩基里按缺失处理, 或 (b) 从秩基剔除。跑这两个臂就能把"值"和"人口"拆开。**codex 没跑这一对**, 而且 DESIGN 自己写了「成员变化后其他名的截面 rank 可变化, 报告成员 diff 而不伪称未受影响名所有 rank 位等」—— 它知道这件事, 只是没做对照。

### 判决: **无法判定(缺什么)**
缺的具体是三样:
1. **`build_targets.py` / `build_funding.py` 的源码**(在 pod2 `/workspace/`)—— 没有它们, "generation/HOLD 目标与资金费修复"这句话无法验证任何一个字。
2. **`future_announcements_ignored` 的非空对照**(把未来公告臂对到空 calendar 臂), 和 **`old_generation_values_ignored` 的反向正控**(扰动 birth 之后的格必须让输出变)。
3. **2022–2024 的活动代理逐格对照**(它自己列为限制)。
我能给的正面判断只有: `generation_windows.py` 这 93 行的 PIT 门与边界算术是对的, 覆盖 4/829 名。

---

## C7 · E60 资金费排在 reduce-only 退出之前

### 改动的确切代码
- commit **`a23e37b327169ab236ffcfb32fcd780415e833c6`**(2026-09-15 22:12, 分支 `codex/fullchain-continuation-20260914`)
- `.../integration/current_economic_risk_20260915/e60_funding_successor/{risk_engine.py, risk_path_runner.py}`(我实测 `risk_engine.py` 的 sha = `8771e24e3c4724ee62703b1cb57bbfb3b0aeef788a6376182b4067921fd70630`, 与 `risk_path_runner.py:30 ENGINE_SHA` 和 `native2/RESULT.json` 所钉一致)

**闸门被松开**(`SOURCE_DIFF.patch`, `risk_path_runner.py`):
```
-    need(count==0,'funding E60 collision outside inherited coverage applicability domain')
+    need(PRIORITY['FUNDING'] < PRIORITY['RISK_ATTEMPT'],'funding before risk-only exit')
+    need(hashlib.sha256((Path(__file__).resolve().parent/'risk_engine.py').read_bytes()).hexdigest() == ENGINE_SHA,'endpoint-guarded exact reduce-only engine')
```

**守卫被加上**(successor `risk_engine.py` L102-110, 逐字):
```python
102:            # Original coverage is [start,end). Certify the settlement instant
103:            # before any whole-book exit can remove its held obligation.
104:            # FUNDING and lifecycle events at this millisecond already ran.
105:            for sym,p in sorted(s['positions'].items()):
106:                if p['qty_exact']=='0':continue
107:                t=e['ts_ms'];known=self.coverage(sym,p['instrument_id'],t,t+1)
108:                require(type(known) is bool,'funding boundary oracle exact bool')
109:                if not known:
110:                    raise base._Unknown('MISSING_HELD_FUNDING_BOUNDARY_COVERAGE',symbol=sym,start_ms=t,end_ms=t+1)
```

### 它声称的机制
`e60_funding_successor/DESIGN.md` 原话:
> 「The original four-path batch stopped before any cash path. There are **8,638 actual funding rows at E60**; the zero-collision prerequisite was too narrow.」
> 「Independent review found that deleting the E60 gate alone was insufficient: **original coverage is [start,end), and funding(t) advances clock to t. Before ANY E60 exit, therefore check [t,t+1ms) for every still-held position.** ... Failure makes the path unmeasurable before any exit; already-booked funding remains.」

### ★ 机制是否成立 —— 我核实了, **成立**, 三处源码互相咬合

1. **区间确是半开**。`dynamic_cash.py` L160-163 docstring 逐字:
   ```
   funding_coverage(symbol, instrument_id, start_ms, end_ms) must certify that
   ALL cash obligations in the held half-open interval [start_ms, end_ms) are
   enumerated/priced by the supplied event source.
   ```
2. **时刻 t 本身永远只由"下一次时钟推进"来认证**。L320-328(通用事件)与 L606-614(资金费批)两处覆盖检查都是 `self.coverage(sym, ..., clock_ms, ts)`, 即 `[clock, ts)` —— **不含 ts**。
3. **而两处循环都 `if p['qty'] != 0`**(L321-322 / L607-608)。**一旦某名在 t 被平到 0, 之后任何一次覆盖检查都会跳过它, t 这个瞬间就再也没人查了。**

**修前会出错的具体输入**: 全书经济停机已触发; 某名 X 在 t = anchor+3,600,000ms(E60, 恰在整点)仍持仓; 事件流里**没有** X 在 t 的资金费结算, 而覆盖神谕也**不知道** `[t, t+1ms)`。修前: 推进到 t 时查的是 `[clock, t)` —— 不含 t —— 通过; 然后 E60 reduce-only 把 X 平到 0; 此后 X 永远被跳过。**一笔真实的结算义务被静默平掉, 现金账仍报 `RESEARCH_PATH_OPEN`。** 修后: L107 先查 `[t, t+1)`, 不知即 `MISSING_HELD_FUNDING_BOUNDARY_COVERAGE`, 整条路 `UNMEASURABLE`, **已入账的资金费保留**(`dynamic_cash.py:598-599`「Unknown cash is never replaced by zero.」)。

我把它的测试 `test_missing_boundary_event_cannot_be_closed_away`(L38-41)对着两份源码走了一遍:
```python
 40:   e.coverage=lambda sym,iid,start,end: not (start<=t<end)
```
该 lambda 只在被问的区间含 t 时返 False。**修后**守卫问 `(t,t+1)` ⇒ `start<=t<end` 为真 ⇒ False ⇒ 炸。**修前**只有通用检查问 `(clock,t)` ⇒ `end==t` ⇒ 条件为假 ⇒ True ⇒ 放行。**这条测试确实能区分修前修后。** 这是我自己的代码追踪, 不是转述它的话。

**为什么原来那条闸门存在**: base `path_runner.py:28-33` 的 `counts` 只覆盖偏移 20/24/25/55 分钟(`1200000,1440000,1500000,3300000`), **不含 E60 的 3600000**。原因很清楚: 那几个偏移都不在整点上, 币安结算永远撞不上; 而 **E60 = 整点, 必然撞上**(8,638 次)。所以旧的 `need(count==0)` 让整条停机臂**根本跑不出数**。⇒ **修前的失败形态是"拒跑", 不是"跑出错数"。** 把闸门松开必须配一个守卫, 它配了 —— 设计上是对的。

### ★ 修法是否正确 —— **对, 但欠修一处同族缺陷**

对的部分: 守卫位置在**任何成交发生之前**(L105-110 整个循环跑完才进 L111 的成交循环); `qty_exact=='0'` 跳过是对的(无库存无义务); 神谕返回值必须是精确 bool(L108); 失败时抛 `_Unknown` 而非 `ValueError`, 走"路径不可测量"而非"崩溃"。

**欠修**: **同一类"在瞬间 t 把义务平掉"的洞, 对 `_on_close`(生命周期 CLOSE)仍然敞着。**
- `PRIORITY = {'DAY':0, 'FUNDING':1, 'CLOSE':2, 'OPEN':3, ...}`(`dynamic_cash.py:21-22`) ⇒ 同刻 FUNDING 先于 CLOSE, 所以**已知**的资金费不会被 CLOSE 吃掉;
- 但 `_on_close`(L635-652)**没有任何边界覆盖检查**, 而它会 `p.update(qty=0., qty_exact='0', ...)`。**t 时刻一笔未知的结算义务, 会被同刻的下市 CLOSE 平掉, 之后永不被查。**
- 更值得记的是: 它的测试 `test_same_time_close_open_has_no_new_generation_obligation`(L44-48)**把这个豁免当成期望行为写进了断言** —— 先在 t 对持仓名 A 发 CLOSE + OPEN, 再把 A 的覆盖设为 False, 断言 `status=='RESEARCH_PATH_OPEN'`。DESIGN 里对应的那句「A closed/reopened generation with **zero inventory** has no held obligation」说的是**零库存**的情形, 而测试里 A 在 CLOSE 之前**是有库存的**。**声明与实现对不上。**(这正是 `[[gate_exists_but_its_verdict_does_not_control_the_write]]` / `[[guard_one_line_past_where_you_stopped]]` 那一族。)

### ★ 红测 —— **不存在**
`e60_funding_successor/LOCAL_CONTROLS.json` 全文只有 9 个字段, 逐字:
```json
"old_actual_chunk": "07cc30", "old_actual_exit": 1, "old_tests": 11, "old_failures": 1, "old_errors": 1,
"new_actual_chunk": "4944a5", "new_actual_exit": 0, "new_tests": 14
```
我用 `git grep -I "07cc30" 8990ebd3` 全树搜过: **除了这一行 JSON 自身, 没有任何对应的输出文件。** 那次"旧 11 测 2 红"的运行**没有留下任何 stdout/stderr**。DESIGN 里写的「Original failed receipts are retained」在这一点上**没有兑现**。

更关键: **它给了自己一个完美的变异对照钩子, 却从没拉过。** `test_e60_funding.py` L7 / L12 逐字:
```python
  7: engine_source=Path(os.environ.get('E60_ENGINE_SOURCE',str(P/'risk_engine.py')))
 12: source=Path(os.environ.get('E60_RUNNER_SOURCE',str(P/'risk_path_runner.py')))
```
把这两个变量指向 `../risk_engine.py` / `../risk_path_runner.py`(冻结的修前版本)再跑同一套 14 测, 就是教科书式的"修前必红"。`git grep -E "E60_ENGINE_SOURCE|E60_RUNNER_SOURCE" 8990ebd3` 在整棵树里**只命中这两行定义本身**(和 `native2/completed/` 里的同一份拷贝), **零次调用**。

绿测是真的: `native2/completed/native2/execution/STDERR.log` 逐名列出 14 个 `... ok` + `Ran 14 tests in 5.578s / OK`; `native2/RESULT.json` 带 argv(`/workspace/venv/bin/python .../test_e60_funding.py -v`)、`actual_child_exit: 0`、stdout/stderr 的 sha256、64 个 source pin、`all_fsync_and_sha_equal: true`。**绿是可信的; 只是没有配对的红。**

### 逐位控制: **有(源身份层), 无(结果层)**
`SOURCE_LOCK.json` 有 ~50 个本地 pin + 同样多的远端 pin; `BASE_SHA='8d8ddf8a…'` 我**独立实测**了 `6e6f5dc6` 上的 `dynamic_cash.py` = `8d8ddf8a002a9de7a613ce61c6bb0a18e7acd2cf12690cd5080d1326c2e4b9ce` ✓ 一致。
**但没有**"修前 vs 修后在同一批真实事件上的现金逐笔差"。DESIGN 说「No fee, funding amount, quantity arithmetic, model, 55/45 blending or halt-trigger formula changed」—— **这是断言, 不是对账。**

### ★ 它根本不在交付数字的路径上
我逐行确认(分支 `6e6f5dc6`, 目录 `book/dynamic_frame_inputs_20260915/current_rule_mark_valuation_20260915/`):
```python
current_plan.py:16   rows=[row for row in rows if row['id']=='nohalt_current_main']
current_modes.py:24   if kind!='RISK_ATTEMPT' or mode=='ECONOMIC_HALT':yield e
current_consumer.py:22-23
  if mode=='ECONOMIC_HALT':c['economic_risk']=risk.contract();return risk.RiskEngine(c,funding_coverage=coverage),c
  return base.Engine(c,funding_coverage=coverage),c
```
⇒ **608 日那一跑只有 `nohalt_current_main` 一格, RISK_ATTEMPT 事件被整批过滤掉, 引擎是 `base.Engine` 不是 `RiskEngine`。C7 的守卫一次也没执行过。**
有趣的是, `current_admission.py:27` 仍然把 `e60_funding_successor/SOURCE_LOCK.json` 的 sha(`E60_LOCK_SHA='286bd16d…'`)**钉为必需依赖** —— **被钉住但从未被调用**。引用 C7 时必须说清这一点, 否则很容易读成"608 日结果里包含了 E60 修正"。

### 判决: **采纳但需改**
机制真、修法对、绿测实。要补两件才能当受据用:
1. **拉一次那个已经写好的钩子**: `E60_ENGINE_SOURCE=../risk_engine.py E60_RUNNER_SOURCE=../risk_path_runner.py python test_e60_funding.py -v`, 留输出。没有这一步, "修好了"这句话只有断言。
2. **把守卫推过 `_on_close`**, 或者明确写下"同刻 CLOSE 豁免边界检查"的理由并把 `test_same_time_close_open_...` 的断言改成有库存/无库存两个分支。现在的状态是**声明说零库存、测试测有库存**。

---

## 判决汇总表

| 项 | 机制成立? | 修法正确? | 红测 | 逐位控制 | 判决 |
|---|---|---|---|---|---|
| **C1** 三月 raw 回填 | ✅ **机制**源码级已证(`canonical_data.py:18-23` 跨洞前推 + `:5` ±0.30 裁剪)。**代价量级**读自收据 `old_next_return_f16`(隔一层, 带 `repair.py:62` 逐位闸门), 且是**下界**(全轴另有 134 个内部价格洞未修) | ✅ 边界逐条对; 曾疑欠写已排除(`canonical_data.py` 只有通道 0 跨行); 11 格残差未解释 | ✅ **行为级**(`repair.py:62` 旧值逐位重放 + `test_repair.py:39` 变异对照, 基线绿被断言) | ✅ 三处硬 raise(`:75` `:177` `:183`) | **采纳** |
| **C2** 2024-12 档还原 | ✅ 740 档确实缺失 —— 但缺在**它自己的 pod**(磁盘配额), 不是我们的数据 | ✅ 两阶段校验 + fsync + `os.link` 原子不覆盖; 1 处计数语义瑕疵 | n/a(文件搬运) | ✅ 740×(before/after) sha | **不采纳**(对我们无内容; 建议从"真值修复"计数里移出) |
| **C3** 三名标签重算 | ✅ 成立; 169/169/181 = 519 与 24,768 bar 我独立算术复核一致 | ✅ 支撑集由时间几何定义; NaN 安全字节比较 | ✅ 同 C1(`:159` 旧值重放 + `test_repair.py:41-49` 含负控) | ✅ `:171-178` 回填后整组位等 | **采纳**(但须按"多了 519 个样本"记, 非"数值改正") |
| **C5** AERGO 4 点 | ✅ 成立; 我用 `dynamic_cash.py:366-370` + 时间戳独立确认它是 570→608 日的唯一闸门; 但选择判据 = "谁挡住了运行", 全轴同类缺口尚余 2,939 | ✅ 实现最严(哨兵拒过修 / `r[6]+1==when` 无前视 / 逐事件 canonical 还原比对 / 少一个就炸) | ⚠ **RED1 是假红**(ModuleNotFoundError); 但 8 条有绿基线的变异对照是真的 | ✅ `mark_valuation.py:60` 逐事件位等; ⚠ GREEN1 跑 17 测而入库 18 测 | **采纳但需改**(改记账口径 + 补第 18 测的绿 + 记 markPrice 混源) |
| **C6** generation/HOLD | ⚠ 遮罩那半成立但只覆盖 **4/829** 名; **目标与资金费两半的源码(`build_targets.py`/`build_funding.py`)在 11 条分支上 0 份** | ⚠ 能读的 93 行 PIT 门与边界算术正确; 活动代理自述"未就绪", 2025 前无对照 | ⚠ 三条对照: 1 强(`all_active_no_boundary`)+1 强(`current_bar_gate`)+1 弱(扰动的正是被遮的格)+**1 空对空**(`future_announcements_ignored` 两臂都不触发, 恒真) | ⚠ 有(同输入旧/新 kernel 位等, `n=400` 非空基线) | **无法判定(缺什么)** |
| **C7** E60 资金费排序 | ✅ 成立; 我从 `dynamic_cash.py:160-163/320-328/606-614` 三处独立推出半开区间 + `qty!=0` 跳过 = 平仓即失忆 | ⚠ 守卫位置/失败模式正确; **欠修 `_on_close` 同族洞**, 且其测试把该豁免当期望写进断言(声明说零库存, 测试测有库存) | ❌ **不存在**。`old_actual_chunk "07cc30"` 全树无对应物; 自带的 `E60_ENGINE_SOURCE` 变异钩子**零次使用** | ⚠ 源身份层有(BASE_SHA 我实测一致); **结果层无**(无修前/修后现金对账) | **采纳但需改** |

**额外一条必须随任何引用一起传下去**: **C7 不在 608 日交付数字的路径上**(`current_plan.py:16` + `current_modes.py:24` + `current_consumer.py:22-23` ⇒ 只跑 nohalt、RISK_ATTEMPT 被过滤、引擎是 `base.Engine`)。它只影响那条被弃用的 ECONOMIC_HALT 对照臂。

---

## 我没能回答的

1. ~~`canonical_data.py` 的 `to_channels` 我没有逐行读~~ —— **2026-09-16 已补读并关闭**(见 C1 §(a) 与"曾疑欠写, 现已排除")。**替代它成为 C1 最弱一环的是**: 我**没有打开过 `channels7.npz`**(pod2, 本地无)。`old_next_return_f16` 是 codex 的重放值, 只靠 `repair.py:62` 的逐位闸门与冻结面板绑定, 而**那次闸门跑没跑, 我只有它自报的 `status=PASS…` 和 `EXIT.json`**。要彻底关死需要在 pod2 直接读 `channels7.npz[last+1, j, 0]`。另: 该坏值是否被 `build_features.py` 的特征列消费, **我没核**(见 C1 §(d))。
2. **`audit_raw_overlay.py`(63 行, 三份拷贝)我没打开。** 报告自报的「171,752,832 outside-support raw scalar cells were bitwise equal」和「20 个月逻辑 SHA 只替换 4 个」全部出自它。所以 C1 的**第二阶段**我只读了自报。
3. **`build_targets.py` / `build_funding.py` 不在任何分支**(我逐条查了 11 条)。C6 里"generation/HOLD 目标修复"和"funding 修复"两半, **一个字都无法逐代码验证**。要审必须从 pod2 `/workspace/` 取。
4. **`tests/` 下另外 10 个文件我没打开**(包括 `test_funding_boundary.py`、`test_generation_runtime.py`)。DESIGN 声称 39 项单测, 我只 grep 到 `test_generation_windows.py` 有 6 个 `def test_`。
5. **C7 的 14 测我没有实跑, 也没有拉变异钩子。** 我只做了源码追踪, 论证"`test_missing_boundary_event_cannot_be_closed_away` 在修前引擎上应当失败"。**这是推理, 不是实测。** 要定论需要跑那个钩子 —— 那是 lead 可以指派的一步, 成本极低。
6. **C5 的两个流 SHA(原 `a5563c82…` / 升级后 `f6156f07…`)我没有独立重算。** 「1,653,238 个事件里只有 4 个变」目前只有它的自报 + `mark_valuation.py:60` 那个**逐事件**的位等控制作支撑。后者很强, 但它保证的是"每个被改的事件只改了那一个字段", 不是"只有 4 个事件被改"(那由 L63 的 `seen==set(TARGETS)` 保证, 也还算硬)。
7. **候选集之外那 2,848 个缺失估值格(2943 − 95)的分布我没看。** 它们是否集中在某些已下市名、是否与 `[[dead_contracts_frozen_rows_in_research_data]]` 是同一批, 我没查。
8. **`GRVTUSDT#legacy-unaudited` 这个 instrument_id 我没有追。** 一个带 "legacy-unaudited" 字样的世代标识出现在实际参与回放的日历里, 值得单独看一眼。
9. **C6 的 `probe_generation_components.py` 我读了但没跑。** 我对 `future_announcements_ignored` 是"空对空"的判断来自 `generation_windows.py:50` 的过滤条件 + 该探针 L37-39 两臂的公告时刻都 > 锚时刻。**这是代码推理, 若 `compute_generation_anchor` 内部另有别的公告消费点, 我的判断会偏。**
10. **`native_controls_readback1/RESULT.json` 的 "51 项控制" 没有逐测名单。** 所以 C5 那第 18 个测试到底跑没跑, 我无法定。

---

## lead 复核(2026-09-16 12:0xZ) —— 哪些我自己核了, 哪些还不能传

### ✅ 已独立证实(证据在 codex 自己的产物里)

**C5 的两组关键数字, 全部对上**
`book/dynamic_frame_inputs_20260915/current_rule_mark_valuation_20260915/tail_candidates1/STDOUT.json`
(schema `TAIL_VALUATION_MISSING_CANDIDATES_ONLY_1`, utc 2026-09-15T15:25:42Z):

| 字段 | 值 |
|---|---|
| `post_start_ms` | 1784851200000 = **2026-07-24T00:00Z** |
| `terminal_ms` | 1788220800000 = 2026-09-01T00:00Z |
| `all_axis_active_missing_cells` | **2943** |
| `candidate_missing_cells` | **95** (`rows = list[95]`) |
| `old_held_names` / `candidate_names` | 261 / 427 |
| `new_http_requests` | 0 |

**时间几何独立复核**: 2026-07-24 → 2026-08-31 = **38 天**; 2025-01-01 → 2026-08-31 = 607 日差 = **608 个日节点**。
**尾扫的起点 `post_start_ms` 就是那 4 个 AERGO 点所在的日子。**
⇒ 「608 日里的最后 38 日(含 2026-08 那个 −5.96% / MDD 15.53% 的月份)建立在这 4 个数上」**成立**;
「候选集 95 个同类缺口只修了 4 个」**成立**。

**C7 不在 608 日路径上** —— `current_plan.py:16`(只留 nohalt) + `current_modes.py:24`(过滤 RISK_ATTEMPT)
我在快照 `CODEX_EVIDENCE_SNAPSHOT/devices/` 里逐行读过, **成立**。

### ⚠ 暂不可传 —— 一个数我追溯不到
报告 C1 节称「冻结面板里 2026-03-01 00:05 那根 5 分钟 bar 的 ret5 是 **−16.87%**, 真值应为 **−1.83%**」
(以及 BMT 那格 +0.65% 被写成 −15.53%)。**我无法追溯这几个数**:

- `channels7.npz` 在**本地 worktree 与 pod2 均不存在**(`find` 全盘);
- `canonical_month_repair_20260914/` 下对全部 `*.md` / `*.json` 搜 `16.8` / `1.83` / `15.53` / `0.65` —— **零命中**;
- 该目录无任何含 `old_ret5` / `ret5_old` / `first_after_gap` 的文件;
- 含 `old_channels` 的只有 `repair.py` 与 `test_repair.py` 两个**源码**文件, **没有补丁数据**。

**故本次交付一律不引用这几个数。** 已去信审查员问出处(读面板 / 还是推算), 答复到后按其口径修订本节。

**但 C1 的「机制成立」不依赖这几个数** —— 它依赖的是 `repair.py:62` / `:159` 那条**旧值逐位重放门**
(把缺失月重设 NaN 后重算通道, 要求与冻结缓存逐字节相同)与 `:75` `:177` `:183` 三处硬 raise,
这些我读过源码, **成立**。缺的只是「代价有多大」的量级证据。

### 判决修订(在量级证据补上之前)
| 项 | 原判决 | lead 修订后 |
|---|---|---|
| C1 | 采纳 | **采纳(机制已证)**; 但「代价量级」一栏标 **未证**, 不得引用 −16.87% |
| C3 | 采纳 | 不变 |
| C5 | 采纳但需改 | 不变; 其两组数字我已独立证实 |
| C7 | 采纳但需改 | 不变; 「不在 608 日路径上」我已独立证实 |
| C2 | 不采纳 | 不变 |
| C6 | 无法判定 | 不变 |

---

## lead 复核 · 第二轮(2026-09-16 12:1xZ) —— C1 量级证据**已补齐并独立复算**

第一轮我拦下了 −16.87% 这个数(追溯不到)。审查员给出了出处, **我自己跑了, 对上了**。

### 出处(可复跑)
`git show a90dc829:multi_asset/exports/research/codex_causal_fullchain_2026-09-14/data/canonical_month_repair_20260914/completed/build2/RESULT.json`
字段 `repaired_months[i].old_next_return_f16` / `.new_next_return_f16`。

**我第一轮 grep 打不到的原因已查明, 不是数字不存在**: 值以**分数**存(`-0.168701171875`),
报告里被百分号化成 `−16.87%`, 于是 `grep "16\.8"` 必然落空。**这是表述问题, 已由审查员更正。**

### 三条原始记录(逐字)
| symbol | previous_close | last_inserted_close | next_close | `old_next_return_f16` | `new_next_return_f16` |
|---|---|---|---|---|---|
| 1000000BOBUSDT | 0.01482 | 0.01255 | 0.01232 | **−0.168701171875** | −0.0183258056640625 |
| BMTUSDT | 0.01829 | 0.01535 | 0.01545 | **−0.1552734375** | **+0.0065155029296875** |
| MTLUSDT | 0.2699 | 0.2946 | 0.2951 | +0.0933837890625 | +0.001697540283203125 |

### ★ lead 独立复算: 3/3 逐位相同
我不看它的收据值, 只用表中的原始收盘价重算:
- 旧值 = `np.float16(next_close / previous_close − 1)` —— **跨整个 NaN 段**
- 新值 = `np.float16(next_close / last_inserted_close − 1)` —— 对上一根真实 bar

三行**全部与收据逐位相同**(float16 位级)。

**代价**: −16.87% → −1.83% · **−15.53% → +0.65%(符号翻转)** · +9.34% → +0.17%。
**冻结面板里有三格, 把整整一个月的涨跌当成一根 5 分钟收益写了进去, 其中一格连符号都是反的。**

### ±0.30 裁剪: 出处已换成对方自己的源码
`data/canonical_data.py:5` `CLIPS=[(-.3,.3),(0,.5),(0,1),(0,25),(0,20),(-5,15),(0,1)]`
+ `:32-33` `np.clip(v[good],lo,hi).astype(np.float16)`。
三个旧值 `|x| < 0.30` ⇒ **一格都没被裁掉, 原样进了通道 0**。

⚠ 审查员**主动更正**: 上一版此处引的是**我方**记忆条目 `[[cache_ret5_channel_clipped_at_0p30…]]`,
那是**把我方事实外推到对方链路**。现引对方自己的生产算术。**这个自我更正是对的, 记一笔。**

### 仍未验(已降级, 不得写成已验)
「**直接进了特征面板**」→ 降级为「**进了面板文件的通道 0; 是否被 `build_features.py` 的特征列消费, 未验**」。

### 代价是**下界**(依据已核)
`ORIGINAL_FULL_AXIS_AUDIT_SUMMARY.json` 实测: `price_gaps.kinds.INTERNAL = **134**`
(另 `TERMINAL 29` · `at_least30days 158` · 涉 162 符号 / 829 全轴)。
同一条前推**对任何 NaN 段一视同仁、不问成因**, 故每个 INTERNAL 洞各有一个同类重连格, **一个都没修**;
且 <7 天的短洞根本不在盘点内。
**但不得说「还有 134 个同等严重的缺陷」** —— 其中多少是"该修的档案缺失"、多少是"合法停牌(跨段收益是真的)",
无人分过。审查员自己写明了这一点, **这个克制是对的**。

### 顺带关掉一个开放问题
补读 `canonical_data.py:24-31` 确认通道 1~6 全是**逐行**运算, **只有通道 0 跨行** ⇒
C1 只在 `last+1` 改通道 0 **确实不欠写**。

### C1 最终判决(修订)
| | 第一轮 | 第二轮(本节) |
|---|---|---|
| 机制成立 | ✅ 源码级 | ✅ 不变 |
| **代价量级** | **未证, 禁引** | ✅ **已证, 3/3 逐位独立复算** |
| 是否进特征列 | — | ⚠ **未验** |
| 判决 | 采纳(机制) | **采纳** |

**C1 最弱的一环现在是**: 没人直接读过 `channels7.npz`(pod2 上也不存在), 那条逐位闸门
(`repair.py:62`, 对全 7 通道要求与冻结缓存 `same_bits` 否则 raise)**跑没跑只有它自报**。
准确表述: **「该值等于冻结面板对应格, 条件是 build2 那次运行确实执行了 L62 并退出 0」** ——
比"我读了面板"弱一格, 比"按收盘价推算"强很多。**引用请用这句话。**
