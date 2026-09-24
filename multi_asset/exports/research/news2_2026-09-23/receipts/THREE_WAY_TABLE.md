<!-- news2_three_way_table.py sha 0525e7c4110aec86; statistics imported from news_stats.py 7141ba42ab227b9f; cell scaled_rule_raw_UAFE -->

### 研究员 NEW / NEW_S / NC 同表(逐段收益、夏普、回撤)

> 只列事实, 不下结论。三列并排会自然诱发排序, 而排序只有在三列**产生方式相同**时才有意义, 所以每臂都带来源与口径, 且差异逐条列出而不是概括。

**区间总收益**（`total_return`,路径均值）

| 臂 | 2023H2 | 2024 | 2025 | pre2026 | 2026 |
|---|---|---|---|---|---|
| OLD | -15.85% | +18.29% | +2.23% | +1.77% | +130.57% |
| NEW_s42 | -4.96% | +41.01% | +65.58% | +121.91% | +138.27% |
| NEW_s2027 | -4.41% | +37.37% | +51.32% | +98.65% | +134.66% |
| NEW_S_s42 | -8.00% | +31.92% | +48.31% | +80.00% | +142.71% |
| NEW_S_s2027 | -5.62% | +28.58% | +33.38% | +61.87% | +134.00% |
| NC_s42 | -7.13% | +29.40% | +42.20% | +70.87% | +141.29% |
| NC_s2027 | -9.70% | +23.83% | +61.94% | +81.08% | +136.51% |

**夏普**（`sharpe`,路径均值）

| 臂 | 2023H2 | 2024 | 2025 | pre2026 | 2026 |
|---|---|---|---|---|---|
| OLD | -1.82 | +0.95 | +0.21 | +0.12 | +4.15 |
| NEW_s42 | -0.78 | +1.85 | +1.89 | +1.44 | +4.25 |
| NEW_s2027 | -0.89 | +1.73 | +1.65 | +1.28 | +4.25 |
| NEW_S_s42 | -1.20 | +1.46 | +1.60 | +1.11 | +4.27 |
| NEW_S_s2027 | -1.14 | +1.42 | +1.27 | +0.96 | +4.15 |
| NC_s42 | -1.06 | +1.39 | +1.40 | +1.02 | +4.30 |
| NC_s2027 | -1.57 | +1.20 | +1.90 | +1.14 | +4.23 |

**最大回撤(5m)**（`maxdd_5m`,路径均值）

| 臂 | 2023H2 | 2024 | 2025 | pre2026 | 2026 |
|---|---|---|---|---|---|
| OLD | -22.04% | -26.87% | -27.70% | -38.40% | -18.15% |
| NEW_s42 | -14.76% | -13.73% | -12.40% | -18.11% | -19.73% |
| NEW_s2027 | -15.02% | -12.94% | -12.06% | -17.61% | -19.43% |
| NEW_S_s42 | -14.17% | -18.47% | -12.63% | -23.01% | -21.81% |
| NEW_S_s2027 | -14.55% | -14.12% | -13.09% | -18.85% | -21.73% |
| NC_s42 | -14.17% | -19.91% | -12.54% | -23.10% | -21.21% |
| NC_s2027 | -15.16% | -18.07% | -12.38% | -22.53% | -20.98% |

**口径与装置是否相同**

| 臂 | runs 根 | 格 | 运行配置与 Stage-1 OLD 的叶级差异 |
|---|---|---|---|
| OLD | `ovn_2026-09-23` | `scaled_rule_raw_UAFE` | 0 处, 其中**影响设置的 0 处**(⇒ 设置一致, 可比); 其余为标签/谱系/目标:  |
| NEW_s42 | `ovn_2026-09-23` | `scaled_rule_raw_UAFE` | 68 处, 其中**影响设置的 0 处**(⇒ 设置一致, 可比); 其余为标签/谱系/目标: `config`, `new_lineage.adapter_receipt.path`, `new_lineage.adapter_receipt.sha256`, `new_lineage.arm`, `new_lineage.new_target_receipt.hold_contract` … |
| NEW_s2027 | `ovn_2026-09-23` | `scaled_rule_raw_UAFE` | 68 处, 其中**影响设置的 0 处**(⇒ 设置一致, 可比); 其余为标签/谱系/目标: `config`, `new_lineage.adapter_receipt.path`, `new_lineage.adapter_receipt.sha256`, `new_lineage.arm`, `new_lineage.new_target_receipt.hold_contract` … |
| NEW_S_s42 | `news_2026-09-23` | `scaled_rule_raw_UAFE` | 75 处, 其中**影响设置的 0 处**(⇒ 设置一致, 可比); 其余为标签/谱系/目标: `config`, `created_utc`, `new_lineage.adapter_receipt.path`, `new_lineage.adapter_receipt.sha256`, `new_lineage.arm` … |
| NEW_S_s2027 | `news_2026-09-23` | `scaled_rule_raw_UAFE` | 75 处, 其中**影响设置的 0 处**(⇒ 设置一致, 可比); 其余为标签/谱系/目标: `config`, `created_utc`, `new_lineage.adapter_receipt.path`, `new_lineage.adapter_receipt.sha256`, `new_lineage.arm` … |
| NC_s42 | `news2_2026-09-23` | `scaled_rule_raw_UAFE` | 75 处, 其中**影响设置的 0 处**(⇒ 设置一致, 可比); 其余为标签/谱系/目标: `config`, `created_utc`, `new_lineage.adapter_receipt.path`, `new_lineage.adapter_receipt.sha256`, `new_lineage.arm` … |
| NC_s2027 | `news2_2026-09-23` | `scaled_rule_raw_UAFE` | 75 处, 其中**影响设置的 0 处**(⇒ 设置一致, 可比); 其余为标签/谱系/目标: `config`, `created_utc`, `new_lineage.adapter_receipt.path`, `new_lineage.adapter_receipt.sha256`, `new_lineage.arm` … |
