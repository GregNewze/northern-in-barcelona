"""v1.12 da Northern in Barcelona = v1.11 + regra da CALMA.

Regra nova (unica mudanca em relacao a v1.11):
    sumico da bola SEM set piece, com 5 a 18 s, em que os jogadores se movem devagar
    -> D (bola parada), em vez de continuacao da posse.

"Devagar" = velocidade mediana dos jogadores no sumico abaixo do CORTE, que e o ponto medio
entre duas referencias medidas NO PROPRIO JOGO, sem gabarito:
    JOGO   = velocidade com a bola visivel e rotulo H/A (v1.11)
    PARADA = velocidade durante sumicos que coincidem com SET PIECE
No BAR-ATH: 1,67 e 0,95 m/s -> corte ~1,31 m/s.

Por que (13-14/11):
  - analisa_gaps_longos.py: 25 dos 56 sumicos <18 s sem set piece tinham cara de parada,
    e a v1.11 continuava a posse neles.
  - valida_calma_idsse.py (IDSSE, bola viva/morta REAL): o sinal separa morto de vivo com
    AUC 0,94-0,96; corte escolhido num jogo acerta 81-85% no outro. A velocidade de bola
    parada la (0,93-0,94 m/s) e a mesma do nosso jogo (0,95).
  - Ponto fraco conhecido: faixa 5-8 s pouco provada (n=3 num dos jogos do IDSSE).

Uso:
    python src/v1_12.py --saida northern-in-barcelona.csv [--verificar]
"""

import argparse
import os
import sys
import warnings

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)
import v1_11 as V11  # noqa: E402

FPS = V11.FPS
PASSO = 5            # velocidade = deslocamento em 0,2 s
MAX_MS = 12.0        # acima disso e salto do tracker
MIN_JOG = 6          # minimo de jogadores visiveis pra ler a velocidade do frame
CALMA_MIN_S = 5.0
CALMA_MAX_S = 18.0   # igual ao teto da v1.11: >= 18 s ja vira D


def ler_jogadores(txt, n, length, width):
    """(n, slots, 2) float32 em metros; NaN quando o slot nao esta em campo.
    Formato "frame_id:jogadores:bola", frame_id a partir de 1."""
    pos = None
    with open(txt, encoding="utf-8", errors="replace") as f:
        for linha in f:
            parts = linha.rstrip("\n").split(":")
            if len(parts) != 3:
                continue
            try:
                idx = int(parts[0]) - 1
            except ValueError:
                continue
            if idx < 0 or idx >= n:
                continue
            grupos = parts[1].split(";")
            if pos is None:
                pos = np.full((n, len(grupos), 2), np.nan, dtype=np.float32)
            for s, g in enumerate(grupos[:pos.shape[1]]):
                if not g or g[0] == "N":
                    continue
                p = g.split(",")
                try:
                    pos[idx, s, 0] = float(p[0]) * length
                    pos[idx, s, 1] = float(p[1]) * width
                except (ValueError, IndexError):
                    pass
    return pos


def atividade_por_frame(pos):
    """Velocidade mediana (m/s) dos jogadores em campo, por frame (NaN sem leitura)."""
    n = pos.shape[0]
    v = np.full(n, np.nan, dtype=np.float32)
    if n <= PASSO:
        return v
    d = np.linalg.norm(pos[PASSO:] - pos[:-PASSO], axis=2) / (PASSO / FPS)
    d[d > MAX_MS] = np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(d, axis=1)
    med[np.sum(~np.isnan(d), axis=1) < MIN_JOG] = np.nan
    v[PASSO:] = med
    return v


def mediana_trecho(v, a, b):
    x = v[a:b + 1]
    x = x[~np.isnan(x)]
    return float(np.median(x)) if len(x) else float("nan")


def referencias(v, labels, bola_visivel, graded, gaps, ev, tol_f):
    """Corte = ponto medio entre JOGO (bola visivel, H/A) e PARADA (sumicos com set piece)."""
    jogo = graded & bola_visivel & np.isin(labels, ["H", "A"])
    pj = v[jogo]
    pj = pj[~np.isnan(pj)]
    par = [v[a:b + 1] for a, b in gaps if V11.intersecta(a, b, ev, tol_f)]
    pp = np.concatenate(par) if par else np.array([], dtype=np.float32)
    pp = pp[~np.isnan(pp)]
    if len(pj) == 0 or len(pp) == 0:
        raise RuntimeError("sem dados pra calcular as referencias de velocidade")
    j, p = float(np.median(pj)), float(np.median(pp))
    return j, p, (j + p) / 2


def aplicar_calma(labels, gaps, ev, tol_f, v, corte):
    """Sumico sem set piece, CALMA_MIN_S <= dur < CALMA_MAX_S, velocidade < corte -> D.
    Devolve (rotulos, lista dos sumicos mudados)."""
    out = labels.copy()
    mudados = []
    for a, b in gaps:
        dur = (b - a + 1) / FPS
        if not (CALMA_MIN_S <= dur < CALMA_MAX_S):
            continue
        if V11.intersecta(a, b, ev, tol_f):
            continue
        m = mediana_trecho(v, a, b)
        if np.isnan(m) or m >= corte:
            continue
        out[a:b + 1] = "D"
        mudados.append((a, b, dur, m))
    return out, mudados


def gerar_labels(oficial, tol=2.0, dmaxseg=18.0, devolver_etapas=False):
    """Rotulos v1.12 do jogo todo. NAO le o gabarito."""
    oficial = V11.preparar_caminhos(oficial)
    import baseline
    try:
        length, width = baseline.GAMES[baseline.GAME]["pitch"]
    except Exception:
        length, width = 105.0, 68.0

    lab11, et = V11.gerar_labels(oficial, tol, dmaxseg, devolver_etapas=True)
    codes, gaps, ev, blocos, sem_faq = et["codes"], et["gaps"], et["ev"], et["blocos"], et["sem_faq"]
    n = len(codes)
    graded = np.zeros(n, dtype=bool)
    for _, a, b in blocos:
        graded[a:b + 1] = True
    tol_f = int(tol * FPS)

    txt = os.path.join(oficial, "data", "tactical", "BAR-ATH_tactical_atd.txt")
    v = atividade_por_frame(ler_jogadores(txt, n, length, width))
    # referencias com os rotulos FINAIS da v1.11 (FAQ aplicado), como no analisa_gaps_longos.py:
    # sem o FAQ, o aquecimento antes do 2o tempo entraria como "jogo" e puxaria a referencia pra baixo
    j, p, corte = referencias(v, lab11, codes != baseline.NOBODY, graded, gaps, ev, tol_f)
    calma, mudados = aplicar_calma(sem_faq, gaps, ev, tol_f, v, corte)
    labels = V11.forcar_bola_morta(calma)
    if devolver_etapas:
        et.update(dict(v=v, ref_jogo=j, ref_parada=p, corte=corte, mudados=mudados,
                       labels_v1_11=lab11, graded=graded))
        return labels, et
    return labels


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--oficial", default=V11.OFICIAL_PADRAO)
    ap.add_argument("--saida", default=None)
    ap.add_argument("--verificar", action="store_true")
    a = ap.parse_args()

    oficial = V11.preparar_caminhos(a.oficial)
    import baseline
    import possession_metrics as pm

    labels, et = gerar_labels(oficial, devolver_etapas=True)
    lab11, graded, mud = et["labels_v1_11"], et["graded"], et["mudados"]

    print("\nREGRA DA CALMA")
    print("  referencia JOGO   : %.3f m/s" % et["ref_jogo"])
    print("  referencia PARADA : %.3f m/s" % et["ref_parada"])
    print("  corte             : %.3f m/s" % et["corte"])
    print("  sumicos mudados pra D: %d (%d frames)" % (len(mud), sum(b - a + 1 for a, b, _, _ in mud)))

    if a.verificar:
        dif = np.flatnonzero(labels != lab11)
        dentro = np.zeros(len(labels), dtype=bool)
        for x0, x1, _, _ in mud:
            dentro[x0:x1 + 1] = True
        ok1 = bool(np.all(dentro[dif])) if len(dif) else True
        ok2 = bool(np.all(labels[dif] == "D")) if len(dif) else True
        ok3 = bool(np.all(np.isin(lab11[dif], ["H", "A"]))) if len(dif) else True
        print("\nVERIFICACAO v1.12 contra v1.11")
        print("  so mudou dentro dos sumicos elegiveis : %s" % ("OK" if ok1 else "FALHOU"))
        print("  toda mudanca e para D                 : %s" % ("OK" if ok2 else "FALHOU"))
        print("  so mudou frame que era H/A na v1.11   : %s" % ("OK" if ok3 else "FALHOU"))
        print("  frames diferentes da v1.11            : %d (%d na janela publica)"
              % (len(dif), int(np.sum((dif >= 11185) & (dif <= 18684)))))

    if a.saida is not None:
        destino = os.path.join(oficial, "evaluation", "results", a.saida)
        baseline.write_submission(destino, labels)
        erro = pm.validate_submission(pm.read_label_csv(destino), len(labels))
        print("\ngerado: %s  (validacao oficial: %s)" % (destino, "ok" if erro is None else erro))

    stats11 = V11.stats(lab11, graded)
    stats12 = V11.stats(labels, graded)
    # Sem nota publica aqui: o gabarito dos 5 min nao serve para comparar versoes (EVALUATION.md).
    print("\n%-6s | %6s | %8s | %6s" % ("", "posses", "dur med", "D%"))
    print("%-6s | %6d | %7.1fs | %5.1f%%" % (("v1.11",) + stats11))
    print("%-6s | %6d | %7.1fs | %5.1f%%" % (("v1.12",) + stats12))


if __name__ == "__main__":
    main()
