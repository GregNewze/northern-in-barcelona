"""analise_sumicos.py - entende QUANDO, ONDE e COMO a bola some do tracking (os ~43%).

NAO mede nota. So descreve os sumicos pra a gente criar regras melhores e features:
  1. Distribuicao de DURACAO (oclusao curta vs bola realmente fora).
  2. O que tem ANTES e DEPOIS (mesmo time = oclusao; troca = disputa/perda).
  3. ONDE no campo a bola some (terco do campo + perto das linhas).
  4. Quantos coincidem com SET PIECE real (parada) vs nao (oclusao em jogo).
  5. Cruzamento: dos sumicos LONGOS, quantos sao parada real vs oclusao longa
     (isto valida a hipotese da v1.8/v1.9).

Uso:
    python analises/analise_sumicos.py
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np

FPS = 25


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


def ler_bola(txt_path, n):
    """Posicao (x,y) normalizada da bola por frame; NaN quando a bola sumiu.

    Formato da linha: "frame_id:jogadores:BOLA" (3 partes separadas por ':'), frame_id
    contado a partir de 1 -- igual ao baseline.nearest_player_labels. (Corrigido em 13/11:
    antes lia o 1o jogador como se fosse a bola.)"""
    bola = np.full((n, 2), np.nan)
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
            partes = parts[2].split(",")
            try:
                bola[idx] = (float(partes[0]), float(partes[1]))
            except (ValueError, IndexError):
                pass
    return bola


def ler_set_pieces(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    out = []
    for inst in root.findall('.//instance'):
        if inst.findtext('code') != 'SET PIECES':
            continue
        tipo = None
        for lbl in inst.findall('label'):
            if lbl.findtext('group') == 'Type':
                tipo = lbl.findtext('text')
                break
        try:
            out.append((float(inst.findtext('start')), float(inst.findtext('end')), tipo))
        except (TypeError, ValueError):
            continue
    return out


def barra(frac, larg=28):
    cheio = int(round(frac * larg))
    return "#" * cheio + "." * (larg - cheio)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--oficial", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "oficial"))
    p.add_argument("--tol", type=float, default=2.0, help="folga (s) pra casar sumico com SET PIECE")
    a = p.parse_args()

    oficial = preparar_caminhos(a.oficial)
    import baseline
    import games

    codes = baseline.build()
    n = len(codes)
    blocos = games.half_video_blocks(games.GAME)
    gaps = sumicos(codes, baseline.NOBODY, blocos)

    txt = os.path.join(oficial, "data", "tactical", "BAR-ATH_tactical_atd.txt")
    bola = ler_bola(txt, n) if os.path.exists(txt) else np.full((n, 2), np.nan)

    xml = os.path.join(oficial, "data", "tactical", "BAR-ATH_tactical_smart_tagging.xml")
    sps = ler_set_pieces(xml) if os.path.exists(xml) else []
    sp_frames = [(int(s * FPS), int(e * FPS)) for s, e, _ in sps]
    tol = int(a.tol * FPS)

    def tem_sp(x, y):
        for s, e in sp_frames:
            if x <= e + tol and y >= s - tol:
                return True
        return False

    H, A, NB = baseline.HOME, baseline.AWAY, baseline.NOBODY
    sem_bola = int(np.sum(codes == NB))

    print()
    print("=" * 74)
    print(f"ANALISE DOS SUMICOS DA BOLA   (jogo completo, {n} frames)")
    print("=" * 74)
    print(f"frames com bola : {n - sem_bola:>7} ({(n - sem_bola) / n * 100:4.1f}%)")
    print(f"frames SEM bola : {sem_bola:>7} ({sem_bola / n * 100:4.1f}%)   <- os famosos ~43%")
    print(f"numero de sumicos: {len(gaps)}   |   SET PIECES no jogo: {len(sps)}")

    # 1) DURACAO
    print("\n" + "-" * 74)
    print("1) DURACAO DOS SUMICOS  (quanto tempo a bola fica sumida de cada vez)")
    print("-" * 74)
    buckets = [(0, 1), (1, 2), (2, 3), (3, 5), (5, 8), (8, 12), (12, 20), (20, 1e9)]
    rotulos = ["0-1s", "1-2s", "2-3s", "3-5s", "5-8s", "8-12s", "12-20s", "20s+"]
    cont = [0] * len(buckets)
    tempo = [0.0] * len(buckets)
    for x, y in gaps:
        d = (y - x + 1) / FPS
        for i, (lo, hi) in enumerate(buckets):
            if lo <= d < hi:
                cont[i] += 1
                tempo[i] += d
                break
    tot = max(1, len(gaps))
    tot_t = max(1e-9, sum(tempo))
    print(f"{'faixa':>8} | {'qtd':>5} | {'% dos sumicos':>22} | {'% do tempo sumido':>18}")
    for i, r in enumerate(rotulos):
        print(f"{r:>8} | {cont[i]:>5} | {barra(cont[i]/tot)} {cont[i]/tot*100:4.1f}% | {tempo[i]/tot_t*100:5.1f}%")
    curtos = sum(cont[i] for i, (lo, hi) in enumerate(buckets) if hi <= 8)
    print(f"\n-> {curtos}/{len(gaps)} sumicos ({curtos/tot*100:.0f}%) sao < 8s (provavel oclusao)")

    # 2) ANTES -> DEPOIS
    print("\n" + "-" * 74)
    print("2) O QUE TEM ANTES E DEPOIS DO SUMICO")
    print("-" * 74)
    mesmo, troca, borda = 0, 0, 0
    for x, y in gaps:
        antes = codes[x - 1] if x > 0 else None
        depois = codes[y + 1] if y + 1 < n else None
        if antes in (H, A) and depois in (H, A):
            if antes == depois:
                mesmo += 1
            else:
                troca += 1
        else:
            borda += 1
    print(f"mesmo time antes e depois : {mesmo:>5} ({mesmo/tot*100:4.1f}%)  -> oclusao, jogo seguiu")
    print(f"TROCOU de time            : {troca:>5} ({troca/tot*100:4.1f}%)  -> disputa/perda no sumico")
    print(f"borda (inicio/fim do bloco): {borda:>5} ({borda/tot*100:4.1f}%)")

    # 3) ONDE no campo (posicao da bola no ultimo frame antes de sumir)
    print("\n" + "-" * 74)
    print("3) ONDE A BOLA ESTAVA AO SUMIR  (x = gol-a-gol, y = lateral-a-lateral)")
    print("-" * 74)
    tercos = {"esq (0-33%)": 0, "centro (33-67%)": 0, "dir (67-100%)": 0}
    perto_lateral, perto_gol, validos = 0, 0, 0
    for x, y in gaps:
        if x > 0 and not np.isnan(bola[x - 1, 0]):
            bx, by = bola[x - 1]
            validos += 1
            if bx < 0.333:
                tercos["esq (0-33%)"] += 1
            elif bx < 0.667:
                tercos["centro (33-67%)"] += 1
            else:
                tercos["dir (67-100%)"] += 1
            if by < 0.10 or by > 0.90:
                perto_lateral += 1
            if bx < 0.06 or bx > 0.94:
                perto_gol += 1
    if validos:
        for k, v in tercos.items():
            print(f"{k:>16} : {v:>5} ({v/validos*100:4.1f}%)")
        print(f"\nperto das LINHAS laterais (y<10% ou >90%): {perto_lateral} ({perto_lateral/validos*100:.1f}%)")
        print(f"perto das LINHAS de fundo  (x<6% ou >94%): {perto_gol} ({perto_gol/validos*100:.1f}%)")
    else:
        print("(sem coordenadas da bola - confira o caminho do .txt)")

    # 4) e 5) SET PIECE x duracao
    print("\n" + "-" * 74)
    print("4) SUMICO COINCIDE COM SET PIECE REAL?  (parada de verdade vs oclusao)")
    print("-" * 74)
    com_sp = sum(1 for x, y in gaps if tem_sp(x, y))
    print(f"sumicos que casam com SET PIECE: {com_sp} ({com_sp/tot*100:.1f}%)")
    print(f"sumicos SEM set piece          : {len(gaps)-com_sp} ({(len(gaps)-com_sp)/tot*100:.1f}%)")

    print("\n5) CRUZAMENTO (valida a v1.8/v1.9):")
    for faixa, lo, hi in [("curtos <8s", 0, 8), ("longos >=8s", 8, 1e9)]:
        g = [(x, y) for x, y in gaps if lo <= (y - x + 1) / FPS < hi]
        if not g:
            continue
        sp = sum(1 for x, y in g if tem_sp(x, y))
        print(f"  {faixa:>12}: {len(g):>4} sumicos | com set piece {sp:>3} ({sp/len(g)*100:4.1f}%) "
              f"| sem {len(g)-sp:>3} ({(len(g)-sp)/len(g)*100:4.1f}%)")
    print("\n  leitura: sumico LONGO + set piece = parada real (marcar D).")
    print("           sumico LONGO sem set piece = oclusao longa (a v1.9 trata como continuacao).")
    print("=" * 74)


if __name__ == "__main__":
    main()