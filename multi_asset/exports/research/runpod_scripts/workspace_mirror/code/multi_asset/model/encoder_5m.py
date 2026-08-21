"""A1: Conformer5m — 在役 conformer(1h 长程流)原样 + film2 定版 5m 分支(短程流) + 零初始化门控.
受据: RESULT_dl_ceiling_batch1-4 §3-bis(film2 双种子 0.0627, 树对照+33%). gate=0 ⇒ 输出与冠军逐位相同.
归一化用固定常量(通道本身有 clip 界, 首层后 GroupNorm 吸收标度) ⇒ 零折内拟合零泄漏.
"""
import io, zipfile
import numpy as np
import torch
import torch.nn as nn
import torch.utils.checkpoint as _ckpt


def _zload(path):
    z = zipfile.ZipFile(path)
    out = {}
    for n in z.namelist():
        with z.open(n) as f:
            out[n[:-4] if n.endswith('.npy') else n] = np.lib.format.read_array(io.BytesIO(f.read()), allow_pickle=True)
    return out


_MU = torch.tensor([0.0, 0.004, 0.5, 10.0, 5.0, 5.0, 0.5])
_SD = torch.tensor([0.004, 0.006, 0.35, 4.0, 2.5, 2.5, 0.15])


class Seq5mBranch(nn.Module):
    def __init__(self, d_out=64, ch=96, cin=8):
        super().__init__()
        L = []
        c = cin
        for d in (1, 2, 4, 8, 16, 32, 64, 128):
            L += [nn.Conv1d(c, ch, 3, dilation=d), nn.GELU(), nn.GroupNorm(8, ch)]
            c = ch
        self.net = nn.ModuleList(L)
        self.films = nn.ModuleList([nn.Sequential(nn.Linear(8, 32), nn.GELU(), nn.Linear(32, 2*ch)) for _ in range(8)])
        self.apq = nn.Linear(ch, 1)
        self.proj = nn.Linear(2*ch, d_out)
        self.ch = ch

    def forward(self, x, cx):
        h = x.transpose(1, 2)
        nb = 0
        for l in self.net:
            if isinstance(l, nn.Conv1d):
                h = nn.functional.pad(h, (l.dilation[0]*2, 0)); h = l(h)
            else:
                h = l(h)
                if isinstance(l, nn.GroupNorm):
                    fb = self.films[nb](cx); nb += 1
                    h = h*(1 + 0.1*fb[:, :self.ch].unsqueeze(-1)) + 0.1*fb[:, self.ch:].unsqueeze(-1)
        hs = h[:, :, -288:]
        w = torch.softmax(self.apq(hs.transpose(1, 2)).squeeze(-1), -1)
        z = torch.cat([(hs*w.unsqueeze(1)).sum(-1), h[:, :, -1]], -1)
        return self.proj(z)


class Conformer5m(nn.Module):
    wants_rows = True

    def __init__(self, base, seq5m_path, panel_ts_ms, panel_symbols, d=64, chunk=2048, fusion='add'):
        super().__init__()
        self.base = base
        self.d_out = getattr(base, 'd_out', d)
        self.branch = Seq5mBranch(d_out=d)
        self.gate = nn.Parameter(torch.zeros(1))
        self.aux_head = nn.Linear(d, 1)
        self.last_aux = None
        self.fusion = fusion
        if fusion in ('film', 'filmv'):
            self.f_gamma = nn.Linear(d, d)
            self.f_beta = nn.Linear(d, d)
            if fusion == 'filmv':
                self.gate = nn.Parameter(torch.zeros(d))
        elif fusion == 'inter':
            self.f_U = nn.Linear(d, d)
            self.f_V = nn.Linear(d, d)
        elif fusion not in ('add',):
            raise ValueError(f'unknown fusion {fusion}')
        Z = _zload(seq5m_path)
        cts = Z['ts'].astype(np.int64)
        csyms = [str(s) for s in Z['symbols']]
        order = [csyms.index(str(s)) for s in panel_symbols]
        cd = np.ascontiguousarray(Z['data'][:, order, :])
        self.register_buffer('CD', torch.from_numpy(cd), persistent=False)
        wall = np.asarray(panel_ts_ms).astype(np.int64)//1000 + 3600
        re = (wall - int(cts[0]))//300
        self.register_buffer('row_end', torch.from_numpy(re.astype(np.int64)), persistent=False)
        self.register_buffer('nmu', _MU.clone(), persistent=False)
        self.register_buffer('nsd', _SD.clone(), persistent=False)
        self.W5 = 576
        self.CW = 2016
        self.btc = [str(s) for s in panel_symbols].index('BTCUSDT')
        self.chunk = chunk

    def _win(self, e):
        blk = self.CD[e-self.W5:e].float()
        mk = torch.isfinite(blk)
        xp = torch.where(mk, blk, torch.zeros((), device=blk.device))
        xp = torch.clamp((xp - self.nmu)/self.nsd, -8, 8)
        return torch.cat([xp, mk.all(-1, keepdim=True).float()], -1).transpose(0, 1)

    def _ctx(self, e):
        s0 = max(0, e - self.CW)
        blk = torch.nan_to_num(self.CD[s0:e].float())
        r = blk[:, :, 0]
        vol7 = r.std(0)
        btcv = r[:, self.btc].std()
        disp = r[-self.W5:].sum(0).std()
        breadth = (r[-288:].sum(0) > 0).float().mean()
        absr = r.abs().mean()
        volpct = vol7.argsort().argsort().float()/max(r.shape[1]-1, 1) - 0.5
        qz = blk[-288:, :, 3].mean(0)
        qz = (qz - qz.mean())/(qz.std()+1e-6)
        tbf = blk[-288:, :, 6].mean(0) - 0.5
        n = r.shape[1]
        mkt = torch.stack([btcv.expand(n), disp.expand(n), breadth.expand(n), absr.expand(n)], -1)*100
        own = torch.stack([torch.log1p(100*vol7), volpct, qz, tbf], -1)
        return torch.cat([mkt, own], -1)

    def forward(self, x, mask, rows=None):
        h = self.base(x, mask)
        assert rows is not None, 'conformer5m: rows 必传(静默回退=缺陷家族)'
        B, N, d = h.shape
        T5 = self.CD.shape[0]
        xs, cs, idx = [], [], []
        for bi in range(B):
            e = int(self.row_end[int(rows[bi])])
            if e < self.W5 or e > T5:
                continue
            xs.append(self._win(e)); cs.append(self._ctx(e)); idx.append(bi)
        e5 = torch.zeros(B, N, d, device=h.device, dtype=h.dtype)
        if xs:
            X = torch.cat(xs); C = torch.cat(cs)
            outs = []
            for c0 in range(0, X.shape[0], self.chunk):
                xc, cc = X[c0:c0+self.chunk], C[c0:c0+self.chunk]
                if self.training:
                    outs.append(_ckpt.checkpoint(self.branch, xc, cc, use_reentrant=False))
                else:
                    outs.append(self.branch(xc, cc))
            O = torch.cat(outs).view(len(idx), N, d)
            for k, bi in enumerate(idx):
                e5[bi] = O[k]
        self.last_aux = self.aux_head(e5).squeeze(-1)
        if self.fusion in ('film', 'filmv'):
            return h*(1 + self.gate*self.f_gamma(e5)) + self.gate*self.f_beta(e5)
        if self.fusion == 'inter':
            return h + self.gate*(e5 + self.f_U(h*self.f_V(e5)))
        return h + self.gate*e5
