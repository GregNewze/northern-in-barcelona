"""valida_calma_idsse.py - o sinal "jogadores andando = bola parada" funciona de verdade?

No nosso jogo (sem gabarito) vimos: bola visivel -> jogadores a ~1,67 m/s; sumico com set
piece -> ~0,95 m/s. Aqui medimos o MESMO sinal no IDSSE, que tem ball_state vivo/morto real:

  1. velocidade mediana dos jogadores por frame (mesma conta do analisa_gaps_longos.py:
     deslocamento em 0,2 s, saltos > 12 m/s descartados, minimo 6 jogadores);
  2. cada trecho MORTO real vs um trecho VIVO sorteado com a MESMA duracao;
  3. AUC (o quanto o sinal separa) e acerto por faixa de duracao;
  4. corte escolhido no JOGO 1 e testado no JOGO 2 (que ele nunca viu).

"Bola fora de jogo" e quase a mesma coisa em qualquer fornecedor, entao aqui a diferenca de
definicao do IDSSE pesa bem menos do que pesava na posse.

Antes: pip install kloppy
Uso:
    python src/valida_calma_idsse.py
    python src/valida_calma_idsse.py --matches J03WPY,J03WN1
"""

import argparse
import warnings

import numpy as np

FPS = 25
PITCH_X, PITCH_Y = 105.0, 68.0
PASSO = 5
MAX_MS = 12.0
MIN_JOG = 6
FAIXAS = [(2, 5), (5, 8), (8, 12), (12, 18), (18, 30), (30, 60)]


def carregar(match):
    from kloppy import sportec
    tr = sportec.load_open_tracking_data(match_id=match, limit=None, only_alive=False)
    frames = tr.frames
    n = len(frames)
    slot = {}
    for fr in frames:
        for p in (getattr(fr, "players_coordinates", None) or {}):
            slot.setdefault(p, len(slot))
    pos = np.full((n, len(slot), 2), np.nan, dtype=np.float32)
    morto = np.zeros(n, dtype=bool)
    for i, fr in enumerate(frames):
        morto[i] = "DEAD" in str(getattr(fr, "ball_state", "")).upper()
        for p, pt in (getattr(fr, "players_coordinates", None) or {}).items():
            x, y = getattr(pt, "x", None), getattr(pt, "y", None)
            if x is not None and y is not None:
                pos[i, slot[p]] = (x * PITCH_X, y * PITCH_Y)
    return pos, morto


def atividade_por_frame(pos):
    n = pos.shape[0]
    v = np.full(n, np.nan, dtype=np.float32)
    d = np.linalg.norm(pos[PASSO:] - pos[:-PASSO], axis=2) / (PASSO / FPS)
    d[d > MAX_MS] = np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(d, axis=1)
    med[np.sum(~np.isnan(d), axis=1) < MIN_JOG] = np.nan
    v[PASSO:] = med
    return v


def trechos(m):
    m = np.concatenate(([False], m, [False])).astype(np.int8)
    d = np.diff(m)
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1))


def pares(v, morto, rng):
    """Cada trecho morto (2-60 s) + um trecho vivo sorteado com a mesma duracao."""
    vivos = [(a, b) for a, b in trechos(~morto) if b - a + 1 >= 2 * FPS]
    out = []
    for a, b in trechos(morto):
        L = b - a + 1
        dur = L / FPS
        if dur < 2 or dur >= 60:
            continue
        cand = [(x, y) for x, y in vivos if y - x + 1 >= L]
        if not cand:
            continue
        x, y = cand[int(rng.integers(len(cand)))]
        s = int(rng.integers(x, y - L + 2))
        vm = v[a:b + 1]
        vv = v[s:s + L]
        vm, vv = vm[~np.isnan(vm)], vv[~np.isnan(vv)]
        if len(vm) and len(vv):
            out.append((dur, float(np.median(vm)), float(np.median(vv))))
    return out


def auc(neg, pos_):
    """P(velocidade de um trecho vivo > de um morto). 0,5 = inutil, 1 = perfeito."""
    neg, pos_ = np.asarray(neg), np.asarray(pos_)
    if len(neg) == 0 or len(pos_) == 0:
        return float("nan")
    gt = (pos_[:, None] > neg[None, :]).mean()
    eq = (pos_[:, None] == neg[None, :]).mean()
    return float(gt + 0.5 * eq)


def melhor_corte(mortos, vivos):
    u = np.unique(np.concatenate([mortos, vivos]))
    cands = (u[:-1] + u[1:]) / 2 if len(u) > 1 else u   # pontos medios: nao cola o corte num dado
    best, bt = -1, None
    for t in cands:
        ba = 0.5 * (np.mean(np.asarray(mortos) < t) + np.mean(np.asarray(vivos) >= t))
        if ba > best:
            best, bt = ba, t
    return float(bt), float(best)


def acerto(mortos, vivos, t):
    m, v = np.asarray(mortos), np.asarray(vivos)
    return float(np.mean(m < t)), float(np.mean(v >= t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matches", default="J03WPY,J03WN1")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)

    jogos = []
    for m in [x.strip() for x in a.matches.split(",") if x.strip()]:
        print("carregando %s ..." % m)
        pos, morto = carregar(m)
        v = atividade_por_frame(pos)
        jogos.append((m, v, morto, pares(v, morto, rng)))

    print("\n" + "=" * 78)
    print("1. VELOCIDADE MEDIANA DOS JOGADORES POR FRAME (compare com o nosso: jogo 1,67 | parada 0,95)")
    print("=" * 78)
    for m, v, morto, _ in jogos:
        def r(x):
            x = x[~np.isnan(x)]
            return "p25 %.2f  mediana %.2f  p75 %.2f" % tuple(np.percentile(x, [25, 50, 75]))
        print("   %s  VIVA : %s" % (m, r(v[~morto])))
        print("   %s  MORTA: %s   (%.1f%% dos frames mortos)" % (m, r(v[morto]), morto.mean() * 100))

    print("\n" + "=" * 78)
    print("2. TRECHO MORTO REAL x TRECHO VIVO DE MESMA DURACAO (mediana da velocidade no trecho)")
    print("=" * 78)
    for m, _, _, pr in jogos:
        print("   %s: %d pares" % (m, len(pr)))
        print("   %-7s | %4s | %-12s | %-12s | %s" % ("duracao", "n", "morto med", "vivo med", "AUC"))
        for lo, hi in FAIXAS:
            sel = [p for p in pr if lo <= p[0] < hi]
            if not sel:
                continue
            mm = [p[1] for p in sel]
            vv = [p[2] for p in sel]
            print("   %-7s | %4d | %-12.2f | %-12.2f | %.2f"
                  % ("%d-%ds" % (lo, hi), len(sel), np.median(mm), np.median(vv), auc(mm, vv)))
        print("   %-7s | %4d |              |              | %.2f" % ("TODOS", len(pr), auc([p[1] for p in pr], [p[2] for p in pr])))

    if len(jogos) >= 2:
        (m1, _, _, p1), (m2, _, _, p2) = jogos[0], jogos[1]
        t, ba = melhor_corte([p[1] for p in p1], [p[2] for p in p1])
        am, av = acerto([p[1] for p in p2], [p[2] for p in p2], t)
        print("\n" + "=" * 78)
        print("3. CORTE ESCOLHIDO NO %s, TESTADO NO %s (nunca visto)" % (m1, m2))
        print("=" * 78)
        print("   corte escolhido: %.2f m/s (acerto balanceado no %s: %.0f%%)" % (t, m1, ba * 100))
        print("   no %s: mortos detectados %.0f%% | vivos preservados %.0f%% | balanceado %.0f%%"
              % (m2, am * 100, av * 100, (am + av) * 50))
        for lo, hi in ((5, 18), (12, 18)):
            s2 = [p for p in p2 if lo <= p[0] < hi]
            if s2:
                am, av = acerto([p[1] for p in s2], [p[2] for p in s2], t)
                print("   so trechos de %d-%ds no %s (n=%d): mortos %.0f%% | vivos %.0f%%" % (lo, hi, m2, len(s2), am * 100, av * 100))
        am, av = acerto([p[1] for p in p2], [p[2] for p in p2], 1.31)
        print("   (referencia) corte do nosso jogo, 1,31 m/s, no %s: mortos %.0f%% | vivos %.0f%%" % (m2, am * 100, av * 100))

    print("\n" + "=" * 78)
    print("LEITURA:")
    print(" - AUC >= ~0,85 nos trechos de 5-18 s: o sinal decide bem -> vira candidato a regra.")
    print(" - AUC perto de 0,5-0,7: o sinal e fraco -> descartar e documentar.")
    print(" - Se as velocidades do IDSSE forem bem diferentes das nossas, o corte nao se transfere")
    print("   direto (tracking diferente); ai so a ORDEM do sinal vale, nao o numero.")


if __name__ == "__main__":
    main()