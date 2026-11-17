"""exporta_sinais_idsse.py - grava os pesos dos classificadores P1/P2 aprovados (src/modelo_sinais.json).

Reproduz EXATAMENTE o treino de analises/sinais_jogadores_idsse.py (mesma semente, mesmos
sorteios, mesma logistica, so os 5 jogos de desenvolvimento do IDSSE) e salva media, desvio e
pesos, para o pipeline aplicar no nosso jogo sem precisar do IDSSE.

Confere no fim: as previsoes com os pesos exportados sao identicas as da funcao original.

Uso (depois de analises/cache_idsse.py):
    python analises/exporta_sinais_idsse.py
"""

import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import sinais_jogadores_idsse as S  # noqa: E402

SAIDA = os.path.join(os.path.dirname(AQUI), "src", "modelo_sinais.json")


def logistica_params(X, y, it=3000, lr=0.1):
    """Mesma conta de S.logistica, mas devolve os parametros."""
    mu, sd = np.nanmean(X, 0), np.nanstd(X, 0) + 1e-9
    Z = np.nan_to_num((X - mu) / sd)
    w = np.zeros(Z.shape[1] + 1)
    Zb = np.hstack([Z, np.ones((len(Z), 1))])
    for _ in range(it):
        p = 1 / (1 + np.exp(-Zb @ w))
        w -= lr * Zb.T @ (p - y) / len(y)
    return mu, sd, w


def main():
    rng = np.random.default_rng(S.SEED)
    dados = {m: S.coletar(m, rng) for m in S.C.DEV}   # DEV vem primeiro no script original
    nomes1, nomes2 = dados[S.C.DEV[0]][5], dados[S.C.DEV[0]][6]
    X = np.vstack([dados[m][0] for m in S.C.DEV])
    y = np.concatenate([dados[m][1] for m in S.C.DEV]).astype(float)
    mu1, sd1, w1 = logistica_params(X, y)
    f = S.logistica(X, y)
    assert np.allclose(f(X), np.hstack([np.nan_to_num((X - mu1) / sd1), np.ones((len(X), 1))]) @ w1)

    P2 = [dados[m][2][:, :-1] for m in S.C.DEV]          # tira a flag de disputa
    X2 = np.vstack([np.column_stack([p, np.where(dados[m][4] == 1, 1.0, -1.0)])
                    for p, m in zip(P2, S.C.DEV)])
    y2 = (np.concatenate([dados[m][3] for m in S.C.DEV]) == 1).astype(float)
    mu2, sd2, w2 = logistica_params(X2, y2)
    f2 = S.logistica(X2, y2)
    assert np.allclose(f2(X2), np.hstack([np.nan_to_num((X2 - mu2) / sd2), np.ones((len(X2), 1))]) @ w2)

    out = dict(
        origem="IDSSE dev " + ",".join(S.C.DEV) + " (analises/sinais_jogadores_idsse.py, seed %d)" % S.SEED,
        p1=dict(sinais=nomes1, mu=mu1.tolist(), sd=sd1.tolist(), w=w1.tolist(),
                leitura="score > 0 (prob > 0,5) = PARADO"),
        p2=dict(sinais=nomes2 + ["ultimo_time"], mu=mu2.tolist(), sd=sd2.tolist(), w=w2.tolist(),
                leitura="score > 0 = MANDANTE; ultimo_time = +1 mandante, -1 visitante"),
    )
    with open(SAIDA, "w") as fh:
        json.dump(out, fh, indent=1)
    print("salvo src/modelo_sinais.json | P1 %d sinais, P2 %d sinais | %d e %d exemplos"
          % (len(nomes1), len(nomes2) + 1, len(X), len(X2)))
    for nome, wi in zip(nomes1 + ["(bias)"], w1):
        print("  P1 %-14s %+.3f" % (nome, wi))
    for nome, wi in zip(nomes2 + ["ultimo_time", "(bias)"], w2):
        print("  P2 %-14s %+.3f" % (nome, wi))


if __name__ == "__main__":
    main()
