p = '/Users/haosiyu/Desktop/quant_research/multi_asset/exports/eda/RESULT_channel_cutoff_audit_2026-08-03.md'
s = open(p, encoding='utf-8').read()

OLD_VERIFY = ('**数值验证(不靠文档):** 对长度 40 的数组放一个单位脉冲在 t=20, '
              '`np.convolve(x, ones(24), "same")` 的非零输出落在 **t = 9…32** ⇒ '
              '**输出 `out[t]` 用到输入 `x[t−11 … t+12]`。**')

NEW_VERIFY = '''**数值验证(不靠文档):** 构造卷积矩阵 `M[:, i] = convolve(e_i, ones(24), "same")` — 第 i 列是输入 i 的贡献, 于是 **`M[t]` 的非零列就是 `out[t]` 实际用到的输入下标**。实测:
```
out[t] 用到 input[t−12 … t+11]     共 24 项, 其中【未来项 11 个】
```

> **★ 更正(team-lead 独立复现时指出, 我采纳): 本文初版写作 `x[t−11 … t+12]` /「12 小时前视」, 方向读反了。** 我当时量的是「一个单位脉冲影响哪些输出」(脉冲在 20 → 输出 9…32) —— **那是支撑区间的镜像, 不是 `out[t]` 的支撑区间。** 正确读法是上面的卷积矩阵**按行**取。**结论不变(仍是前视), 但未来项是 11 个不是 12 个。**
> **记一笔: 我用一个【正确的数值实验】得出了一个【方向反了的读数】—— 实验没错, 解读错了。这类错误不会被"把它重跑一遍"发现, 只会被"换一种读法"发现。**'''

subs = [
 ('第 32 个 `betaadj_ret24` 含 12 小时前视', '第 32 个 `betaadj_ret24` 含 **11 小时**前视'),
 ('| **★ t+12h(前视 12 小时)** |', '| **★ t+11h(前视 11 小时)** |'),
 (OLD_VERIFY, NEW_VERIFY),
 ('**`mkt24[t]` 含 t 之后 11–12 小时的市场收益', '**`mkt24[t]` 含 t 之后 1…11 小时的市场收益'),
 ('**信号行的 `mkt24` 只累加了窗口的过去一半, 未来那 11–12 项被当作 0。**',
  '**信号行的 `mkt24` 只累加了窗口的过去 13 项(t−12…t), 未来那 11 项被当作 0。**'),
]
for a, b in subs:
    n = s.count(a)
    print(('OK   %d x  ' % n) + repr(a[:40]) if n >= 1 else '*** MISS ***  ' + repr(a[:40]))
    s = s.replace(a, b)
open(p, 'w', encoding='utf-8').write(s)
print('written')
