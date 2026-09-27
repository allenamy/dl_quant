> **创建:** 2026-09-27 06:3xZ | **Session:** session_01VNPQL7t93ECz7Xkrv9rH6n(news2) | **状态:** 结果(恒等控制,只作描述;不产生书层或模型层数字) | **作废条件:** 表中任一装置再改动(须对改动的行重跑);或参照产物被重建

# 结果:重建装置端到端干跑(2026-09-27,pod2)

**计划与判据**:`docs/PLAN_rebuild_devices_dry_run_2026-09-27.md`。lead 于 acd2303b6 冻结,冻结补遗 1 为 093f72527;另有两次续跑裁定:D3 因配额挂起,D5a 修复后续跑。
**问题**:d3a7f013d 把链上装置的写文件改成走 `common/durable_write.py`(ac8960d8b 又补了两处漏掉的 import);再加上三份收据补记的 argv 与解释器。在与上次交付完全相同的输入上重跑,产物是否与上次一致?

## 1. 逐行结果(以最后一次运行为准)

| 行 | 装置 | 结果 | 部分 | 说明 |
|---|---|---|---|---|
| S0 | 比较器自测 | PASS | 1–4 各一次 | S1–S15 全过,含 1 ULP、dtype、字节翻转、argv --out 断言 |
| D7 | `d10_make_symlists.py` | IDENTICAL | 1 | 80 个文件逐字节相同,文件集合相同 |
| D8 | `d10_manifest_gate.py --selftest` | PASS | 1 | SELFTEST GREEN 7/7 |
| D1 | `d10_build_ledger_ms.py` | IDENTICAL | 1 | 数组逐位相同;收据逐键相同;183 s |
| D2a | `d10_build_fund_state.py --mode snap` | IDENTICAL | 1 | 数组与收据相同 |
| D2b | `d10_build_fund_state.py --mode d10` | IDENTICAL | 1 | 数组与收据相同 |
| D3 | `d10_stage2_assemble.py` | IDENTICAL | 4 | 第 1 部分 ERROR:/workspace 配额满(EDQUOT),见 E-0927-D;第 2 部分记 NOT_RUN(quota);lead 释放配额后单独补跑,写前探针 4,034,360,591 字节完整写入并删除;56 s |
| D4a | `d10_parity_gate.py`(snap control) | IDENTICAL | 2 | 参照为 521c6a28 产出的收据(GREEN) |
| D4b | `d10_parity_gate.py`(common window) | IDENTICAL | 2 | RED 判词与内容逐键复现 |
| D4pc | `d10_parity_gate.py --positive-control` | PASS | 2 | CONTROL_PASS(只作功能检查,按补遗 1) |
| D5a | `d10_p2_ledger_vs_archive.py`(旧 P2) | IDENTICAL | 3 | 第 2 部分 ERROR,是**干跑抓到的真缺陷**,见 §2;修后 IDENTICAL |
| D5b | `d10_p2_ledger_vs_archive.py`(ledger_ms) | IDENTICAL | 3 | 126 s |
| D5c | `d10_legs_rn8_vs_archive.py` | IDENTICAL | 3 | 与 D5a 同一缺陷;修后首次实跑 |
| D6 | `d10_live_ledger_vs_archive.py` | IDENTICAL | 3 | 输入快照仍在,sha 91a1a2cd;没有 NOT_RUN |
| D9 | `d10_archive_inventory.py`(3 名,真实请求) | IDENTICAL | 3 | BTCUSDT、ETHUSDT、SOLUSDT 的盘点条目相同 |
| D10 | `d10_pull_months_pod2.sh` + rev 2 拉取器(3 名,真实拉取 2026-08) | IDENTICAL | 3 | COMPLETE all_verified=yes;3 个 zip 逐字节相同;manifest 条目相同 |

**gate_sha256 的豁免**(补遗 1 第 3 条):manifest 门的两个版本,793c5eb2 与 6a8b16ca,ast.dump 相等(ast sha 为 21aebc27a281d077,两侧相同)。D5a–D6 的收据里,两侧的取值恰好就是这两个版本。

## 2. 干跑抓到的缺陷(已修)

- **缺陷**:`d10_p2_ledger_vs_archive.py` 与 `d10_legs_rn8_vs_archive.py` 在 d3a7f013d 里改成调用 `DW.write_json`,但没有插入 import。审计本身跑完了,在写收据的最后一行抛出 NameError。
- **没被早些发现的原因**:解析检查、`--help`、裸写检查都过了,因为这个名字只在 main() 的最后一行才用到。
- **修复**:ac8960d8b。类守卫为契约测试 C5:runbook 点名的装置里,不许有无法解析的名字。它先在恰好这两个装置上判红,修后绿,26/26;扫描全目录没有其它命中。
- **影响面**(lead 要求核实):有缺陷的版本只存在于仓库(05:24Z 到修复)和 pod2 的干跑目录。pod2 上其它副本都是补丁前的版本,自 09-26 起未变;补丁之后,两台机器上都没有这两个装置的任何新产物。**这两个装置只在干跑里首次触发**,没有任何产物需要标为待重核。

## 3. 一处更正:npz 文件 sha 其实可以复现

- 计划 §1 第 1 条、d3a7f013d 的提交信息、比较器的 docstring 都写着「npz 文件本身的 sha 无法复现,因为 zip 条目带写入时刻」。**这是错的。**
- 实测:干跑写出的四个 npz,**文件 sha 与参照完全相同**:
  - NEWS_FEATURES_D10 f1cd3fa2
  - fund_state_snap 35cc8f30
  - fund_state_d10 f07e4ebd
  - ledger_full_ms e179071d
- 原因:numpy 的 `savez` 写出的 zip 条目时间固定为 1980-01-01,实测 date_time = (1980, 1, 1, 0, 0, 0)。
- 我先前的说法是从另一件事推广过来的:KING_OOF.npz 里带着每次运行都会变的 model_sha256 数组,所以它的文件 sha 会变。那是**内容**在变,不是容器在变。
- **对本次判据的影响**:按冻结判据,npz 的文件 sha 被列为「易变」。事实上它们全部相等,所以结果比判据要求的更强,没有任何一行的判词受影响。今后比较 npz,文件 sha 相等可以作为额外证据;不相等时,仍然要比数组,才能区分「内容变了」和「容器里某个辅助字段变了」。

## 4. 没有覆盖的

- `nc_p2_build.py`、`nc_legs.py`(生产派生的复制件,未改)、训练器、生产者树、执行器,都不在本次范围内。
- 干跑只证明「同输入,同输出」,不证明十月的新输入(九月的 zip、新轴)能走通。那部分由 runbook §1–§2 的恒等控制在十月当时负责。
- 两个尚未写的装置(ledger_ms rev 2、按 argv 取月份的复审计驱动)写好后,同样要先过契约测试与各自的控制。

## 5. 收据

- `multi_asset/exports/research/news2_2026-09-23/receipts/dryrun_2026-09-27/part{1,2,3,4}/`:每部分的 `DRYRUN_RESULT*.json`、`dryrun.log`,以及各行装置的 stdout/stderr。
- 装置:
  - 比较器 `d10_dryrun_compare.py`(sha 1c8f6148…)
  - runner `d10_dryrun_run.py`(rev 2,sha aca7dd6a…)
- pod2 上的产物:`/workspace/d10_dryrun_2026-09-27/out/`,3.1 G,与参照逐位相同,是冗余副本。清理与否由 lead 定。

## 6. 删除前的产物清单(lead 06:4xZ 裁定:先记 sha 再删 `/workspace/d10_dryrun_2026-09-27/out/`)

四个 npz 的文件 sha 与参照逐字比对(参照 sha 取自各自上次交付的收据):

- `ms/ledger_full_ms.npz`: e179071d595521987450f89e1774a95775a2593d76277a9c9dc6d86dcbc31a88 — 参照 e179071d595521987450f89e1774a95775a2593d76277a9c9dc6d86dcbc31a88 — 相同
- `fund_state_snap.npz`: 35cc8f309267ea7b7019595178a8367947700c07f39ee6512ea42e2ec8069542 — 参照 35cc8f309267ea7b7019595178a8367947700c07f39ee6512ea42e2ec8069542 — 相同
- `fund_state_d10.npz`: f07e4ebdfa4310b10ee8ac6e1f631d0787adaa10a1803507f81e95539ccd46c7 — 参照 f07e4ebdfa4310b10ee8ac6e1f631d0787adaa10a1803507f81e95539ccd46c7 — 相同
- `NEWS_FEATURES_D10.npz`: f1cd3fa2b48e96ddf202a5098e08b9cc0ebcffda3bfc42c347743b9a5cd7d5fd — 参照 f1cd3fa2b48e96ddf202a5098e08b9cc0ebcffda3bfc42c347743b9a5cd7d5fd — 相同

其余文件(JSON 收据、symlists、syms3)已原样拷入 `receipts/dryrun_2026-09-27/out_small/`,逐文件 sha 与 pod2 相同。完整清单(sha256 与路径):

```
ba6c86ca34751a1c502385a508ad335fba4c46a1fee7416504af1519a7e046f9  ./D10_LEDGER_MS_VS_ARCHIVE_JAN_AUG.json
78bbf62e5af53063737181d9fbf03069f5c4a14ce7f8c190882bd6ec71db4459  ./D10_LEGS_RN8_VS_ARCHIVE_JAN_AUG.json
7b8a2283445ff7e5040962d5a9596d738dbc0f2e15a8fdf47f7b38245b5bb659  ./D10_LIVE_LEDGER_VS_ARCHIVE_2026-08_RESIGNED.json
44cdd5eb17641eb04ff17cf38a835d59734a2a90855ac1f96900f788e9e6cd0b  ./D10_P2_LEDGER_VS_ARCHIVE_JAN_AUG.json
d0b9750015da3db4ba2e0affa4ff81286eae6ff23c0223dd618846b1fe929e66  ./D10_PARITY_COMMON_WINDOW.json
254bc04a455bb421227331bc5cdb8d44b3eb5916484544e4724dd131060de997  ./D10_PARITY_POSITIVE_CONTROL.json
1b961e9ddf01425e483c67e4e4b332bf51280281d911217c4d5e4bd87125dd8e  ./D10_PARITY_SNAP_CONTROL.json
88b16aeb594af2dbe766f5186b5439c74b034652f6d7e85cc7492473c5a5cfee  ./DRYRUN_RESULT.json
5419083602bc44b9c7bef4f0813e8f8092802e45fc7437b733225747d8466826  ./DRYRUN_RESULT_part2.json
e0022e6013706984672a69c8f60ec233baad1befa4eb714d66863fd783fbe95e  ./DRYRUN_RESULT_part3.json
6666e12497bedf92bf2bbb63245cf5dd45a13d8043c64ba8d85af52ab6a8ba77  ./DRYRUN_RESULT_part4.json
27ca9a3b95d40ef87644977e7de699dc9b5fd36d01a973729c42b0cd6ab86b4c  ./INVENTORY_3.json
36e0429d932b8b51ccfb212524b6a5b3ffe96c8030670e02fda4e38e1d41606a  ./INVENTORY_3_progress.json
f1cd3fa2b48e96ddf202a5098e08b9cc0ebcffda3bfc42c347743b9a5cd7d5fd  ./NEWS_FEATURES_D10.npz
58c929dd0682a2751495cc70fe28ed1474358575e80e2fd016c48419ccbd5367  ./NEWS_FEATURES_D10_RECEIPT.json
f07e4ebdfa4310b10ee8ac6e1f631d0787adaa10a1803507f81e95539ccd46c7  ./fund_state_d10.npz
e7dd3562eaa61238ef5f3c8bdc7ab3e0f0ea49a1baa212c39d5c20fac1dce921  ./fund_state_d10_RECEIPT.json
35cc8f309267ea7b7019595178a8367947700c07f39ee6512ea42e2ec8069542  ./fund_state_snap.npz
7d0eed00c6b082d57b45b70a0c1662e5fa6bc73a3a0480fa77ab45226e30b599  ./fund_state_snap_RECEIPT.json
e800fab11f68a83dd7f737fcdbcb11623e044e18dca519b77775b6fef958f593  ./ms/D10_LEDGER_MS_BUILD.json
e179071d595521987450f89e1774a95775a2593d76277a9c9dc6d86dcbc31a88  ./ms/ledger_full_ms.npz
ceda859bbfafc5bd1ad5bbc1cc37e1cdc3b88bcf1b1120d2e6f274875f3c3375  ./symlists/2020-01.txt
ee011423efde61516e666f014e4fbccacd9ef91da5a6546570924486de49ae61  ./symlists/2020-02.txt
6cff9071fdfa7340149a71000c79338c7ffda95f56148b47b9a80c1161442bf3  ./symlists/2020-03.txt
6cff9071fdfa7340149a71000c79338c7ffda95f56148b47b9a80c1161442bf3  ./symlists/2020-04.txt
e8ff825d59e1d7e08840646561d8d13ea00216ed7f51a57d1db0b283e1d0c205  ./symlists/2020-05.txt
935ca9cf93793fcd00aede74b93066996b8adc919deff368949e7bf805a928e0  ./symlists/2020-06.txt
f3bfb5f0adad5f8f83d7f6b8446892532029aba84695b60ab475962f9c19dcb0  ./symlists/2020-07.txt
e96c4faf3df7b88e3a6ca06d329b1ce16cafcb5797a21552fddbc8bb7407efc6  ./symlists/2020-08.txt
7888a72f59107f798c3867fe8cf6c4a4280c6d7cc784fe24bc90e52651a30ad6  ./symlists/2020-09.txt
55adec54695f7a26b11aef7c02489878847dac07236ffd8b7fac8c5393a06cb9  ./symlists/2020-10.txt
c9bed96af9812d0772b5c2ccb9dd862444397979c4ac57aa38c67d20094d7e48  ./symlists/2020-11.txt
18c9a799934347c46fd2bfa9545552dff26b49255d52db23554369c7b3be0ed1  ./symlists/2020-12.txt
62e2a0907eb43404b1ae095fa73dba5ea8c32ae41a4e8a5f8a5fad7f18f9863e  ./symlists/2021-01.txt
ee3c4e0ee83f258119af04b550b34516225840e48d35ca1c3d6b734af78e3251  ./symlists/2021-02.txt
cde052bdfb4d18883a7d218c33585c713bda186f1608d2b246c4c5d5ffaee30c  ./symlists/2021-03.txt
b43d1f614f062fb092768119891dd6a2f5d79685069c825afb1f2b5741b5bda8  ./symlists/2021-04.txt
fbf59c9b8fbb46226371db0d15acb32b1de11a4949f22a9e55c3b0e9e4e18b3a  ./symlists/2021-05.txt
dd7486f92c28a32b704846d73b1611e6c4eee138a1e8b432feaafbd3fa82dc35  ./symlists/2021-06.txt
dd7486f92c28a32b704846d73b1611e6c4eee138a1e8b432feaafbd3fa82dc35  ./symlists/2021-07.txt
9e924cd83f4daf6cd0773663ab44deca2d93f91deac3d5dbd0a810e3123d1f16  ./symlists/2021-08.txt
8d4cb6c6dfac2596ebf70819dd74cf7d39e36a96149f8eb0eafb80110300a465  ./symlists/2021-09.txt
b6d930d7d0e30528763f903a0bd1dc2462baff03dbf0a245b1f0d9af26a5f079  ./symlists/2021-10.txt
87f643cf28e6d8127f8b2050ce222cbb6e293a4d073bb0b7df09cfc587aa6ba0  ./symlists/2021-11.txt
7ccbde2082fe38570ff79ab12d59ca6cf161c22256c7ce010a6034050a319568  ./symlists/2021-12.txt
66f68ac39648f649626b3bc7ca954bc844fe4751a0ad745a65e6babdae1a2858  ./symlists/2022-01.txt
09145712cd5e78c91250b48621300a201e1f1d9287101ee5dc9f994c9ae7690d  ./symlists/2022-02.txt
ac353ee21fd33e2e52799a84da83ce1276a7e3585221a8b89da4b230782eefeb  ./symlists/2022-03.txt
5003237e1d9fed3d718b5ce3c74230fd5bef9953d130b6841843b40c8c36050f  ./symlists/2022-04.txt
5a0f83bb9e14775de16119279b797dff91cd7f6f09e62b74329508331f4f859c  ./symlists/2022-05.txt
39b8a381111f724f7abe2c2975911e5d4b1a1627092e62824affcd8d546e464c  ./symlists/2022-06.txt
39b8a381111f724f7abe2c2975911e5d4b1a1627092e62824affcd8d546e464c  ./symlists/2022-07.txt
ba02bac56e09ca5a53eb872b6c2768ad0da0a33c02f23659e7b5cabbf61661b5  ./symlists/2022-08.txt
a872cb81a197477555ac6bb64ed2d2dd8b03e3162beacd1956f32630a90f49cd  ./symlists/2022-09.txt
00f9bb167c0398577beeff30611c68b5178b2a22f2e38b4fc6df30856d3ca161  ./symlists/2022-10.txt
cc5477ceeb05726635315f0298b3c5486fbb37bb6aca081ad93034a3bf698184  ./symlists/2022-11.txt
cc5477ceeb05726635315f0298b3c5486fbb37bb6aca081ad93034a3bf698184  ./symlists/2022-12.txt
94c7a1cc8013826528e14acdfa53e6e26a905e3c9d09e9cbc086aa2028992e59  ./symlists/2023-01.txt
2927ff28e72e4e49f471e4ba2db015bd2d8bc7a585b045641bfd2a73f0b9767b  ./symlists/2023-02.txt
9432ceff423689136e6c9a9b0568f8780d3cef8c132459385279c14285fc69c5  ./symlists/2023-03.txt
d9e68f43e618301dbd02f8348d65bad8bfdbe69a8a983230731e53c33b42d7b6  ./symlists/2023-04.txt
95c14b513101177fc652bdb516db358598e76d33671f28c456381c6134df52f0  ./symlists/2023-05.txt
f4fdf645b483041b7d93476633812f8172bd1532e5a11e7bcc0f560d9f04247d  ./symlists/2023-06.txt
5c50f56dada1eb60473f55dcf7fb968d8d75934f5ac6828ff27391f8ed0ee35d  ./symlists/2023-07.txt
c1a5bd4d4185d21dc46b57ac763e2adc6e0db5e11de95f19cd8905cae884ba07  ./symlists/2023-08.txt
057e45cb7352968a5c4d39672cfd8ddcfe2c824170850c2d4fce11a05c51fb11  ./symlists/2023-09.txt
c8d1cdf65242f5b4b47f37f639f7c98738507a31dae1506ff32fd7380c254f2c  ./symlists/2023-10.txt
1367824ce29a4d3e6acf7a9c490e9d36767613f3e3726ef33954f46c67418acb  ./symlists/2023-11.txt
a17a78e5a0a1037131ee7f8ec03ecbfe916ac24f73ce6ca0564166385adc1c32  ./symlists/2023-12.txt
5af64bab85eba0bfd27a99af5d933c8aaab8b5e7bba373630a7f2acafdb12a7a  ./symlists/2024-01.txt
20535bef4902b084c1fe409dd936bf562a94c4e2aba4c12bfa4d482365c040dc  ./symlists/2024-02.txt
ac093c0882854d9be14293eea29974bb0bca9af25c93aac65c817c8bcd9d90af  ./symlists/2024-03.txt
b9854e1d26d8b0da48213fcd064797afd121058a022f7b93c89adee694a0f98d  ./symlists/2024-04.txt
b6bceef4197e4d3f86daf5fa37653733306f0f29085126f92656fbb02df1b259  ./symlists/2024-05.txt
ec11343a9e3de32d468d2880f0d2fb41a1a2dbf6b30cde1229954c80ac50bf22  ./symlists/2024-06.txt
8190d8fa6e31f2741ec05939cf8511faa8271819b112f9892e0461fc0d6aafef  ./symlists/2024-07.txt
da43b175fe75a13a622295edfe01526ebfaa46f5a1d2ad34edc70c29c2431656  ./symlists/2024-08.txt
76e5e847e3caee875456358d1ee0393c80fa37ba3fc1dbffdf8cba2f66ef02e7  ./symlists/2024-09.txt
009c36c354e96ff49ae52f5bb4cbe2aa92929eeccf1606c40dc659518f1a880c  ./symlists/2024-10.txt
859dd3a356b6b90b1cba568ad57dd782a81c1bfdf73ef3d100956819a50f247f  ./symlists/2024-11.txt
f11b38a6c76148c2f8d8440bd109ed3ffab2e74847cf1b27cf715db77888ecfe  ./symlists/2024-12.txt
3b538e4655f9115b97ff73de7f3b4d54790f8038600aeadb0f945a20a89ac0a5  ./symlists/2025-01.txt
2f6f86bfa624a7fe24d7d04bf2da8ec6083f100d47e0c3c47304ad5e0e6f9c44  ./symlists/2025-02.txt
874965b99509af6bf2291b1840d17e6a92470081be9e5dc1a85dc2e84d08631c  ./symlists/2025-03.txt
1efc1ac0ced62f0e98c05f8555e3d65560677a338f78a7b71b41014b5932b411  ./symlists/2025-04.txt
66976a91bc03bedace9d642f18ef9f65ebaa33121e443a78b979202c5b95d63e  ./symlists/2025-05.txt
18d117deb5ff0dbd967af6e0fc9d00224a83f980ba6926dfe1467ee3eeb6fe63  ./symlists/2025-06.txt
8406cab9c3de1caa93b5b9df2e50183fd3becbd78b6713388614cf55ed50dc23  ./symlists/2025-07.txt
9a16d3329ff8ab4b2d09435e2bee21dd30d65333dc9787e8bd8822ffb1561dec  ./symlists/2025-08.txt
77040b3d7759ba703b5a339d05f8a0d5b008f3c7e237148291af5a7717febb7a  ./symlists/2025-09.txt
1d2c967ae2cac464f7f72934d9760ab9c1591fc00fe4592bd2eedfae32d7e090  ./symlists/2025-10.txt
11a3c757d9362da4003569b674e13116a11c0e82cace78c00287cf033ef8052d  ./symlists/2025-11.txt
94aec76c853290aaf844984458165e87736f345770023ace9482996fc9c23897  ./symlists/2025-12.txt
3663e78bd625e87b05d62fd74c8e757f2c4ce5161ea466d16c6085b522b25d99  ./symlists/2026-01.txt
586b686070ac6477902aace8cd42347d441b9849de2d1a4165c5cf4e80ac6fd1  ./symlists/2026-02.txt
31f70b3d8e4c79e3774063500c233da3dedc4e8a5def11ad10b7f45f9bc19d34  ./symlists/2026-03.txt
3db2d29b269d5a30de4f274272a8d8667f95e29801ee420f768cc0654178e809  ./symlists/2026-04.txt
1124bca0a83dff57f5235ee9e01b7223281eabcab4b1973772d3f316936f71c4  ./symlists/2026-05.txt
022c0e0f253d2eb48b7d85656c3db6d3dcd1f09cc3398fa816d3da231d93688f  ./symlists/2026-06.txt
b36da2a25505374f899ef962a52aa14a2d9fc6fd0adf0491a1c1108a6df4ed39  ./symlists/2026-07.txt
82ad819774f4fdf6225cd558e8249555fe060763f08a093b858c513fe38988a0  ./symlists/2026-08.txt
2bab6eadbcc033316f8a3ab7da719aaa12cabdb6bc231bae58eff24dd861b032  ./syms3.txt
```
