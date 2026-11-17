"""v1.13 da Northern in Barcelona = v1.12 + Bi-LSTM nos frames sem bola (HIBRIDO).

So entra na entrega se analises/lstm_posse_idsse.py aprovar o HIBRIDO pela regra declarada
(ver validacao/REGISTRO.md). O modelo (src/modelo_lstm.pt) e treinado SO no IDSSE; aqui ele
apenas e aplicado. Nada aqui le o gabarito.

Mudanca em relacao a v1.12:
  - onde a bola esta visivel: rotulo da v1.12;
  - onde a bola sumiu: classe mais provavel do Bi-LSTM (H, A ou D);
  - sumico que coincide com SET PIECE do smart tagging continua D (sinal automatico do
    proprio jogo, mantido por precaucao: o IDSSE nao tem smart tagging para testar a troca);
  - histerese 1,5 s no fim (igual ao HIBRIDO testado) e FAQ (intervalo) por ultimo.

Uso:
    python src/v1_13.py --saida northern-in-barcelona.csv
"""

import argparse
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)
import posse_lstm as L  # noqa: E402
import v1_11 as V11  # noqa: E402
import v1_12 as V12  # noqa: E402

MODELO = os.path.join(AQUI, "modelo_lstm.pt")


def ler_bola(txt_path, n, length, width):
    bola = np.full((n, 2), np.nan, np.float32)
    with open(txt_path, encoding="utf-8", errors="replace") as f:
        for linha in f:
            parts = linha.rstrip("\n").split(":")
            if len(parts) != 3:
                continue
            try:
                idx = int(parts[0]) - 1
            except ValueError:
                continue
            if idx < 0 or idx >= n or not parts[2] or parts[2][0] == "N":
                continue
            p = parts[2].split(",")
            try:
                bola[idx] = (float(p[0]) * length, float(p[1]) * width)
            except (ValueError, IndexError):
                pass
    return bola


def carregar_modelo():
    import torch
    ck = torch.load(MODELO, map_location="cpu", weights_only=False)
    m = L.construir_modelo(ck["F"])
    m.load_state_dict(ck["estado"])
    return m, ck["mu"], ck["sd"]


def gerar_labels(oficial, devolver_etapas=False):
    oficial = V11.preparar_caminhos(oficial)
    import baseline
    import torch
    torch.set_num_threads(4)
    try:
        length, width = baseline.GAMES[baseline.GAME]["pitch"]
    except Exception:
        length, width = 105.0, 68.0

    lab12, et = V12.gerar_labels(oficial, devolver_etapas=True)
    codes, gaps, ev, blocos = et["codes"], et["gaps"], et["ev"], et["blocos"]
    n = len(codes)
    tactical = os.path.join(oficial, "data", "tactical")
    txt = os.path.join(tactical, "BAR-ATH_tactical_atd.txt")
    times = baseline.team_of_each_track(os.path.join(tactical, "BAR-ATH_tactical_atd.xml"))
    pos = V12.ler_jogadores(txt, n, length, width)
    k = min(len(times), pos.shape[1])
    home = pos[:, :k][:, times[:k] == baseline.HOME]
    away = pos[:, :k][:, times[:k] == baseline.AWAY]
    bola = ler_bola(txt, n, length, width)
    period = np.zeros(n, np.int8)
    for half, a, b in blocos:
        period[a:b + 1] = int(half) if str(half).isdigit() else (1 if a < n // 2 else 2)

    modelo, mu, sd = carregar_modelo()
    P = L.prever(modelo, L.sinais(bola, home, away, period), mu, sd)
    ll = np.array(L.CLASSES)[P.argmax(1)]

    sem_bola = codes == baseline.NOBODY
    sp = np.zeros(n, bool)
    tol_f = int(2.0 * V11.FPS)
    for a, b in gaps:
        if V11.intersecta(a, b, ev, tol_f):
            sp[a:b + 1] = True
    hb = lab12.copy()
    troca = sem_bola & ~sp
    hb[troca] = ll[troca]
    hb = V11.histerese(hb, 1.5)
    labels = V11.forcar_bola_morta(hb)
    if devolver_etapas:
        et.update(dict(labels_v1_12=lab12, prob=P, trocados=int(troca.sum())))
        return labels, et
    return labels


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--oficial", default=V11.OFICIAL_PADRAO)
    ap.add_argument("--saida", default=None)
    a = ap.parse_args()
    oficial = V11.preparar_caminhos(a.oficial)
    import baseline
    import possession_metrics as pm

    labels, et = gerar_labels(oficial, devolver_etapas=True)
    graded = et["graded"]
    dif = int(np.sum((labels != et["labels_v1_12"]) & graded))
    print("\nv1.13: frames sem bola decididos pelo LSTM: %d | frames avaliados diferentes da v1.12: %d"
          % (et["trocados"], dif))
    for nome, lab in (("v1.12", et["labels_v1_12"]), ("v1.13", labels)):
        print("%-6s | posses %d | dur med %.1fs | D %.1f%%" % ((nome,) + V11.stats(lab, graded)))
    if a.saida is not None:
        destino = os.path.join(oficial, "evaluation", "results", a.saida)
        baseline.write_submission(destino, labels)
        erro = pm.validate_submission(pm.read_label_csv(destino), len(labels))
        print("gerado: %s  (validacao oficial: %s)" % (destino, "ok" if erro is None else erro))


if __name__ == "__main__":
    main()
