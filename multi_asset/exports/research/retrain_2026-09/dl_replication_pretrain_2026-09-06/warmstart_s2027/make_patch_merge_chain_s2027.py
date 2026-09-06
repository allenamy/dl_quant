"""make_patch_merge_chain_s2027.py — PREREG_dl_warmstart_replication_2026-09-06: merge_chain.py 的种子 2027 版本。
改动只在【种子相关处】: SEED 42→2027; 首折初始权重 INIT_PT 的年折 .pt 从 s42→s2027; 有限掩码参照从 CONST(s42) 改为
mE1 s2027 拼接文件(同种子的对照, 与 §5 早停复验 merge_mwf3s.py 同法)。其余逐字节不变(折规则/断言/拼行/输出命名按 SEED)。"""
import sys, hashlib
src, dst = sys.argv[1], sys.argv[2]
S = open(src, encoding="utf-8").read()
subs = [
 ('B = "/workspace/review_scratch/allweather_trackB"; SEED = 42',
  'B = "/workspace/review_scratch/allweather_trackB"; SEED = 2027'),
 ('INIT_PT = f"{B}/mE1_constseed/yearly_out/models/f10_V2MAIN_YS_s42_2025.pt"',
  'INIT_PT = f"{B}/mE1_constseed/yearly_out/models/f10_V2MAIN_YS_s2027_2025.pt"'),
 ('SC = np.load(f"{B}/mE1_constseed/preds/f10_V2MAIN_mE1c_s42.npy")',
  'SC = np.load(f"{B}/mwf_s2027/preds/f10_V2MAIN_mE1_s2027.npy")'),
]
for old, new in subs:
    assert S.count(old) == 1, (S.count(old), old[:70])
    S = S.replace(old, new)
open(dst, "w", encoding="utf-8").write(S)
print("wrote", dst, hashlib.sha256(S.encode("utf-8")).hexdigest()[:16], "| 替换", len(subs), "处")
