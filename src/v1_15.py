"""v1.15 da Northern in Barcelona: base da v1.14 + Bi-LSTM nos frames sem bola (metodo B).

So e candidata se analises/comparacao_final_dev.py decidir TROCAR pela regra declarada
(validacao/REGISTRO.md #24). Mesmo desenho do metodo B testado no IDSSE:
  base (preenche 3 s, voto +-75, parada 3 s, histerese 1,5 s) -> continuacao nos sumicos ->
  frames sem bola = classe do Bi-LSTM -> histerese 1,5 s.
Diferencas declaradas em relacao ao B (o IDSSE nao tem smart tagging nem o intervalo do FAQ):
  sumico com SET PIECE continua D e o bloco do FAQ e D, como em todas as versoes.

O modelo (src/modelo_lstm.pt) foi treinado SO nos 5 jogos de desenvolvimento do IDSSE
(analises/lstm_posse_idsse.py). Aqui ele e apenas aplicado. Nada aqui le o gabarito.

Uso:
    python src/v1_15.py --saida northern-in-barcelona.csv
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
import v1_14 as V14  # noqa: E402

MODELO = os.path.join(AQUI, "modelo_lstm.pt")


def gerar_labels(oficial, tol=2.0, devolver_etapas=False):
    oficial = V11.preparar_caminhos(oficial)
    import baseline
    import games
    import torch
    torch.set_num_threads(4)
    try:
        length, width = baseline.GAMES[baseline.GAME]["pitch"]
    except Exception:
        length, width = 105.0, 68.0
    tactical = os.path.join(oficial, "data", "tactical")
    ev = V11.ler_set_pieces(os.path.join(tactical, "BAR-ATH_tactical_smart_tagging.xml"))
    codes = baseline.build()
    n = len(codes)
    blocos = games.half_video_blocks(games.GAME)
    gaps = V11.sumicos(codes, baseline.NOBODY, blocos)
    tol_f = int(tol * V11.FPS)

    c = V11.preencher_sumicos(codes, gaps, baseline.NOBODY, V14.PREENCHE_S)
    lab = baseline.smooth(c, V14.JANELA)
    lab = V11.marcar_parada(lab, gaps, V14.PARADA_S)
    lab = V11.histerese(lab, V14.HISTERESE_S)
    lab = V11.decidir_sumicos(lab, ev, tol_f, 1e9)

    txt = os.path.join(tactical, "BAR-ATH_tactical_atd.txt")
    times = baseline.team_of_each_track(os.path.join(tactical, "BAR-ATH_tactical_atd.xml"))
    pos = V12.ler_jogadores(txt, n, length, width)
    k = min(len(times), pos.shape[1])
    home = pos[:, :k][:, times[:k] == baseline.HOME]
    away = pos[:, :k][:, times[:k] == baseline.AWAY]
    del pos
    bola = V14.ler_bola(txt, n, length, width)
    period = np.zeros(n, np.int8)
    for half, a, b in blocos:
        period[a:b + 1] = int(half)

    ck = torch.load(MODELO, map_location="cpu", weights_only=False)
    modelo = L.construir_modelo(ck["F"])
    modelo.load_state_dict(ck["estado"])
    P = L.prever(modelo, L.sinais(bola, home, away, period), ck["mu"], ck["sd"])
    ll = np.array(L.CLASSES)[P.argmax(1)]

    sp = np.zeros(n, bool)
    for a, b in gaps:
        if V11.intersecta(a, b, ev, tol_f):
            sp[a:b + 1] = True
    troca = (codes == baseline.NOBODY) & ~sp
    out = lab.copy()
    out[troca] = ll[troca]
    out = V11.histerese(out, V14.HISTERESE_S)
    labels = V11.forcar_bola_morta(out)
    if devolver_etapas:
        graded = np.zeros(n, bool)
        for _, a, b in blocos:
            graded[a:b + 1] = True
        return labels, dict(codes=codes, gaps=gaps, graded=graded, trocados=int(troca.sum()),
                            antes_do_lstm=V11.forcar_bola_morta(lab))
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
    print("\nv1.15: frames sem bola (sem set piece) decididos pelo LSTM: %d" % et["trocados"])
    print("%-6s | posses %d | dur med %.1fs | D %.1f%%" % (("v1.15",) + V11.stats(labels, et["graded"])))
    if a.saida is not None:
        destino = os.path.join(oficial, "evaluation", "results", a.saida)
        baseline.write_submission(destino, labels)
        erro = pm.validate_submission(pm.read_label_csv(destino), len(labels))
        print("gerado: %s  (validacao oficial: %s)" % (destino, "ok" if erro is None else erro))


if __name__ == "__main__":
    main()
