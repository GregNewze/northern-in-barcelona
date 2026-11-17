"""valida_parada_visivel_idsse.py - detector de BOLA PARADA COM A BOLA VISIVEL, validado fora.

Hoje so marcamos D quando a bola SOME. Num lateral/falta/tiro de meta cobrado com a bola na
tela, escrevemos H/A e colamos duas posses numa so. Regra candidata (fisica, sem gabarito):

    bola quase parada (velocidade < B m/s)  E  jogadores andando (velocidade mediana <
    k x mediana do proprio jogo com a bola visivel), por pelo menos T segundos seguidos  -> D

O corte dos jogadores e RELATIVO a cada jogo: k x (mediana da velocidade dos jogadores em TODOS
os frames com a bola visivel), calculada do MESMO jeito no IDSSE e no nosso jogo, porque o
tracking do IDSSE mede jogo rolando mais rapido que o nosso.

Teste no IDSSE (bola viva/morta REAL), mesmo desenho da selecao de janela:
  - pipeline: nearest-player -> votacao +-3 s -> histerese 1,5 s -> detector marca D ->
    histerese de novo (limpa pedacos curtos que sobrarem), igual ao que entraria na v1.13;
  - precisao/recall do D do detector contra a bola morta real (por frame);
  - spellF1 sem detector, com detector e com a bola morta perfeita (referencia; nao e um limite
    exato, porque o spellF1 depende de onde caem as fronteiras).

REGRA DE DECISAO (declarada antes de rodar):
  1. Entre as combinacoes com PRECISAO media >= 0,90 nos 5 jogos de desenvolvimento, vence a de
     maior RECALL medio (acha mais paradas sem errar).
  2. Ela so vira candidata se, nos DOIS jogos reservados, tiver precisao >= 0,90 E spellF1 maior
     que o pipeline sem detector.

Uso:
    python analises/valida_parada_visivel_idsse.py --oficial oficial
"""

import argparse
import os
import sys
import time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
for _p in (AQUI, os.path.join(os.path.dirname(AQUI), "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import v1_11 as V11  # noqa: E402
import v1_12 as V12  # noqa: E402

FPS = 25
PITCH_X, PITCH_Y = 105.0, 68.0
DEV = ["J03WPY", "J03WN1", "J03WMX", "J03WOY", "J03WQQ"]
RESERVA = ["J03WR9", "J03WOH"]
BS = [0.5, 1.0, 2.0]                # velocidade maxima da bola (m/s)
KS = [0.6, 0.7, 0.78, 0.9]          # corte dos jogadores = k x mediana do jogo com bola visivel
TS = [2.0, 3.0, 5.0]                # duracao minima (s)
PREC_MIN = 0.90


def carregar(match, HOME, AWAY, NOBODY):
    from kloppy import sportec
    tr = sportec.load_open_tracking_data(match_id=match, limit=None, only_alive=False)
    home, away = tr.metadata.teams[0], tr.metadata.teams[1]
    frames = tr.frames
    n = len(frames)
    slot = {}
    for fr in frames:
        for p in (getattr(fr, "players_coordinates", None) or {}):
            slot.setdefault(p, len(slot))
    pos = np.full((n, len(slot), 2), np.nan, dtype=np.float32)
    bola = np.full((n, 2), np.nan)
    codes = np.full(n, NOBODY, dtype=np.int64)
    gt = np.full(n, "D", dtype="<U1")
    morto = np.zeros(n, dtype=bool)
    for i, fr in enumerate(frames):
        if "DEAD" in str(getattr(fr, "ball_state", "")).upper():
            morto[i] = True
        else:
            bot = getattr(fr, "ball_owning_team", None)
            gt[i] = "H" if bot == home else ("A" if bot == away else "D")
        pcs = getattr(fr, "players_coordinates", None) or {}
        for p, pt in pcs.items():
            if getattr(pt, "x", None) is not None and getattr(pt, "y", None) is not None:
                pos[i, slot[p]] = (pt.x * PITCH_X, pt.y * PITCH_Y)
        bc = getattr(fr, "ball_coordinates", None)
        if bc is None or getattr(bc, "x", None) is None or getattr(bc, "y", None) is None:
            continue
        bx, by = bc.x * PITCH_X, bc.y * PITCH_Y
        bola[i] = (bx, by)
        melhor, t = None, NOBODY
        for p, pt in pcs.items():
            if getattr(pt, "x", None) is None or getattr(pt, "y", None) is None:
                continue
            d = (pt.x * PITCH_X - bx) ** 2 + (pt.y * PITCH_Y - by) ** 2
            if melhor is None or d < melhor:
                melhor, t = d, (HOME if p.team == home else AWAY)
        codes[i] = t
    gt[morto] = "D"
    return codes, gt, morto, bola, pos


def velocidade_bola(bola, passo=V12.PASSO):
    v = np.full(len(bola), np.nan)
    d = np.hypot(bola[passo:, 0] - bola[:-passo, 0], bola[passo:, 1] - bola[:-passo, 1]) / (passo / FPS)
    v[passo:] = d
    return v


def detector(vbola, vjog, B, corte, T):
    """True nos frames de trechos (>= T s) com bola < B m/s e jogadores < corte m/s."""
    cand = (vbola < B) & (vjog < corte)            # NaN -> False
    out = np.zeros(len(cand), dtype=bool)
    min_f = int(round(T * FPS))
    for a, b in V11.trechos(cand):
        if b - a + 1 >= min_f:
            out[a:b + 1] = True
    return out


def pipeline(codes, baseline, det=None, morto=None):
    """Mesmo processamento pra todos: o D marcado (pelo detector OU a bola morta real do teto)
    passa pela mesma segunda histerese. Senao o 'teto' nao seria comparavel."""
    lab = V11.histerese(baseline.smooth(codes, 75), 1.5)
    lab = lab.copy()
    marca = det if det is not None else morto
    if marca is not None:
        lab[marca] = "D"
        lab = V11.histerese(lab, 1.5)
    return lab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oficial", required=True)
    a = ap.parse_args()
    V11.preparar_caminhos(a.oficial)
    import baseline
    import possession_metrics as pm

    def spell(gt, lab):
        return float(pm.evaluate(pm.label_codes(gt), pm.label_codes(lab), bootstrap_n=0)["spell_f1_mean"])

    combos = [(B, k, T) for B in BS for k in KS for T in TS]
    res, base = {}, {}
    for m in DEV + RESERVA:
        t0 = time.time()
        print("carregando %s ..." % m, flush=True)
        codes, gt, morto, bola, pos = carregar(m, baseline.HOME, baseline.AWAY, baseline.NOBODY)
        vjog = V12.atividade_por_frame(pos)
        vbola = velocidade_bola(bola)
        vis = ~np.isnan(bola[:, 0])
        med_vis = float(np.nanmedian(vjog[vis]))
        s_sem = spell(gt, pipeline(codes, baseline))
        s_teto = spell(gt, pipeline(codes, baseline, morto=morto))
        base[m] = (s_sem, s_teto, med_vis, float(morto.mean()))
        res[m] = {}
        for (B, k, T) in combos:
            det = detector(vbola, vjog, B, k * med_vis, T)
            prec = float(morto[det].mean()) if det.any() else float("nan")
            rec = float(det[morto].mean()) if morto.any() else float("nan")
            res[m][(B, k, T)] = (prec, rec, spell(gt, pipeline(codes, baseline, det=det)), float(det.mean()))
        print("   %s ok (%.0f s) | mediana jogadores c/ bola visivel %.2f m/s | bola morta %.0f%% | "
              "spellF1 sem detector %.4f | ref. bola morta perfeita %.4f" % (m, time.time() - t0, med_vis, morto.mean() * 100, s_sem, s_teto),
              flush=True)

    def media(c, i):
        vals = [res[m][c][i] for m in DEV]
        vals = [v for v in vals if not np.isnan(v)]
        return float(np.mean(vals)) if vals else float("nan")

    print("\n" + "=" * 92)
    print("DESENVOLVIMENTO (%s)" % ", ".join(DEV))
    print("=" * 92)
    print("   %-22s | %-9s | %-9s | %-8s | %-9s | %s" % ("B(m/s) k  T(s)", "precisao", "recall", "% D", "spellF1", "vs sem detector"))
    s_sem_dev = np.mean([base[m][0] for m in DEV])
    ordem = sorted(combos, key=lambda c: (-(media(c, 0) >= PREC_MIN), -media(c, 1)))
    for c in ordem[:12]:
        print("   B=%-4.1f k=%-4.2f T=%-4.1f | %-9.3f | %-9.3f | %-8.1f | %-9.4f | %+.4f"
              % (c[0], c[1], c[2], media(c, 0), media(c, 1), media(c, 3) * 100, media(c, 2), media(c, 2) - s_sem_dev))
    print("   (sem detector: spellF1 medio %.4f | referencia com bola morta perfeita: %.4f - referencia, nao e limite)"
          % (s_sem_dev, np.mean([base[m][1] for m in DEV])))

    elegiveis = [c for c in combos if media(c, 0) >= PREC_MIN]
    print("\n" + "=" * 92)
    if not elegiveis:
        print("NENHUMA combinacao com precisao media >= %.2f no desenvolvimento -> DESCARTAR o detector." % PREC_MIN)
        return
    melhor = max(elegiveis, key=lambda c: media(c, 1))
    print("ESCOLHIDA NO DESENVOLVIMENTO: B=%.1f m/s, k=%.2f, T=%.1f s (precisao %.3f, recall %.3f)"
          % (melhor[0], melhor[1], melhor[2], media(melhor, 0), media(melhor, 1)))
    print("RESERVADOS (%s):" % ", ".join(RESERVA))
    passa = True
    for m in RESERVA:
        prec, rec, s_det, frac = res[m][melhor]
        ok = (prec >= PREC_MIN) and (s_det > base[m][0])
        passa &= ok
        print("   %s: precisao %.3f | recall %.3f | spellF1 %.4f vs sem detector %.4f (ref. morta perfeita %.4f) | %s"
              % (m, prec, rec, s_det, base[m][0], base[m][1], "PASSA" if ok else "NAO PASSA"))
    print("\nDECISAO PELA REGRA DECLARADA: %s"
          % (("CANDIDATO para v1.13: B=%.1f, k=%.2f, T=%.1f" % melhor) if passa else "DESCARTAR o detector"))
    print("(no nosso jogo: corte = k x mediana dos jogadores com a bola visivel, mesma conta; so age com a bola visivel)")


if __name__ == "__main__":
    main()
