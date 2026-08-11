> **创建:** 2026-07-12 | **Session:** 0C independent scorer/auditor | **状态:** final | **作废条件:** aux+xattn combo 实跑落地(用真实增量替换预检先验)

# GPU 队列预检 — 全家 pred-corr vs xattn 新王 (0C)

**结论: aux-MTL vs xattn 逐 fold 横截面 rank corr = 0.277(<< 0.6)→ 预注册读数 = QUEUE "lam_orth=0 + xattn + aux-MTL" combo(HIGH EV)。** 方法同 xattn↔QIM 预检(那次 0.42 预言了 +0.028,方法有一次确认命中)。全家同 panel md5=39f5cc4e。

## 全家对 xattn 新王的横截面 rank corr(逐 fold + 均值)

| arm | per-fold | **mean corr** | 队列读数 |
|--|--|--|--|
| lamorth0 | [.491,.689,.441] | **0.54** | xattn 的 base(已在书内) |
| QIM | [.373,.563,.564] | **0.50** | blend 已被 xattn supersede |
| **aux-MTL** | [.173,.335,.323] | **0.277** | ★ **HIGH-EV → 排 aux+xattn combo** |
| conformer_ref | [.187,.364,.150] | 0.234 | reference/weak |
| pred_smooth | [.136,.115,.218] | 0.156 | 已 REJECT |

## 判词

- **aux-MTL 0.277 << 0.6** → aux supervision(1h/24h 辅助头正则 shared trunk)产出与 xattn 王实质不同的下注 → **独立内容先验成立,排 combo(高 EV)。**
- **★ caveat(诚实):** 现有对照臂(aux-MTL/conformer_ref/pred_smooth)都是**带惩罚**(lam_orth=1.0),其对无惩罚 xattn 王的低 corr **部分反映惩罚打散,非纯信号正交** —— 故 0.277 是**正-但-不确定先验**(真实相似度的下界)。真 EV 靠 combo 实跑(aux 头正则 xattn 用的同一 shared trunk,机制是"aux 监督是否改善 xattn 模型",非预测 blend)。同 caveat 曾用于 xattn↔QIM 预检(0.42),那次 +0.028 命中 —— 方法有一次确认。
- **QIM/lamorth0 对 xattn 都只 ~0.5** = 即便强臂之间也有大量 diversity;但 xattn 已 dominant,blend 反稀释(见加冕判),故不走 blend 路。

## 队列建议

1. **NEXT(高 EV):** `lam_orth=0 + xattn + aux-MTL` combo。若胜 clean-xattn 0.0835 → aux 是第三 lever。
2. **其下:** ARM-MIX / FinPFN(新范式,与全家 corr 未知,探索价值)。
3. **不重排:** pred-smooth / conformer_ref(弱 + 已测)。

---
**产物:** `queue_precheck.json` · `queue_precheck.py`(可复算)


---

## 确认结局 (0C, 2026-07-12): aux+xattn combo = REJECT (预注册干净 FAIL)

我从 fold scores 重算 honest ensemble(非信 JSON)+ panel byte-check(39f5cc4e PASS):
- 王(lam0+xattn): [0.0718/0.0988/0.1138] mean **0.0948**
- aux combo: [0.0644/0.0801/0.1029] mean **0.0825** —— Δ −0.0123,**三 fold 全劣**,低于三 seed 下沿 0.0910 → **干净 FAIL,REJECT**。aux-MTL 监督在 clean+xattn 基线不但无增量还**伤**。

**★ 方法论教训(值得存档):** pred-corr 预检的**预言力是条件性的**。
- **xattn 预检成功**(penalized-xattn↔QIM 0.42 → 预言 +0.028,命中):因预检臂**共享被测 lever**(去惩罚同一 attention 机制)→ 低 corr = 惩罚打散但真实的机制多样性,去惩罚即解锁。
- **aux 预检失败**(penalized-aux↔xattn 0.277 → 预言独立,实测 −0.0123):因 aux-MTL 是**不同机制**(训练正则器非因子)**且带惩罚** → 低 corr 是**惩罚打散的伪多样性**,非独立信号。
- **规则:** pred-corr 预检只在预检臂是**同代干净臂**或**同机制去惩罚**时是可靠先验;对**不同机制的带惩罚旧臂**,低 corr 不可靠(可能伪多样性)。我预检时的 caveat("正-但-不确定,部分惩罚打散")**正确,aux FAIL 确认之**。

**队列更新:** aux+xattn REJECTED,不重排 aux combos。NEXT = xattn2 深度臂(跑中)> ARM-MIX/FinPFN(需 build)。
