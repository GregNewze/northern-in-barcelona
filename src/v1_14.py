"""v1.14 da Northern in Barcelona: os JOGADORES decidem os sumicos da bola.

Mudancas em relacao a v1.12 (declaradas em validacao/REGISTRO.md antes de aplicar):
  1. Preenchimento e parada = 3,0 s: o meio da faixa 1-5 s onde o jogo nao tem nenhum sumico
     (analise_sumicos.py). analises/sensibilidade_parametros.py mostra que nenhum frame muda
     entre 0,5 e 4,9 s, entao o resultado e identico ao dos valores antigos.
  2. O teto de 18 s e a regra da calma saem. Cada sumico com >= 5 s, sem set piece e fora do
     bloco do FAQ, e decidido por dois classificadores treinados SO no IDSSE
     (analises/sinais_jogadores_idsse.py, aprovados nos jogos reservados; pesos em
     src/modelo_sinais.json, exportados por analises/exporta_sinais_idsse.py):
       P1 (intensidade, sprint, queda, agrupamento, convergencia, jogador na linha, area)
          prob > 0,5 -> D (bola parada)
       P2 senao: qual time tem a bola (avanco, espalhar, perto, receptor, saida, permanencia,
          superioridade, voronoi, sincronia, contra-ataque, dispersao + ultimo time)
  3. Mantidos: janela +-75 e histerese 1,5 s (seleciona_janela_idsse.py manteve), set piece
     -> D, bloco do FAQ -> D.

Nao le o gabarito.

Uso:
    python src/v1_14.py --saida northern-in-barcelona.csv
"""

import argparse
import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AQUI)
for _p in (AQUI, os.path.join(REPO, "analises")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import v1_11 as V11  # noqa: E402
import v1_12 as V12  # noqa: E402
import sinais_jogadores_idsse as S  # noqa: E402  (mesmos sinais do experimento aprovado)

FPS = V11.FPS
PREENCHE_S = 3.0
PARADA_S = 3.0
JANELA = 75
HISTERESE_S = 1.5
MIN_GAP_S = 5.0
MODELO = os.path.join(AQUI, "modelo_sinais.json")


def ler_bola(txt_path, n, length, width):
    """(n, 2) em metros; NaN quando a bola sumiu. Linha "frame_id:jogadores:bola", frame_id de 1."""
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


def score(params, x):
    mu, sd, w = (np.array(params[k]) for k in ("mu", "sd", "w"))
    z = np.nan_to_num((np.asarray(x, float) - mu) / sd)
    return float(np.dot(np.append(z, 1.0), w))


def gerar_labels(oficial, tol=2.0, devolver_etapas=False):
    oficial = V11.preparar_caminhos(oficial)
    import baseline
    import games
    try:
        length, width = baseline.GAMES[baseline.GAME]["pitch"]
    except Exception:
        length, width = 105.0, 68.0
    with open(MODELO) as fh:
        mod = json.load(fh)

    tactical = os.path.join(oficial, "data", "tactical")
    ev = V11.ler_set_pieces(os.path.join(tactical, "BAR-ATH_tactical_smart_tagging.xml"))
    codes = baseline.build()
    n = len(codes)
    blocos = games.half_video_blocks(games.GAME)
    gaps = V11.sumicos(codes, baseline.NOBODY, blocos)
    tol_f = int(tol * FPS)

    c = V11.preencher_sumicos(codes, gaps, baseline.NOBODY, PREENCHE_S)
    lab = baseline.smooth(c, JANELA)
    lab = V11.marcar_parada(lab, gaps, PARADA_S)
    lab = V11.histerese(lab, HISTERESE_S)
    lab = V11.decidir_sumicos(lab, ev, tol_f, 1e9)     # set piece -> D; resto: continuacao

    txt = os.path.join(tactical, "BAR-ATH_tactical_atd.txt")
    times = baseline.team_of_each_track(os.path.join(tactical, "BAR-ATH_tactical_atd.xml"))
    pos = V12.ler_jogadores(txt, n, length, width)
    k = min(len(times), pos.shape[1])
    home = pos[:, :k][:, times[:k] == baseline.HOME]
    away = pos[:, :k][:, times[:k] == baseline.AWAY]
    del pos
    bola = ler_bola(txt, n, length, width)
    period = np.zeros(n, np.int8)
    for half, a, b in blocos:
        period[a:b + 1] = int(half)
    g = S.preparar(dict(ball=bola, home=home, away=away, dead=~np.isfinite(bola[:, 0]), period=period))

    out = lab.copy()
    decisoes = []
    faq0, faq1 = V11.FAQ_BOLA_MORTA
    for a, b in gaps:
        dur = (b - a + 1) / FPS
        if dur < MIN_GAP_S or V11.intersecta(a, b, ev, tol_f) or (a <= faq1 and b >= faq0):
            continue
        if a < 1 or not np.isfinite(bola[a - 1, 0]):
            continue
        p1, p2 = S.sinais(g, a, b)
        p2.pop("_disputa", None)
        if score(mod["p1"], list(p1.values())) > 0:
            out[a:b + 1] = "D"
            decisoes.append((a, b, "D"))
            continue
        antes = out[:a][np.isin(out[:a], ["H", "A"])]
        ult = 1.0 if (len(antes) and antes[-1] == "H") else -1.0
        t = "H" if score(mod["p2"], list(p2.values()) + [ult]) > 0 else "A"
        out[a:b + 1] = t
        decisoes.append((a, b, t))
    labels = V11.forcar_bola_morta(out)
    if devolver_etapas:
        graded = np.zeros(n, bool)
        for _, a, b in blocos:
            graded[a:b + 1] = True
        return labels, dict(codes=codes, gaps=gaps, ev=ev, blocos=blocos, graded=graded,
                            antes_dos_jogadores=V11.forcar_bola_morta(lab), decisoes=decisoes)
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
    dec = et["decisoes"]
    tipos = {t: sum(1 for *_, x in dec if x == t) for t in "DHA"}
    seg = {t: sum(b - a + 1 for a, b, x in dec if x == t) / FPS for t in "DHA"}
    print("\nv1.14: %d sumicos decididos pelos jogadores | D %d (%.0f s) | H %d (%.0f s) | A %d (%.0f s)"
          % (len(dec), tipos["D"], seg["D"], tipos["H"], seg["H"], tipos["A"], seg["A"]))
    print("%-6s | posses %d | dur med %.1fs | D %.1f%%" % (("v1.14",) + V11.stats(labels, et["graded"])))
    if a.saida is not None:
        destino = os.path.join(oficial, "evaluation", "results", a.saida)
        baseline.write_submission(destino, labels)
        erro = pm.validate_submission(pm.read_label_csv(destino), len(labels))
        print("gerado: %s  (validacao oficial: %s)" % (destino, "ok" if erro is None else erro))


if __name__ == "__main__":
    main()
