> **创建:** 2026-07-14 | **Session:** 0C suppl-factor S2 seed check | **状态:** final | **作废条件:** panel 重建

# S2 G2 seed 判 (0C)

**判词: G2 PASS —— S2 增量 seed-robust。** 结合 5yr regime-robustness(五年全正),king-正交增量确认**真 + regime-robust + seed-robust**。

三 seed(3-fold 32ch,从 config 核对 lam_orth=0/xattn/H24/32ch,byte-一致 panel 1c8ad451,防 stale):

| seed | fold0/1/2 raw | raw mean | **king-正交增量** |
|--|--|--|--|
| 42 | .0524/.0696/.0639 | 0.0620 | **+0.0285** |
| 43 | .0559/.0875/.0758 | 0.0731 | **+0.0389** |
| 44 | .0556/.0590/.0805 | 0.0650 | **+0.0332** |

- raw IC CoV **7%**;**增量 CoV 12.7%,min +0.0285,三 seed 全正**。
- 全 32ch/H24,同 panel md5 1c8ad451。

**G2 PASS。** 增量非单 seed 幸运。→ 进四腿装配(见 book_assembly_4leg)。

---
**产物:** `s2_g2_seeds.json` · `score_s2_seeds.py`
