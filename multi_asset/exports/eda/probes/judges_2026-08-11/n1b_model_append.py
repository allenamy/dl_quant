

# =========================================================================== #
# ARM-N1b: Multi-relational cross-asset attention (2026-07-15).
# King single-xattn path (base) + gated multi-relation delta. Relation edges =
# rolling-correlation buckets at K lookbacks (co-movement structure, causal <=t).
# ZERO-INIT gates: alpha (overall) + lambda_k (edge biases) start at 0, so at
# init h_out == base(h) == the king single-xattn (byte-identical start = built-in
# ablation). Shared Q/K/V/out across edges (edges differ only by the corr bias) ->
# ~17k incremental params. Wired via WideMultiRelModel (opt-in --multirel).
# =========================================================================== #
import math as _math


class MultiRelXAttn(nn.Module):
    def __init__(self, d, nhead=4, lookbacks=(24, 72, 168), ret_idx=20, dropout=0.2):
        super().__init__()
        self.base = CrossAssetAttnLayer(d, nhead=nhead, dropout=dropout)   # king path
        self.norm = nn.LayerNorm(d)
        self.Wq = nn.Linear(d, d, bias=False)
        self.Wk = nn.Linear(d, d, bias=False)
        self.Wv = nn.Linear(d, d, bias=False)
        self.Wout = nn.Linear(d, d)
        self.lam = nn.Parameter(torch.zeros(len(lookbacks)))    # lambda_k ZERO-INIT
        self.gate = nn.Linear(d, len(lookbacks))                # input-dependent edge mix
        self.alpha = nn.Parameter(torch.zeros(1))               # overall gate ZERO-INIT
        self.drop = nn.Dropout(dropout)
        self.lookbacks = tuple(lookbacks); self.ret_idx = int(ret_idx); self.d = d

    @staticmethod
    def _corr(r, key_pad):
        # r (B,N,L) -> masked pairwise Pearson corr (B,N,N) in [-1,1]
        rc = r - r.mean(-1, keepdim=True)
        rn = rc / rc.norm(dim=-1, keepdim=True).clamp_min(1e-6)
        C = torch.bmm(rn, rn.transpose(1, 2))
        return C.masked_fill(key_pad.unsqueeze(1), 0.0)         # invalid cols -> 0 bias

    def forward(self, h, x, key_pad):
        # h (B,N,d); x (B,N,W,C); key_pad (B,N) True=invalid
        h_base = self.base(h, key_pad)
        hn = self.norm(h)
        q, k, v = self.Wq(hn), self.Wk(hn), self.Wv(hn)
        ret = x[:, :, :, self.ret_idx]                          # (B,N,W) standardized 1h-ret window
        scale = 1.0 / _math.sqrt(self.d)
        deltas = []
        for e, L in enumerate(self.lookbacks):
            Bk = self._corr(ret[:, :, -L:], key_pad)            # (B,N,N)
            logits = torch.bmm(q, k.transpose(1, 2)) * scale + self.lam[e] * Bk
            logits = logits.masked_fill(key_pad.unsqueeze(1), float("-inf"))
            a = torch.softmax(logits, dim=-1)
            a = torch.nan_to_num(a, nan=0.0)                    # all-invalid query rows -> 0
            deltas.append(torch.bmm(a, v))                      # (B,N,d)
        valid = (~key_pad).float().unsqueeze(-1)                # (B,N,1)
        pooled = (hn * valid).sum(1) / valid.sum(1).clamp_min(1.0)   # (B,d)
        g = torch.softmax(self.gate(pooled), dim=-1)            # (B,K)
        mix = sum(g[:, e].view(-1, 1, 1) * deltas[e] for e in range(len(self.lookbacks)))
        delta = torch.nan_to_num(self.Wout(self.drop(mix)), nan=0.0)
        return h_base + self.alpha * delta


class WideMultiRelModel(nn.Module):
    """ARM-N1b: same contract as WideFactorModel (encoder -> cross-asset -> K factor heads,
    output factor_scores (B,N,K)) but the single xattn is replaced by MultiRelXAttn (king base
    path + zero-init gated multi-relation delta). ret_idx = index of the 1h-return channel used
    for the rolling-correlation relation biases."""
    def __init__(self, encoder: PanelEncoder, n_factor_heads=6, lookbacks=(24, 72, 168),
                 ret_idx=20, dropout=0.2):
        super().__init__()
        self.encoder = encoder
        d = encoder.d_out
        self.multirel = MultiRelXAttn(d, nhead=4, lookbacks=lookbacks, ret_idx=ret_idx, dropout=dropout)
        self.factor_heads = nn.ModuleList([
            nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Dropout(dropout), nn.Linear(d, 1))
            for _ in range(n_factor_heads)])

    def forward(self, x, mask):
        h = self.encoder(x, mask)                    # (B,N,d)
        key_pad = mask < 0.5                          # (B,N) True where invalid
        h = self.multirel(h, x, key_pad)
        scores = torch.cat([head(h) for head in self.factor_heads], dim=-1)   # (B,N,K)
        return {"factor_scores": scores}
