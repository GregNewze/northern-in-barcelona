"""lstm_posse_idsse.py - treina o Bi-LSTM (src/posse_lstm.py) no IDSSE e compara com as regras.

So jogos abertos do IDSSE. O jogo da competicao nao aparece aqui.

Desenho:
  - TREINO: os 5 jogos de desenvolvimento, cada um com 6 sorteios de sumicos simulados
    (simular_sumicos: quase toda bola morta some + trechos de jogo rolando, como no nosso
    tracker; intensidade sorteada a cada vez para o modelo nao depender de um valor so).
  - TESTE: os 2 jogos reservados, com dois cenarios FIXOS de sumico:
        cenario 1: 85% das bolas mortas somem + 15% do jogo rolando
        cenario 2: 70% das bolas mortas somem + 25% do jogo rolando
  - Tres previsoes, todas a partir da bola "apagada":
        REGRAS  pipeline v1.11 sem smart tagging (o IDSSE nao tem): nearest-player, preenche
                curto, voto +-3 s, parada, histerese, sumico >= 18 s -> D, senao continua
        LSTM    argmax do modelo em todo frame
        HIBRIDO regras onde a bola esta visivel; LSTM so nos frames sem bola; histerese 1,5 s

REGRA DE DECISAO (declarada antes de rodar):
  O HIBRIDO e o candidato. Ele entra no pipeline SO SE tiver spellF1 pelo menos 0,02 maior que
  as REGRAS nos DOIS jogos reservados e nos DOIS cenarios (4 de 4 comparacoes). Senao, nao entra.
  O LSTM puro e so informativo. Os numeros de desenvolvimento sao dentro da amostra (informativos).

Uso (depois de analises/cache_idsse.py):
    python analises/lstm_posse_idsse.py
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
import posse_lstm as L  # noqa: E402
import v1_11 as V11  # noqa: E402

MODELO = os.path.join(REPO, "src", "modelo_lstm.pt")
SORTEIOS = 6
EPOCAS = 12
SEED = 2027
CENARIOS = [(0.85, 0.15), (0.70, 0.25)]


def nearest(ball, H, A):
    n = len(ball)
    with np.errstate(all="ignore"):
        dh = np.nanmin(np.linalg.norm(H - ball[:, None], axis=2), axis=1)
        da = np.nanmin(np.linalg.norm(A - ball[:, None], axis=2), axis=1)
    dh, da = np.nan_to_num(dh, nan=np.inf), np.nan_to_num(da, nan=np.inf)
    codes = np.full(n, -1, np.int64)
    tem = np.isfinite(ball[:, 0]) & (np.isfinite(dh) | np.isfinite(da))
    codes[tem & (dh <= da)] = 0
    codes[tem & (da < dh)] = 1
    return codes


def regras(codes, baseline, period):
    blocos = []
    for per in np.unique(period):
        idx = np.flatnonzero(period == per)
        blocos.append((per, idx[0], idx[-1]))
    gaps = V11.sumicos(codes, baseline.NOBODY, blocos)
    lab = V11.base(codes, baseline, gaps)
    lab = V11.decidir_sumicos(lab, [], int(2.0 * L.FPS), 18.0)
    return lab


def main():
    import torch
    torch.manual_seed(SEED)
    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True)
    oficial = V11.preparar_caminhos(os.path.join(REPO, "oficial"))
    import baseline
    import possession_metrics as pm

    rng = np.random.default_rng(SEED)
    t0 = time.time()
    Xtr, Ytr = [], []
    for m in C.DEV:
        g = C.carregar(m)
        y = L.rotulos_idsse(g)
        for _ in range(SORTEIOS):
            X = L.sinais(L.simular_sumicos(g, rng), g["home"], g["away"], g["period"])
            for xs, ys in L.janelas(X, y):
                if len(xs) == L.SEQ:
                    Xtr.append(xs)
                    Ytr.append(ys)
        print(f"{m}: sinais prontos ({time.time() - t0:.0f} s)", flush=True)
        del g
    Xtr, Ytr = np.stack(Xtr), np.stack(Ytr)
    mu = Xtr.reshape(-1, Xtr.shape[-1]).mean(0)
    sd = Xtr.reshape(-1, Xtr.shape[-1]).std(0) + 1e-6
    Xtr = ((Xtr - mu) / sd).astype(np.float32)
    print(f"treino: {len(Xtr)} sequencias de {L.SEQ} passos, {Xtr.shape[-1]} sinais", flush=True)

    modelo = L.construir_modelo(Xtr.shape[-1])
    opt = torch.optim.Adam(modelo.parameters(), lr=2e-3)
    freq = np.bincount(Ytr.ravel(), minlength=3) / Ytr.size
    peso = torch.tensor((1 / 3) / freq, dtype=torch.float32)
    lossf = torch.nn.CrossEntropyLoss(weight=peso)
    Xt, Yt = torch.from_numpy(Xtr), torch.from_numpy(Ytr)
    for ep in range(EPOCAS):
        modelo.train()
        perm = torch.randperm(len(Xt))
        tot = 0.0
        for i in range(0, len(perm), 32):
            j = perm[i:i + 32]
            opt.zero_grad()
            out = modelo(Xt[j])
            loss = lossf(out.reshape(-1, 3), Yt[j].reshape(-1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
            opt.step()
            tot += float(loss) * len(j)
        print(f"  epoca {ep + 1:>2}: perda {tot / len(Xt):.4f} ({time.time() - t0:.0f} s)", flush=True)
    torch.save({"estado": modelo.state_dict(), "mu": mu, "sd": sd, "F": Xtr.shape[-1]}, MODELO)
    print(f"modelo salvo em src/modelo_lstm.pt")

    def nota(gt, pred):
        r = pm.evaluate(pm.label_codes(gt), pm.label_codes(pred), bootstrap_n=0)
        return float(r["spell_f1_mean"]), float(r["macro_f1"])

    print("\n" + "=" * 92)
    print("spellF1 (macroF1) com a bola apagada | REGRAS x LSTM x HIBRIDO")
    print("=" * 92)
    veredito = []
    for grupo, jogos in (("DEV (dentro da amostra)", C.DEV), ("RESERVADOS", C.RESERVA)):
        print(f"\n{grupo}")
        for m in jogos:
            g = C.carregar(m)
            gt = np.array(L.CLASSES)[L.rotulos_idsse(g)]
            for k, (pm_, fv) in enumerate(CENARIOS):
                r2 = np.random.default_rng(100 + k)
                ball = L.simular_sumicos(g, r2, p_morto=pm_, frac_vivo=fv)
                codes = nearest(ball, g["home"], g["away"])
                lr = regras(codes, baseline, g["period"])
                P = L.prever(modelo, L.sinais(ball, g["home"], g["away"], g["period"]), mu, sd)
                ll = np.array(L.CLASSES)[P.argmax(1)]
                hb = lr.copy()
                sem = codes == baseline.NOBODY
                hb[sem] = ll[sem]
                hb = V11.histerese(hb, 1.5)
                sr, mr = nota(gt, lr)
                sl, ml = nota(gt, ll)
                sh, mh = nota(gt, hb)
                vis = 100 * np.isfinite(ball[:, 0]).mean()
                print(f"  {m} cen{k + 1} (bola visivel {vis:4.1f}%): REGRAS {sr:.4f} ({mr:.3f}) | "
                      f"LSTM {sl:.4f} ({ml:.3f}) | HIBRIDO {sh:.4f} ({mh:.3f}) | hib-reg {sh - sr:+.4f}",
                      flush=True)
                if m in C.RESERVA:
                    veredito.append(sh - sr >= 0.02)
            del g
    ok = len(veredito) == 4 and all(veredito)
    print(f"\n-> HIBRIDO {'APROVADO' if ok else 'REPROVADO'} pela regra declarada "
          f"({sum(veredito)}/4 comparacoes nos reservados com ganho >= 0,02)")


if __name__ == "__main__":
    main()
