import re
MODEL = "/workspace/code/multi_asset/model/wide_harness.py"
TRAIN = "/workspace/code/multi_asset/train/train_wide_harness.py"

CLS = '''

class BookSpatialTowerEncoder(PanelEncoder):
    """W3 档位空间塔 (2026-08-09) —— 沿【档位轴】做小核卷积取剖面斜率/曲率, 不展平。

    数据布局(book5_hourly 实测): split..+9 = sh_m_L{0..4}{b,a}(均值),
    split+10..+19 = sh_s_L{0..4}{b,a}(标准差), split+20..21 = dep_lvl / dep_chg1h。
    重排为 (quant=2, level=5, side=2) -> Conv1d(in=quant*side=4, 沿 level 长度 5)。

    取自单资产 REG_arch 的【双路+门控】思路而非照搬: 那里是 LOB 路/成交流路,
    这里是【价量主干】/【深度剖面】。侧不对称让卷积核直接学(买卖并入通道维),
    依据是 book 法证实测 买侧变异 0.392 vs 卖侧 1.248 (3.2x) —— 单资产时代推迟到多资产、至今未做的设计。
    档位是有序空间轴: k=3 卷积的一阶/二阶响应 = 剖面斜率与曲率(挂单在哪一层堆积)。
    时间侧用因果 depthwise conv(书状态 AR(1h)=0.102 衰减极快, 不需深时序)。
    零初始化门控 => 初始逐位等于冠军。
    """

    def __init__(self, n_feat, split=32, n_levels=5, d=64, n_blocks=2, kernel_size=5,
                 sw=16, b_kernel=24, dropout=0.2):
        super().__init__()
        self.split = int(split)
        self.L = int(n_levels)
        self.n_grid = 4 * self.L
        self.n_scalar = n_feat - split - self.n_grid
        assert self.n_scalar >= 0, "channels short: n_feat=%d split=%d grid=%d" % (n_feat, split, self.n_grid)
        self.tower_a = SharedTemporalEncoder(self.split, d, n_blocks=n_blocks, n_heads=2,
                                             kernel_size=kernel_size, dropout=dropout)
        self.lv1 = nn.Conv1d(4, sw, 3, padding=1)
        self.lv2 = nn.Conv1d(sw, sw, 3, padding=1)
        self.b_proj = nn.Linear(2 * sw + max(self.n_scalar, 0), sw)
        self.b_conv = nn.Conv1d(sw, sw, b_kernel, groups=sw)
        self.b_out = nn.Linear(sw, d)
        self.b_kernel = int(b_kernel)
        self.gate = nn.Sequential(nn.Linear(2 * d, 32), nn.GELU(), nn.Linear(32, 1))
        self.alpha = nn.Parameter(torch.zeros(1))
        self.drop = nn.Dropout(dropout)
        self.d_out = d

    def forward(self, x, mask):
        B, N, W, C = x.shape
        ha = self.tower_a(x[..., :self.split], mask)
        g = x[..., self.split:self.split + self.n_grid]
        g = g.reshape(B * N * W, 2, self.L, 2).permute(0, 1, 3, 2).reshape(B * N * W, 4, self.L)
        g = torch.nn.functional.gelu(self.lv1(g))
        g = torch.nn.functional.gelu(self.lv2(g))
        g = torch.cat([g.mean(-1), g.amax(-1)], dim=-1)
        if self.n_scalar > 0:
            sc = x[..., self.split + self.n_grid:].reshape(B * N * W, self.n_scalar)
            g = torch.cat([g, sc], dim=-1)
        g = self.b_proj(g).reshape(B * N, W, -1).transpose(1, 2)
        g = torch.nn.functional.pad(g, (self.b_kernel - 1, 0))
        hb = torch.nn.functional.gelu(self.b_conv(g))[..., -1]
        hb = self.b_out(self.drop(hb)).reshape(B, N, -1)
        gt = torch.sigmoid(self.gate(torch.cat([ha, hb], dim=-1)))
        return ha + self.alpha * gt * hb
'''

s = open(MODEL).read()
if "class BookSpatialTowerEncoder" in s:
    print("model: 已存在")
else:
    anchor = "class WideFactorModel(nn.Module):"
    assert anchor in s
    open(MODEL, "w").write(s.replace(anchor, CLS.strip() + "\n\n\n" + anchor, 1))
    print("model: 空间塔已注入")

t = open(TRAIN).read()
if "book5t" in t:
    print("train: 已注册")
else:
    anchor2 = '    raise ValueError(f"unknown encoder arm'
    assert anchor2 in t, "encoder 注册锚点未找到"
    reg = ('    if name == "book5t":\n'
           '        return BookSpatialTowerEncoder(n_feat, split=32, n_levels=5, d=d,\n'
           '                                       n_blocks=n_blocks, kernel_size=kernel, dropout=dropout)\n')
    t = t.replace(anchor2, reg + anchor2, 1)
    m = re.search(r"from multi_asset\.model\.wide_harness import ([^\n]+)\n", t)
    assert m, "import 行未找到"
    if "BookSpatialTowerEncoder" not in m.group(1):
        t = t[:m.start(1)] + "BookSpatialTowerEncoder, " + m.group(1) + t[m.end(1):]
    open(TRAIN, "w").write(t)
    print("train: book5t 已注册 + import 已补")
