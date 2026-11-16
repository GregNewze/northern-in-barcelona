"""seleciona_janela_idsse.py - escolhe a JANELA de votacao e a HISTERESE fora do nosso jogo.

Os dois parametros centrais (janela de votacao e histerese) sao escolhidos so com jogos
EXTERNOS (IDSSE, Bundesliga, gabarito real de posse e de bola viva/morta), sem usar o nosso jogo.

Desenho:
  - por jogo: nearest-player em metros -> votacao(W) -> bola morta REAL vira D nos dois lados
    (gabarito e previsao) -> histerese(H). Assim so medimos a DIVISAO DAS POSSES, que e o que
    W e H controlam; a deteccao de bola parada fica de fora da comparacao.
  - 5 jogos de DESENVOLVIMENTO escolhem a combinacao; 2 jogos RESERVADOS (nunca usados por
    nos ate agora) conferem.
  - nota absoluta NAO vale (a definicao de posse do IDSSE difere da Metrica): so a COMPARACAO
    entre combinacoes nos mesmos jogos.

REGRA DE DECISAO (declarada antes de rodar):
  1. Vence em desenvolvimento a combinacao com maior spellF1 MEDIO nos 5 jogos.
  2. Ela substitui a atual (W=75, H=1,5) SO SE tambem tiver spellF1 maior que a atual nos
     DOIS jogos reservados. Senao, fica a atual.

Uso (precisa do kloppy e do pacote oficial pro possession_metrics/baseline):
    python analises/seleciona_janela_idsse.py
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

PITCH_X, PITCH_Y = 105.0, 68.0
DEV = ["J03WPY", "J03WN1", "J03WMX", "J03WOY", "J03WQQ"]
RESERVA = ["J03WR9", "J03WOH"]
JANELAS = [0, 12, 25, 38, 50, 75, 100, 125]        # +- frames (75 = +-3 s, a atual)
HISTS = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]              # segundos (1,5 = a atual)
ATUAL = (75, 1.5)


def carregar(match, HOME, AWAY, NOBODY):
    """codes (nearest-player por frame), gabarito H/A/D, mascara de bola morta."""
    from kloppy import sportec
    tr = sportec.load_open_tracking_data(match_id=match, limit=None, only_alive=False)
    home, away = tr.metadata.teams[0], tr.metadata.teams[1]
    n = len(tr.frames)
    codes = np.full(n, NOBODY, dtype=np.int64)
    gt = np.full(n, "D", dtype="<U1")
    morto = np.zeros(n, dtype=bool)
    for i, fr in enumerate(tr.frames):
        if "DEAD" in str(getattr(fr, "ball_state", "")).upper():
            morto[i] = True
        else:
            bot = getattr(fr, "ball_owning_team", None)
            gt[i] = "H" if bot == home else ("A" if bot == away else "D")
        bc = getattr(fr, "ball_coordinates", None)
        bx, by = (getattr(bc, "x", None), getattr(bc, "y", None)) if bc is not None else (None, None)
        if bx is None or by is None:
            continue
        bx, by = bx * PITCH_X, by * PITCH_Y
        melhor, time_ = None, NOBODY
        for player, pt in (getattr(fr, "players_coordinates", None) or {}).items():
            px, py = getattr(pt, "x", None), getattr(pt, "y", None)
            if px is None or py is None:
                continue
            d = (px * PITCH_X - bx) ** 2 + (py * PITCH_Y - by) ** 2
            if melhor is None or d < melhor:
                melhor, time_ = d, (HOME if player.team == home else AWAY)
        codes[i] = time_
    gt[morto] = "D"
    return codes, gt, morto


def prever(codes, morto, W, H, baseline):
    lab = baseline.smooth(codes, W)
    lab = lab.copy()
    lab[morto] = "D"
    return V11.histerese(lab, H)


def posses(lab):
    m = np.isin(lab, ["H", "A"])
    if not m.any():
        return 0, 0.0
    runs = V11.trechos(m)
    cont, dur = 0, []
    for a, b in runs:
        seg = lab[a:b + 1]
        troca = np.flatnonzero(seg[1:] != seg[:-1])
        bordas = [a] + [a + t + 1 for t in troca] + [b + 1]
        for x, y in zip(bordas[:-1], bordas[1:]):
            cont += 1
            dur.append((y - x) / 25.0)
    return cont, float(np.mean(dur))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oficial", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "oficial"))
    a = ap.parse_args()
    V11.preparar_caminhos(a.oficial)
    import baseline
    import possession_metrics as pm

    def nota(gt, pred):
        r = pm.evaluate(pm.label_codes(gt), pm.label_codes(pred), bootstrap_n=0)
        return float(r["spell_f1_mean"]), float(r["macro_f1"])

    res = {}   # (match) -> {(W,H): (spell, macro, poss, dur)}
    info = {}
    for m in DEV + RESERVA:
        t0 = time.time()
        print("carregando %s ..." % m, flush=True)
        codes, gt, morto = carregar(m, baseline.HOME, baseline.AWAY, baseline.NOBODY)
        gp, gd = posses(gt)
        info[m] = (gp, gd, float(morto.mean() * 100))
        res[m] = {}
        for W in JANELAS:
            for H in HISTS:
                pred = prever(codes, morto, W, H, baseline)
                s, mac = nota(gt, pred)
                pp, pd_ = posses(pred)
                res[m][(W, H)] = (s, mac, pp, pd_)
        print("   %s ok (%.0f s) | gabarito: %d posses de %.1f s, %.0f%% bola morta"
              % (m, time.time() - t0, gp, gd, info[m][2]), flush=True)

    combos = [(W, H) for W in JANELAS for H in HISTS]
    media = {c: np.mean([res[m][c][0] for m in DEV]) for c in combos}
    ordem = sorted(combos, key=lambda c: -media[c])

    print("\n" + "=" * 86)
    print("DESENVOLVIMENTO (%s): spellF1 medio por combinacao" % ", ".join(DEV))
    print("=" * 86)
    print("   %-8s" % "W \\ H" + "".join("%9.1f" % h for h in HISTS))
    for W in JANELAS:
        linha = "   %-8s" % ("+-%d" % W)
        for H in HISTS:
            marca = "*" if (W, H) == ATUAL else " "
            linha += "%8.4f%s" % (media[(W, H)], marca)
        print(linha)
    print("   (* = atual)")

    print("\n   TOP 8 em desenvolvimento:")
    print("   %-12s | %-8s | %-8s | %s" % ("combinacao", "spellF1", "macroF1", "posses previstas / gabarito (media)"))
    for c in ordem[:8]:
        mac = np.mean([res[m][c][1] for m in DEV])
        razao = np.mean([res[m][c][2] / max(1, info[m][0]) for m in DEV])
        print("   W=%-3d H=%-4.1f | %.4f   | %.4f   | %.2f" % (c[0], c[1], media[c], mac, razao))
    rank_atual = ordem.index(ATUAL) + 1
    print("   atual (W=75 H=1,5): %.4f, posicao %d de %d" % (media[ATUAL], rank_atual, len(combos)))

    melhor = ordem[0]
    print("\n" + "=" * 86)
    print("RESERVADOS (%s): melhor do desenvolvimento x atual" % ", ".join(RESERVA))
    print("=" * 86)
    ganha_todos = True
    for m in RESERVA:
        sb, sa = res[m][melhor][0], res[m][ATUAL][0]
        ganha_todos &= sb > sa
        print("   %s: melhor (W=%d H=%.1f) %.4f | atual %.4f | %s"
              % (m, melhor[0], melhor[1], sb, sa, "melhor ganha" if sb > sa else "atual ganha ou empata"))
    print("\nDECISAO PELA REGRA DECLARADA: %s"
          % (("TROCAR para W=%d, H=%.1f" % melhor) if (melhor != ATUAL and ganha_todos)
             else "MANTER a atual (W=75, H=1,5)"))
    print("(lembrete: o IDSSE tem bola visivel sempre; o nosso jogo, 59% do tempo avaliado.")
    print(" W e H agem na parte com bola visivel; os sumicos continuam com as regras de D.)")


if __name__ == "__main__":
    main()