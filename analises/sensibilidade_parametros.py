"""sensibilidade_parametros.py - quanto cada parametro herdado MEXE nos rotulos? (sem gabarito)

Os valores 2,6 s (preenchimento), 0,5 s (parada) e 18 s (teto) vieram de um ajuste no gabarito
publico e precisam ser re-escolhidos. Antes de escolher, medimos se eles importam: para cada
valor alternativo contamos os frames AVALIADOS que mudam de rotulo em relacao aos valores
atuais. Nao le o gabarito; so imprime contagens.

Leitura:
  0 frames mudam numa faixa de valores -> o parametro e inerte ali; fixamos um valor da faixa
  por argumento fisico declarado, e o ajuste antigo deixa de ter efeito no resultado.
  Muitos frames mudam -> o parametro importa e precisa de escolha externa (IDSSE) ou de regra
  que o substitua.

Uso:
    python analises/sensibilidade_parametros.py
"""

import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
import v1_11 as V11  # noqa: E402


def main():
    oficial = V11.preparar_caminhos(os.path.join(REPO, "oficial"))
    import baseline
    import games

    ev = V11.ler_set_pieces(os.path.join(oficial, "data", "tactical", "BAR-ATH_tactical_smart_tagging.xml"))
    codes = baseline.build()
    blocos = games.half_video_blocks(games.GAME)
    gaps = V11.sumicos(codes, baseline.NOBODY, blocos)
    graded = np.zeros(len(codes), bool)
    for _, p0, p1 in blocos:
        graded[p0:p1 + 1] = True
    tol_f = int(2.0 * V11.FPS)

    def rotular(pre=2.6, W=75, par=0.5, H=1.5, teto=18.0):
        c = V11.preencher_sumicos(codes, gaps, baseline.NOBODY, pre)
        lab = baseline.smooth(c, W)
        lab = V11.marcar_parada(lab, gaps, par)
        lab = V11.histerese(lab, H)
        lab = V11.decidir_sumicos(lab, ev, tol_f, teto)
        return V11.forcar_bola_morta(lab)

    ref = rotular()
    tot = int(graded.sum())

    def mostra(nome, valores, chave):
        print(f"\n{nome}  (atual em [ ])")
        for v in valores:
            lab = rotular(**{chave: v})
            d = int(np.sum((lab != ref) & graded))
            atual = {"pre": 2.6, "par": 0.5, "teto": 18.0}[chave] == v
            print(f"  {('[%g]' % v) if atual else ('%g' % v):>7}: {d:>6} frames mudam ({d / tot * 100:5.2f}%)")

    print(f"frames avaliados: {tot}")
    mostra("PREENCHIMENTO (s)", [0, 0.5, 1.0, 1.5, 2.6, 3.0, 4.0, 4.9], "pre")
    mostra("PARADA (s)", [0.1, 0.5, 1.0, 2.0, 3.0, 4.9], "par")
    mostra("TETO dmaxseg (s)", [8, 12, 15, 18, 20, 25, 30, 45, 60, 1e9], "teto")


if __name__ == "__main__":
    main()
