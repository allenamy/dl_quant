# 轴 B 席位规则: 从 judge.json 逐年水平打印实盘口径表(每 gross 年化 %, 2×NAV %, Sharpe, maxDD % gross), 换算链脚本化(E-0904-G)
import json,sys
j=json.load(open('axisB/judge.json'))
L=j['levels']; W=['2024','2025','2026<=08-10','2026->08-30','2024->26','2025->26']
print('单位链: mean[bps/锚, 每NAV] / gross[×NAV] = bps/锚 每gross; ×2190 锚/年 /100 = %/gross/年; ×2 = 2×gross 下 %NAV/年; maxDD[bps 每NAV]/gross/100 = % gross')
for cal in ['log','prod']:
  for seed in ['s42','s2027']:
    print(f'\n== 口径 {cal} | king rollm(K1) | F10 {seed} | 单元 = %/gross/年 (2×NAV %) S=Sharpe DD=% gross ==')
    print('| 规则 | '+' | '.join(W)+' |'); print('|---'*(len(W)+1)+'|')
    for r in ['R0','R1','R2','R3','R4','R5']:
      k=f'{cal}/rollm/{seed}/{r}'; row=[]
      for w in W:
        v=L[k][w]; pg=v['mean']/v['gross']*2190/100; dd=v['maxDD']/v['gross']/100
        row.append(f"{pg:+.1f}% ({2*pg:+.1f}%) S{v['sharpe']:+.2f} DD{dd:.1f}%")
      print(f'| {r} | '+' | '.join(row)+' |')
print('\nAXISB_UNITS_DONE')
