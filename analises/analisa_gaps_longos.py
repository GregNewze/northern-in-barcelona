"""analisa_gaps_longos.py - os sumicos longos sao PARADA ou JOGO? (sem gabarito)

Os sumicos de mais de 20 s sao ~67% do tempo sem bola (~27% do jogo avaliado) e a v1.11
marca todos como D. Aqui medimos uma coisa fisica que nao depende de rotulo: QUANTO OS
JOGADORES SE MEXEM durante cada sumico. Em bola parada eles andam; com a bola rolando correm.

Referencias (o que ja sabemos de cada grupo):
  - JOGO  : frames com a bola VISIVEL e rotulo H/A na v1.11
  - PARADA: sumicos que coincidem com um SET PIECE do smart tagging

Pergunta: os sumicos SEM set piece (sobretudo os longos) se parecem com JOGO ou com PARADA?

Tambem roda uma ABLACAO: liga/desliga o "preenche sumico <= 2,6 s" e conta quantos frames
mudam. Se for 0, o passo nao faz nada.

Nada aqui le o gabarito.

Uso:
    python analises/analisa_gaps_longos.py
"""

import argparse
import os
import sys
import warnings

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)
import v1_11 as N  # noqa: E402

FPS = 25
PASSO = 5            # velocidade = deslocamento em 5 frames (0,2 s): menos ruido que frame a frame
MAX_MS = 12.0        # acima disso e salto do tracker, nao corrida (recorde humano ~12 m/s)


def ler_jogadores(txt, n, length, width):
    """(n, slots, 2) float32 em metros, NaN quando o slot nao esta em campo."""
    pos = None
    with open(txt, encoding="utf-8", errors="replace") as f:
        for linha in f:
            parts = linha.rstrip("\n").split(":")
            if len(parts) != 3:
                continue
            idx = int(parts[0]) - 1
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
    """Velocidade mediana (m/s) dos jogadores em campo, por frame."""
    n = pos.shape[0]
    v = np.full(n, np.nan, dtype=np.float32)
    d = np.linalg.norm(pos[PASSO:] - pos[:-PASSO], axis=2) / (PASSO / FPS)   # (n-PASSO, slots)
    d[d > MAX_MS] = np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(d, axis=1)
    cont = np.sum(~np.isnan(d), axis=1)
    med[cont < 6] = np.nan          # poucos jogadores visiveis -> sem leitura
    v[PASSO:] = med
    return v


def resumo(x):
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return "   (sem dados)"
    p = np.percentile(x, [25, 50, 75])
    return "n=%6d  p25 %.2f  mediana %.2f  p75 %.2f m/s" % (len(x), p[0], p[1], p[2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oficial", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "oficial"))
    ap.add_argument("--tol", type=float, default=2.0)
    a = ap.parse_args()

    oficial = N.preparar_caminhos(a.oficial)
    import baseline
    try:
        length, width = baseline.GAMES[baseline.GAME]["pitch"]
    except Exception:
        length, width = 105.0, 68.0

    labels, et = N.gerar_labels(oficial, devolver_etapas=True)
    codes, gaps, ev, blocos = et["codes"], et["gaps"], et["ev"], et["blocos"]
    n = len(labels)
    graded = np.zeros(n, dtype=bool)
    for _, x0, x1 in blocos:
        graded[x0:x1 + 1] = True
    tol_f = int(a.tol * FPS)

    # ---------- 0. ablacao do preenche 2,6 s ----------
    import possession_metrics as pm

    def pipeline(max_fill):
        c = N.preencher_sumicos(codes, gaps, baseline.NOBODY, max_fill)
        lab = baseline.smooth(c, 75)
        lab = N.marcar_parada(lab, gaps, 0.5)
        lab = N.histerese(lab, 1.5)
        return N.forcar_bola_morta(N.decidir_sumicos(lab, ev, tol_f, 18.0))

    com = pipeline(2.6)
    sem = pipeline(0.0)
    assert np.array_equal(com, labels), "reconstrucao do pipeline nao bate com a v1_11 (!!)"
    print("\n" + "=" * 78)
    print("0. ABLACAO: o 'preenche sumico <= 2,6 s' faz alguma coisa?")
    print("=" * 78)
    gap_dur = np.array([(b - a_ + 1) / FPS for a_, b in gaps])
    print("   sumicos avaliados com <= 2,6 s: %d de %d" % (int(np.sum(gap_dur <= 2.6)), len(gaps)))
    print("   frames que mudam ao desligar   : %d (jogo todo) | %d (janela publica)"
          % (int(np.sum(com != sem)), int(np.sum(com[11185:18685] != sem[11185:18685]))))

    # ---------- 1. atividade dos jogadores ----------
    txt = os.path.join(oficial, "data", "tactical", "BAR-ATH_tactical_atd.txt")
    print("\n[lendo posicoes dos jogadores ...]")
    pos = ler_jogadores(txt, n, length, width)
    v = atividade_por_frame(pos)

    bola = codes != baseline.NOBODY
    jogo = graded & bola & np.isin(labels, ["H", "A"])
    print("\n" + "=" * 78)
    print("1. REFERENCIAS: velocidade mediana dos jogadores (m/s)")
    print("=" * 78)
    print("   JOGO   (bola visivel, H/A)     : " + resumo(v[jogo]))

    linhas = []
    for a_, b in gaps:
        dur = (b - a_ + 1) / FPS
        sp = N.intersecta(a_, b, ev, tol_f)
        act = v[a_:b + 1]
        act = act[~np.isnan(act)]
        linhas.append((a_, b, dur, sp, float(np.median(act)) if len(act) else np.nan,
                       labels[a_] if a_ < n else "?"))
    gaps_sp = np.concatenate([v[a_:b + 1] for a_, b, _, sp, _, _ in linhas if sp]) if any(l[3] for l in linhas) else np.array([])
    print("   PARADA (sumico com set piece)  : " + resumo(gaps_sp))

    print("\n" + "=" * 78)
    print("2. SUMICOS POR DURACAO: com set piece (parada) x sem set piece (?)")
    print("=" * 78)
    print("   %-8s | %-30s | %-30s" % ("duracao", "COM set piece: n | med m/s", "SEM set piece: n | med m/s"))
    faixas = [(0, 5), (5, 8), (8, 12), (12, 18), (18, 30), (30, 60), (60, 1e9)]
    for lo, hi in faixas:
        com_sp = [l for l in linhas if lo <= l[2] < hi and l[3]]
        sem_sp = [l for l in linhas if lo <= l[2] < hi and not l[3]]

        def m(ls):
            vals = [l[4] for l in ls if not np.isnan(l[4])]
            return "%3d | %.2f" % (len(ls), float(np.median(vals))) if vals else "%3d |  -  " % len(ls)
        nome = ("%d-%ds" % (lo, hi)) if hi < 1e8 else ("%ds+" % lo)
        print("   %-8s | %-30s | %-30s" % (nome, m(com_sp), m(sem_sp)))

    # limiar "parece parada": entre as duas referencias
    jm = float(np.nanmedian(v[jogo]))
    pm_ = float(np.nanmedian(gaps_sp)) if len(gaps_sp) else np.nan
    corte = (jm + pm_) / 2 if not np.isnan(pm_) else np.nan
    print("\n   corte no meio das referencias: %.2f m/s (abaixo = parece PARADA, acima = parece JOGO)" % corte)

    print("\n" + "=" * 78)
    print("3. O QUE A v1.11 FAZ HOJE COM OS SUMICOS SEM SET PIECE, por aparencia")
    print("=" * 78)
    for nome, cond in (("< 18 s (v1.11: continuacao)", lambda d: d < 18), (">= 18 s (v1.11: D)", lambda d: d >= 18)):
        ls = [l for l in linhas if not l[3] and cond(l[2]) and not np.isnan(l[4])]
        if not ls:
            print("   %-28s nenhum" % nome)
            continue
        parece_jogo = [l for l in ls if l[4] >= corte]
        fr_j = sum(int(l[1] - l[0] + 1) for l in parece_jogo)
        fr_t = sum(int(l[1] - l[0] + 1) for l in ls)
        print("   %-28s %3d sumicos | parecem JOGO: %3d (%5d de %5d frames)" % (nome, len(ls), len(parece_jogo), fr_j, fr_t))
    ls = [l for l in linhas if l[3] and not np.isnan(l[4])]
    if ls:
        pj = [l for l in ls if l[4] >= corte]
        print("   %-28s %3d sumicos | parecem JOGO: %3d  <- se for alto, o corte nao separa nada" % ("com set piece (v1.11: D)", len(ls), len(pj)))

    print("\n" + "=" * 78)
    print("LEITURA (honesta):")
    print(" - Se JOGO e PARADA tiverem velocidades bem diferentes, o sinal existe.")
    print(" - Se os longos SEM set piece parecerem JOGO, a v1.11 provavelmente marca D errado neles.")
    print(" - Isto e indicio, nao gabarito. Antes de virar regra, validar o sinal no IDSSE")
    print("   (la tem ball_state vivo/morto de verdade).")


if __name__ == "__main__":
    main()