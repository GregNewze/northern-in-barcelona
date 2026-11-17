"""v1.11 da Northern in Barcelona: nearest-player + tratamento dos sumicos da bola.

Bola morta do FAQ oficial: "the second half is graded from frame 110,808 but does not
kick off until 113,742. Those 2,934 frames are graded and all of them are D."

Pipeline:
  1. nearest-player (baseline.build)
  2. preenche sumico <= 2.6 s se o time e o mesmo dos dois lados
  3. voto de maioria em +-75 frames (+-3 s)
  4. sumico >= 0.5 s vira candidato a D
  5. histerese: posse < 1.5 s e absorvida
  6. cada sumico candidato:
       coincide com SET PIECE (+-2 s)  -> D
       dura >= 18 s                    -> D
       senao                           -> continuacao (ultimo time com a bola)
  7. frames 110808-113741 -> D (FAQ)

Uso:
    python src/v1_11.py --saida northern-in-barcelona.csv
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np

FPS = 25
FAQ_BOLA_MORTA = (110808, 113741)   # inclusivo; FAQ.md "Which frames are actually graded?"
PUB = (11185, 18684)
# Repo oficial (fork GregNewze/more-than-a-hack-2027) vem como submodulo em ./oficial.
# Para usar outra pasta: --oficial "..." ou variavel de ambiente OFICIAL.
OFICIAL_PADRAO = os.environ.get("OFICIAL") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "oficial")


def preparar_caminhos(oficial):
    oficial = os.path.abspath(oficial)
    for sub in ("", "starter", "evaluation"):
        caminho = os.path.join(oficial, sub)
        if caminho not in sys.path:
            sys.path.insert(0, caminho)
    return oficial


def trechos(mascara):
    m = np.concatenate(([False], mascara, [False])).astype(np.int8)
    d = np.diff(m)
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1))


def sumicos(codes, nobody, blocos):
    out = []
    for _, primeiro, ultimo in blocos:
        for a, b in trechos(codes[primeiro:ultimo + 1] == nobody):
            out.append((primeiro + a, primeiro + b))
    return out


def preencher_sumicos(codes, gaps, nobody, max_s):
    out = codes.copy()
    for a, b in gaps:
        if (b - a + 1) / FPS > max_s or a == 0 or b + 1 >= len(out):
            continue
        antes, depois = out[a - 1], out[b + 1]
        if antes == depois and antes != nobody:
            out[a:b + 1] = antes
    return out


def marcar_parada(labels, gaps, min_s):
    if min_s <= 0:
        return labels
    out = labels.copy()
    for a, b in gaps:
        if (b - a + 1) / FPS >= min_s:
            out[a:b + 1] = "D"
    return out


def histerese(labels, min_s):
    if min_s <= 0:
        return labels
    min_frames = int(min_s * FPS)
    out = labels.copy()
    mudou = True
    for _ in range(10):
        if not mudou:
            break
        mudou = False
        posses = []
        i = 0
        while i < len(out):
            j = i
            while j + 1 < len(out) and out[j + 1] == out[i]:
                j += 1
            posses.append((i, j, out[i]))
            i = j + 1
        for idx, (a, b, rotulo) in enumerate(posses):
            if rotulo not in ("H", "A"):
                continue
            if b - a + 1 >= min_frames:
                continue
            antes = next((posses[k][2] for k in range(idx - 1, -1, -1)
                          if posses[k][2] in ("H", "A")), None)
            depois = next((posses[k][2] for k in range(idx + 1, len(posses))
                           if posses[k][2] in ("H", "A")), None)
            if antes and depois and antes == depois:
                out[a:b + 1] = antes
                mudou = True
            elif antes:
                out[a:b + 1] = antes
                mudou = True
    return out


def ler_set_pieces(xml_path):
    root = ET.parse(xml_path).getroot()
    out = []
    for inst in root.findall('.//instance'):
        if inst.findtext('code') != 'SET PIECES':
            continue
        try:
            out.append((int(float(inst.findtext('start')) * FPS), int(float(inst.findtext('end')) * FPS)))
        except (TypeError, ValueError):
            continue
    return out


def intersecta(a_f, b_f, eventos_frames, tol_f):
    for s, e in eventos_frames:
        if a_f <= e + tol_f and b_f >= s - tol_f:
            return True
    return False


def base(codes, baseline, gaps):
    c = preencher_sumicos(codes, gaps, baseline.NOBODY, 2.6)
    lab = baseline.smooth(c, 75)
    lab = marcar_parada(lab, gaps, 0.5)
    lab = histerese(lab, 1.5)
    return lab


def decidir_sumicos(labels, ev, tol_f, dmaxseg_s):
    """Cada trecho de D: set piece -> D; >= dmaxseg -> D; senao continuacao."""
    out = labels.copy()
    n = len(out)
    ultimo = "X"
    i = 0
    while i < n:
        if out[i] in ("H", "A"):
            ultimo = out[i]
            i += 1
        elif out[i] == "D":
            j = i
            while j + 1 < n and out[j + 1] == "D":
                j += 1
            dur = (j - i + 1) / FPS
            if intersecta(i, j, ev, tol_f):
                pass
            elif dur >= dmaxseg_s:
                pass
            else:
                out[i:j + 1] = ultimo
            i = j + 1
        else:
            i += 1
    return out


def forcar_bola_morta(labels):
    out = labels.copy()
    out[FAQ_BOLA_MORTA[0]:FAQ_BOLA_MORTA[1] + 1] = "D"
    return out


def stats(labels, graded):
    lab = labels.copy()
    lab[~graded] = "X"
    posses, dur = 0, []
    i, n = 0, len(lab)
    while i < n:
        if lab[i] in ("H", "A"):
            j = i
            while j + 1 < n and lab[j + 1] == lab[i]:
                j += 1
            posses += 1
            dur.append((j - i + 1) / FPS)
            i = j + 1
        else:
            i += 1
    dpct = float(np.sum(labels[graded] == "D")) / graded.sum() * 100
    return posses, (float(np.mean(dur)) if dur else 0.0), dpct


def gerar_labels(oficial, tol=2.0, dmaxseg=18.0, devolver_etapas=False):
    """Gera os rotulos do jogo todo. NAO le o gabarito (testado em test_integracao)."""
    oficial = preparar_caminhos(oficial)
    import baseline
    import games

    xml = os.path.join(oficial, "data", "tactical", "BAR-ATH_tactical_smart_tagging.xml")
    ev = ler_set_pieces(xml)
    codes = baseline.build()
    blocos = games.half_video_blocks(games.GAME)
    gaps = sumicos(codes, baseline.NOBODY, blocos)
    lab_base = base(codes, baseline, gaps)
    sem_faq = decidir_sumicos(lab_base, ev, int(tol * FPS), dmaxseg)
    labels = forcar_bola_morta(sem_faq)
    if devolver_etapas:
        return labels, dict(codes=codes, blocos=blocos, gaps=gaps, ev=ev,
                            lab_base=lab_base, sem_faq=sem_faq, xml=xml)
    return labels


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--oficial", default=OFICIAL_PADRAO)
    p.add_argument("--tol", type=float, default=2.0)
    p.add_argument("--dmaxseg", type=float, default=18.0)
    p.add_argument("--saida", default=None)
    a = p.parse_args()

    oficial = preparar_caminhos(a.oficial)
    import baseline
    import possession_metrics as pm

    tol_f = int(a.tol * FPS)
    labels, et = gerar_labels(oficial, a.tol, a.dmaxseg, devolver_etapas=True)
    codes, blocos, gaps, ev, sem_faq, xml = (et["codes"], et["blocos"], et["gaps"], et["ev"],
                                             et["sem_faq"], et["xml"])
    n = len(codes)

    graded = np.zeros(n, dtype=bool)
    for _, p0, p1 in blocos:
        graded[p0:p1 + 1] = True

    if a.saida is not None:
        destino = os.path.join(oficial, "evaluation", "results", a.saida)
        baseline.write_submission(destino, labels)
        erro = pm.validate_submission(pm.read_label_csv(destino), len(labels))
        print(f"\ngerado: {destino}  (validacao oficial: {'ok' if erro is None else erro})")

    posses, dur, dpct = stats(labels, graded)
    seg = labels[FAQ_BOLA_MORTA[0]:FAQ_BOLA_MORTA[1] + 1]
    print(f"\njogo todo avaliado: {posses} posses | duracao media {dur:.1f}s | D {dpct:.1f}%")
    print(f"bloco do FAQ: D={int(np.sum(seg == 'D'))}/{len(seg)}")


if __name__ == "__main__":
    main()