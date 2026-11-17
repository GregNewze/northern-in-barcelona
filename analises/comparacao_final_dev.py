"""comparacao_final_dev.py - v1.14 (sinais P1/P2) x LSTM hibrido, so nos 5 jogos de DESENVOLVIMENTO.

Por que existe: o LSTM foi aprovado pela regra dele (lstm_posse_idsse.py) DEPOIS de declararmos a
v1.14 como candidata. Escolher entre os dois pelos jogos reservados seria um 5o uso deles e uma
escolha feita depois de ver o resultado. Aqui a comparacao e nova, declarada antes de rodar, e NAO
usa os reservados (J03WR9, J03WOH): validacao cruzada deixando um jogo de fora (leave-one-game-out)
nos 5 jogos de desenvolvimento.

Em cada dobra, os dois metodos sao treinados nos 4 jogos restantes, do mesmo jeito dos scripts
aprovados, e testados no jogo de fora com a bola apagada (os mesmos 2 cenarios fixos do
lstm_posse_idsse.py):
  A  v1.14 no IDSSE: base (preenche 3 s, voto +-75, parada 3 s, histerese 1,5 s), continuacao, e
     cada sumico >= 5 s com bola no frame anterior decidido por P1/P2 (logistica nos 4 jogos)
  B  LSTM hibrido: base igual + continuacao; frames sem bola = classe do Bi-LSTM (treinado nos 4
     jogos); histerese 1,5 s
  (sem smart tagging nos dois: o IDSSE nao tem. No nosso jogo, os dois mantem set piece -> D.)

REGRA DE DECISAO (declarada antes de rodar):
  Troca a candidata para o LSTM hibrido (B) SO SE:
    1. a media de spellF1 de B nas 10 medidas (5 jogos x 2 cenarios) for >= a de A + 0,02, E
    2. B ganhar de A em pelo menos 4 dos 5 jogos (media dos 2 cenarios por jogo).
  Senao, fica a v1.14 (A). A nota do jogo da competicao nao e usada.

Uso (depois de analises/cache_idsse.py):
    python analises/comparacao_final_dev.py
"""

import os
import sys
import time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AQUI)
for _p in (AQUI, os.path.join(REPO, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import cache_idsse as C  # noqa: E402
import exporta_sinais_idsse as E  # noqa: E402
import lstm_posse_idsse as T  # noqa: E402
import posse_lstm as L  # noqa: E402
import sinais_jogadores_idsse as S  # noqa: E402
import v1_11 as V11  # noqa: E402

FPS = 25
SEED = 2028


def base_continua(codes, baseline, period):
    blocos = []
    for per in np.unique(period):
        idx = np.flatnonzero(period == per)
        blocos.append((per, idx[0], idx[-1]))
    gaps = V11.sumicos(codes, baseline.NOBODY, blocos)
    c = V11.preencher_sumicos(codes, gaps, baseline.NOBODY, 3.0)
    lab = baseline.smooth(c, 75)
    lab = V11.marcar_parada(lab, gaps, 3.0)
    lab = V11.histerese(lab, 1.5)
    return V11.decidir_sumicos(lab, [], int(2.0 * FPS), 1e9), gaps


def treinar_sinais(jogos, rng):
    dados = {m: S.coletar(m, rng) for m in jogos}
    X = np.vstack([dados[m][0] for m in jogos])
    y = np.concatenate([dados[m][1] for m in jogos]).astype(float)
    p1 = dict(zip(("mu", "sd", "w"), E.logistica_params(X, y)))
    X2 = np.vstack([np.column_stack([dados[m][2][:, :-1], np.where(dados[m][4] == 1, 1.0, -1.0)]) for m in jogos])
    y2 = (np.concatenate([dados[m][3] for m in jogos]) == 1).astype(float)
    p2 = dict(zip(("mu", "sd", "w"), E.logistica_params(X2, y2)))
    return p1, p2


def score(p, x):
    z = np.nan_to_num((np.asarray(x, float) - p["mu"]) / p["sd"])
    return float(np.dot(np.append(z, 1.0), p["w"]))


def metodo_A(g, ball, codes, baseline, p1, p2):
    lab, gaps = base_continua(codes, baseline, g["period"])
    gg = S.preparar(dict(ball=ball, home=g["home"], away=g["away"], dead=~np.isfinite(ball[:, 0]),
                         period=g["period"]))
    out = lab.copy()
    for a, b in gaps:
        if (b - a + 1) / FPS < 5.0 or a < 1 or not np.isfinite(ball[a - 1, 0]):
            continue
        s1, s2 = S.sinais(gg, a, b)
        s2.pop("_disputa", None)
        if score(p1, list(s1.values())) > 0:
            out[a:b + 1] = "D"
            continue
        antes = out[:a][np.isin(out[:a], ["H", "A"])]
        ult = 1.0 if (len(antes) and antes[-1] == "H") else -1.0
        out[a:b + 1] = "H" if score(p2, list(s2.values()) + [ult]) > 0 else "A"
    return out


def treinar_lstm(jogos, rng):
    import torch
    Xtr, Ytr = [], []
    for m in jogos:
        g = C.carregar(m)
        y = L.rotulos_idsse(g)
        for _ in range(T.SORTEIOS):
            X = L.sinais(L.simular_sumicos(g, rng), g["home"], g["away"], g["period"])
            for xs, ys in L.janelas(X, y):
                if len(xs) == L.SEQ:
                    Xtr.append(xs)
                    Ytr.append(ys)
        del g
    Xtr, Ytr = np.stack(Xtr), np.stack(Ytr)
    mu = Xtr.reshape(-1, Xtr.shape[-1]).mean(0)
    sd = Xtr.reshape(-1, Xtr.shape[-1]).std(0) + 1e-6
    Xt = torch.from_numpy(((Xtr - mu) / sd).astype(np.float32))
    Yt = torch.from_numpy(Ytr)
    modelo = L.construir_modelo(Xt.shape[-1])
    opt = torch.optim.Adam(modelo.parameters(), lr=2e-3)
    freq = np.bincount(Ytr.ravel(), minlength=3) / Ytr.size
    lossf = torch.nn.CrossEntropyLoss(weight=torch.tensor((1 / 3) / freq, dtype=torch.float32))
    for _ in range(T.EPOCAS):
        modelo.train()
        perm = torch.randperm(len(Xt))
        for i in range(0, len(perm), 32):
            j = perm[i:i + 32]
            opt.zero_grad()
            loss = lossf(modelo(Xt[j]).reshape(-1, 3), Yt[j].reshape(-1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
            opt.step()
    return modelo, mu, sd


def metodo_B(g, ball, codes, baseline, modelo, mu, sd):
    lab, _ = base_continua(codes, baseline, g["period"])
    P = L.prever(modelo, L.sinais(ball, g["home"], g["away"], g["period"]), mu, sd)
    ll = np.array(L.CLASSES)[P.argmax(1)]
    sem = codes == baseline.NOBODY
    out = lab.copy()
    out[sem] = ll[sem]
    return V11.histerese(out, 1.5)


def main():
    import torch
    torch.manual_seed(SEED)
    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True)
    V11.preparar_caminhos(os.path.join(REPO, "oficial"))
    import baseline
    import possession_metrics as pm

    def nota(gt, pred):
        return float(pm.evaluate(pm.label_codes(gt), pm.label_codes(pred), bootstrap_n=0)["spell_f1_mean"])

    t0 = time.time()
    res = {}
    for fora in C.DEV:
        treino = [m for m in C.DEV if m != fora]
        rng = np.random.default_rng(SEED)
        p1, p2 = treinar_sinais(treino, rng)
        modelo, mu, sd = treinar_lstm(treino, np.random.default_rng(SEED))
        g = C.carregar(fora)
        gt = np.array(L.CLASSES)[L.rotulos_idsse(g)]
        res[fora] = []
        for k, (pmorto, fv) in enumerate(T.CENARIOS):
            ball = L.simular_sumicos(g, np.random.default_rng(100 + k), p_morto=pmorto, frac_vivo=fv)
            codes = T.nearest(ball, g["home"], g["away"])
            a = nota(gt, metodo_A(g, ball, codes, baseline, p1, p2))
            b = nota(gt, metodo_B(g, ball, codes, baseline, modelo, mu, sd))
            res[fora].append((a, b))
            print(f"  fora={fora} cen{k + 1}: A (v1.14) {a:.4f} | B (LSTM hibrido) {b:.4f} | B-A {b - a:+.4f}"
                  f"  ({time.time() - t0:.0f} s)", flush=True)
        del g

    todos = [x for m in C.DEV for x in res[m]]
    ma, mb = np.mean([a for a, _ in todos]), np.mean([b for _, b in todos])
    ganha = sum(1 for m in C.DEV if np.mean([b for _, b in res[m]]) > np.mean([a for a, _ in res[m]]))
    print(f"\nmedia spellF1: A {ma:.4f} | B {mb:.4f} | B-A {mb - ma:+.4f} | B ganha em {ganha}/5 jogos")
    troca = (mb >= ma + 0.02) and ganha >= 4
    print(f"-> DECISAO pela regra declarada: {'TROCAR para o LSTM hibrido' if troca else 'MANTER a v1.14'}")


if __name__ == "__main__":
    main()
