"""posse_lstm.py - Bi-LSTM que diz H/A/D a partir dos JOGADORES (e da bola, quando visivel).

Inspiracao: Kim et al., "Ball Trajectory Inference from Multi-Agent Sports Contexts Using Set
Transformer and Hierarchical Bi-LSTM" (KDD 2023): a posse e a bola podem ser inferidas pelo
movimento coletivo dos jogadores. Aqui a saida e direto a classe do desafio (mandante, visitante,
bola morta), a 5 Hz.

Treino SO com jogos abertos do IDSSE (Bundesliga). O jogo da competicao nunca e usado para
treinar nem para escolher nada: o modelo so e aplicado nele no fim.

Sinais por frame (iguais em qualquer jogo, invariantes a ordem dos jogadores, campo orientado
para o mandante atacar em +x):
  bola: visivel?, x, y, velocidade, tempo desde a ultima vista, ultima posicao conhecida
  por time: centroide, espalhamento, intensidade relativa, sprint, jogadores a < 5/10 m da bola
            (atual ou ultima), menor distancia a bola, sincronia, velocidade do centroide
  geral: time do jogador mais perto da bola visivel, jogador parado na linha, jogadores nas areas
"""

import numpy as np

FPS = 25
PASSO = 5            # 25 fps -> 5 Hz
SEQ = 300            # 60 s por sequencia
CLASSES = ("H", "A", "D")


def _vel(P, k=5):
    v = np.full(P.shape, np.nan, np.float32)
    v[k:] = (P[k:] - P[:-k]) * (FPS / k)
    return v


def sinais(ball, home, away, period):
    """(n, F) float32. ball (n,2) com NaN quando sumida; home/away (n, k, 2) em metros."""
    n = len(ball)
    # orientacao: mandante ataca em +x em cada tempo
    sent = np.ones(n, np.float32)
    for per in np.unique(period):
        m = period == per
        if np.nanmean(home[m][..., 0]) > 52.5:
            sent[m] = -1.0
    def ori(P):
        Q = P.copy()
        flip = sent < 0
        Q[flip, ..., 0] = 105.0 - Q[flip, ..., 0]
        Q[flip, ..., 1] = 68.0 - Q[flip, ..., 1]
        return Q
    b, H, A = ori(ball[:, None, :])[:, 0], ori(home), ori(away)
    vis = np.isfinite(b[:, 0])
    # ultima posicao conhecida e tempo desde entao
    idx = np.where(vis, np.arange(n), -1)
    idx = np.maximum.accumulate(idx)
    tem = idx >= 0
    ult = np.where(tem[:, None], b[np.maximum(idx, 0)], np.array([52.5, 34.0], np.float32))
    desde = np.where(tem, (np.arange(n) - idx) / FPS, 60.0).clip(0, 60)
    bv = np.linalg.norm(np.nan_to_num(_vel(b[:, None, :])[:, 0]), axis=1).clip(0, 40)
    bv[~vis] = 0
    vH, vA = np.linalg.norm(_vel(H), axis=2), np.linalg.norm(_vel(A), axis=2)
    vH[vH > 12] = np.nan
    vA[vA > 12] = np.nan
    with np.errstate(all="ignore"):
        ref = np.nanmedian(np.concatenate([vH, vA], 1)[vis])
    ref = ref if np.isfinite(ref) and ref > 0 else 1.0
    alvo = np.where(vis[:, None], np.nan_to_num(b), ult)
    cols = [vis.astype(np.float32), np.nan_to_num(b[:, 0]) / 105, np.nan_to_num(b[:, 1]) / 68,
            bv / 40, desde / 60, ult[:, 0] / 105, ult[:, 1] / 68]
    dmin = {}
    with np.errstate(all="ignore"):
        for T, v in ((H, vH), (A, vA)):
            c = np.nanmean(T, axis=1)
            esp = np.nanmean(np.linalg.norm(T - c[:, None], axis=2), axis=1)
            d = np.linalg.norm(T - alvo[:, None], axis=2)
            dm = np.nanmin(d, axis=1)
            dmin[id(T)] = dm
            u = _vel(T)
            un = u / np.linalg.norm(u, axis=2, keepdims=True)
            pol = np.linalg.norm(np.nanmean(un, axis=1), axis=1)
            frente = np.nanmean(un[..., 0], axis=1)
            cv = np.zeros(n, np.float32)
            cv[1:] = np.diff(c[:, 0]) * FPS
            cols += [c[:, 0] / 105, c[:, 1] / 68, esp / 30, np.nanmedian(v, 1) / ref,
                     np.nanmean(v > 1.8 * ref, 1), np.nansum(d < 5, 1) / 5, np.nansum(d < 10, 1) / 8,
                     np.clip(dm, 0, 40) / 40, pol * np.sign(np.nan_to_num(frente)), np.clip(cv, -10, 10) / 10]
        allp = np.concatenate([H, A], 1)
        x, y = allp[..., 0], allp[..., 1]
        borda = np.minimum.reduce([y, 68 - y, x, 105 - x])
        vall = np.concatenate([vH, vA], 1)
        na_linha = np.any((borda < 2) & (vall < 0.5 * ref), axis=1)
        area = np.nansum(((x < 16.5) | (x > 88.5)) & (y > 13.85) & (y < 54.15), 1) / 10
        dh, da = dmin[id(H)], dmin[id(A)]
        perto = np.where(vis, np.sign(np.nan_to_num(da, nan=99) - np.nan_to_num(dh, nan=99)), 0)
    cols += [perto, na_linha.astype(np.float32), area]
    X = np.nan_to_num(np.column_stack(cols).astype(np.float32))
    return X


def rotulos_idsse(g):
    y = np.full(len(g["dead"]), 2, np.int64)
    y[(~g["dead"]) & (g["owner"] == 1)] = 0
    y[(~g["dead"]) & (g["owner"] == 2)] = 1
    return y


def simular_sumicos(g, rng, p_morto=None, frac_vivo=None, faixas=None):
    """Apaga a bola do IDSSE como o tracker do nosso jogo apaga: quase toda bola morta some,
    mais trechos com o jogo rolando. Parametros sorteados por chamada (aleatorizacao de dominio)."""
    ball = g["ball"].copy()
    n = len(ball)
    p_morto = rng.uniform(0.6, 1.0) if p_morto is None else p_morto
    frac_vivo = rng.uniform(0.05, 0.25) if frac_vivo is None else frac_vivo
    faixas = faixas or [((5, 8), 38), ((8, 12), 31), ((12, 20), 19), ((20, 60), 44)]
    dead = g["dead"]
    m = np.concatenate(([False], dead, [False])).astype(np.int8)
    d = np.diff(m)
    for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1):
        if rng.random() < p_morto:
            a2 = max(0, a - int(rng.uniform(0, 2) * FPS))
            b2 = min(n - 1, b + int(rng.uniform(0, 1) * FPS))
            ball[a2:b2 + 1] = np.nan
    vivo = int((~dead).sum() * frac_vivo)
    pesos = np.array([w for _, w in faixas], float)
    pesos /= pesos.sum()
    apagado = 0
    while apagado < vivo:
        lo, hi = faixas[rng.choice(len(faixas), p=pesos)][0]
        L = int(rng.uniform(lo, hi) * FPS)
        a = int(rng.integers(0, n - L))
        ball[a:a + L] = np.nan
        apagado += L
    return ball


def construir_modelo(F, hid=64):
    import torch.nn as nn

    class Rede(nn.Module):
        def __init__(self):
            super().__init__()
            self.ent = nn.Sequential(nn.Linear(F, hid), nn.ReLU())
            self.lstm = nn.LSTM(hid, hid, num_layers=2, batch_first=True, bidirectional=True, dropout=0.2)
            self.sai = nn.Linear(2 * hid, len(CLASSES))

        def forward(self, x):
            h, _ = self.lstm(self.ent(x))
            return self.sai(h)
    return Rede()


def janelas(X, y=None, seq=SEQ, passo_seq=SEQ // 2):
    Xs = X[::PASSO]
    ys = y[::PASSO] if y is not None else None
    out = []
    for s in range(0, max(1, len(Xs) - seq + 1), passo_seq):
        out.append((Xs[s:s + seq], ys[s:s + seq] if ys is not None else None))
    return out


def prever(modelo, X, mu, sd):
    """Probabilidades (n, 3) a 25 fps: janelas de 60 s com sobreposicao, media das previsoes."""
    import torch
    Xs = (X[::PASSO] - mu) / sd
    m = len(Xs)
    soma = np.zeros((m, 3), np.float64)
    cont = np.zeros(m, np.float64)
    modelo.eval()
    with torch.no_grad():
        for s in list(range(0, max(1, m - SEQ + 1), SEQ // 4)) + [max(0, m - SEQ)]:
            x = torch.from_numpy(Xs[s:s + SEQ][None].astype(np.float32))
            p = torch.softmax(modelo(x), -1)[0].numpy()
            soma[s:s + len(p)] += p
            cont[s:s + len(p)] += 1
    P = soma / np.maximum(cont, 1)[:, None]
    return np.repeat(P, PASSO, axis=0)[:len(X)]
