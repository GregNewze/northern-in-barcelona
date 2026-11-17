"""sinais_jogadores_idsse.py - o que os JOGADORES dizem quando a bola some? (validado no IDSSE)

No nosso jogo a bola some 43% do tempo, quase sempre em trechos longos. Durante o sumico so
sobram os jogadores. Duas perguntas:

  P1. O jogo esta PARADO ou ROLANDO?  (rotulo D vs H/A)
  P2. Se esta rolando, QUAL TIME tem a bola?  (hoje: "continua o ultimo time")

No IDSSE a bola e quase sempre visivel e ha gabarito real (ball_state e ball_owning_team).
Simulamos o nosso problema: escondemos a bola em janelas sorteadas com as duracoes dos nossos
sumicos e so olhamos os jogadores + a ULTIMA posicao conhecida da bola.

Sinais (todos fisicos, calculados igual em qualquer jogo):
  intensidade   velocidade mediana dos jogadores / mediana do proprio jogo (relativo, porque o
                tracking do IDSSE mede velocidades maiores que o nosso)
  sprint        fracao de jogadores acima de 1,8 x a mediana do jogo
  queda         intensidade nos 2 s antes de sumir menos a dos 2 s depois (apito = todo mundo
                desacelera junto)
  agrupamento   distancia media ao centroide do proprio time (m), por time
  convergencia  distancia do jogador mais perto ate a ULTIMA posicao da bola (m)
  na_linha      ha um jogador parado a < 2 m de uma linha (lateral/escanteio/tiro de meta)
  area          jogadores dentro das duas grandes areas (escanteio / bola na area)
  P2: avanco    quanto o centroide de cada time anda na direcao do gol adversario
      espalhar  time com a bola tende a abrir (agrupamento maior)
      perto     time do jogador mais perto da ultima posicao da bola no FIM da janela

INTERACAO PERTO DA ULTIMA BOLA (P2, ideia da equipe; janelas com >= 2 jogadores a < 5 m da
ultima posicao conhecida sao a subamostra "disputa", reportada a parte):
  receptor      jogador que chega mais perto do ponto nos 2 s iniciais E desacelera (recepcao/
                dominio); vale o time dele
  saida         o receptor depois se desloca e os adversarios viram na direcao dele: time dele
  permanencia   quem fica mais tempo a < 5 m do ponto (disputa / desarme)
  superioridade jogadores a < 10 m do ponto, mandante - visitante (pressao / cobertura)
  voronoi       fracao do circulo de 15 m em volta do ponto controlada por cada time (controle
                de espaco) no fim da janela
  sincronia     alinhamento das direcoes de corrida dentro de cada time (time que ataca corre
                junto); combinado com o sentido do ataque
  contra        velocidade do centroide em direcao ao gol adversario (contra-ataque /
                reorganizacao defensiva)
  dispersao     variacao do espalhamento do time durante a janela (abrir = ganhou a bola)
  PPDA e xT ficam de fora: precisam de eventos de passe/desarme, que nao existem durante o sumico.

REGRA DE DECISAO (declarada antes de rodar):
  P1: cada sinal e medido pela AUC (D vs rolando) nos 5 jogos de DESENVOLVIMENTO.
      Uma combinacao logistica dos sinais com AUC media >= 0,75 e treinada nos 5 jogos de dev.
      Ela so e aprovada se tiver AUC >= 0,75 nos DOIS jogos reservados.
  P2: a regra "time vencedor por sinal" substitui "continua o ultimo time" SO SE acertar o
      time dono por >= 3 pontos percentuais a mais nos 5 dev (media) E nos 2 reservados.
  Nota absoluta nao interessa; o gabarito do jogo da competicao NAO e usado.

Uso (depois de analises/cache_idsse.py):
    python analises/sinais_jogadores_idsse.py
"""

import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import cache_idsse as C  # noqa: E402

FPS = 25
# duracoes (s) dos sumicos do nosso jogo, por faixa (analise_sumicos.py): peso = qtd de sumicos
FAIXAS = [((5, 8), 38), ((8, 12), 31), ((12, 20), 19), ((20, 60), 44)]
JANELAS_POR_JOGO = 600
SEED = 7


def velocidades(P):
    """(n, k) m/s, deslocamento em 0,2 s, saltos > 12 m/s descartados."""
    d = np.full(P.shape[:2], np.nan, np.float32)
    d[5:] = np.linalg.norm(P[5:] - P[:-5], axis=2) * (FPS / 5)
    d[d > 12] = np.nan
    return d


def sentido(team, period):
    """+1 se o time ataca para x crescente naquele tempo (defende o lado de x menor)."""
    out = {}
    for per in np.unique(period):
        m = period == per
        cx = np.nanmean(team[m][:, :, 0])
        out[int(per)] = 1.0 if cx < 52.5 else -1.0
    return out


def preparar(g):
    vh, va = velocidades(g["home"]), velocidades(g["away"])
    vall = np.concatenate([vh, va], axis=1)
    med_frame = np.nanmedian(vall, axis=1)
    ref = np.nanmedian(med_frame[~g["dead"]])
    g["int"] = med_frame / ref
    g["sprint"] = np.nanmean(vall > 1.8 * ref, axis=1)
    g["vall"] = vall
    g["ref"] = ref
    g["sent_h"], g["sent_a"] = sentido(g["home"], g["period"]), sentido(g["away"], g["period"])
    return g


def agrup(T):
    c = np.nanmean(T, axis=1, keepdims=True)
    return np.nanmean(np.linalg.norm(T - c, axis=2), axis=1)


def sinais(g, a, b):
    """Sinais de uma janela escondida [a, b] (so jogadores + bola em a-1)."""
    bola0 = g["ball"][a - 1]
    H, A = g["home"][a:b + 1], g["away"][a:b + 1]
    allp = np.concatenate([H, A], axis=1)
    intens = np.nanmedian(g["int"][a:b + 1])
    pre = np.nanmedian(g["int"][max(0, a - 50):a])
    pos = np.nanmedian(g["int"][a:a + 50])
    dist0 = np.nanmin(np.linalg.norm(allp - bola0, axis=2), axis=1)
    x, y = allp[..., 0], allp[..., 1]
    borda = np.minimum.reduce([y, 68 - y, x, 105 - x])
    lento = g["vall"][a:b + 1] < 0.5 * g["ref"]
    na_linha = np.nanmean(np.any((borda < 2) & lento, axis=1))
    area = (((x < 16.5) | (x > 88.5)) & (y > 13.85) & (y < 54.15)).sum(axis=1)
    ah, aa = agrup(H), agrup(A)
    p1 = dict(
        intensidade=-intens,              # sinal "parado" = intensidade baixa
        sprint=-np.nanmean(g["sprint"][a:b + 1]),
        queda=(pre - pos),
        agrupamento=-np.nanmean(np.minimum(ah, aa)),
        convergencia=np.nanmedian(dist0),
        na_linha=na_linha,
        area=np.nanmean(area),
    )
    per = int(g["period"][a])
    cx_h = np.nanmean(H[..., 0], axis=1)
    cx_a = np.nanmean(A[..., 0], axis=1)
    k = min(25, len(cx_h) - 1)
    av_h = (np.nanmean(cx_h[-k:]) - np.nanmean(cx_h[:k])) * g["sent_h"][per]
    av_a = (np.nanmean(cx_a[-k:]) - np.nanmean(cx_a[:k])) * g["sent_a"][per]
    fim = slice(max(0, len(H) - 25), len(H))
    dh = np.nanmedian(np.nanmin(np.linalg.norm(H[fim] - bola0, axis=2), axis=1))
    da = np.nanmedian(np.nanmin(np.linalg.norm(A[fim] - bola0, axis=2), axis=1))
    p2 = dict(avanco=av_h - av_a, espalhar=np.nanmean(ah - aa), perto=da - dh)  # >0 = mandante
    p2.update(interacao(g, a, b, bola0, H, A, per))
    return p1, p2


def _vel(P):
    v = np.full(P.shape, np.nan, np.float32)
    v[5:] = (P[5:] - P[:-5]) * (FPS / 5)
    return v


def interacao(g, a, b, bola0, H, A, per):
    """Sinais de interacao em volta da ultima posicao da bola. Todos: > 0 = mandante."""
    L = len(H)
    k = min(50, L)
    pre = slice(max(0, a - 10), a + k)
    Hp, Ap = g["home"][pre], g["away"][pre]
    allp = np.concatenate([Hp, Ap], axis=1)
    team = np.r_[np.ones(Hp.shape[1]), -np.ones(Ap.shape[1])]
    dist = np.linalg.norm(allp - bola0, axis=2)                     # (t, jog)
    vel = np.linalg.norm(_vel(allp), axis=2)
    out = {}
    # receptor: chega mais perto e desacelera
    dmin = np.nanmin(dist, axis=0)
    with np.errstate(all="ignore"):
        dec = np.nanmean(vel[:10], axis=0) - np.nanmean(vel[-10:], axis=0)
    cand = np.where(np.isfinite(dmin) & (dmin < 5) & (np.nan_to_num(dec) > 0), dmin, np.inf)
    j = int(np.argmin(cand)) if np.isfinite(cand).any() else -1
    out["receptor"] = float(team[j]) if j >= 0 else 0.0
    # saida: o receptor se desloca e os adversarios viram para ele
    if j >= 0 and L > 25:
        full = np.concatenate([H, A], axis=1)
        pj = full[:, j]
        des = np.nanmax(np.linalg.norm(pj - pj[0], axis=1)) if np.isfinite(pj).any() else 0
        adv = full[:, team != team[j]]
        vadv = _vel(adv)[-25:]
        alvo = pj[-25:, None, :] - adv[-25:]
        with np.errstate(all="ignore"):
            cos = np.sum(vadv * alvo, axis=2) / (np.linalg.norm(vadv, axis=2) * np.linalg.norm(alvo, axis=2))
        persegue = np.nanmean(cos) if np.isfinite(cos).any() else 0
        out["saida"] = float(team[j]) * (1.0 if (des > 5 and persegue > 0.2) else 0.0)
    else:
        out["saida"] = 0.0
    full = np.concatenate([H, A], axis=1)
    tf = team
    d_full = np.linalg.norm(full - bola0, axis=2)
    perto5 = d_full < 5
    out["permanencia"] = float(np.nansum(perto5[:, tf > 0]) - np.nansum(perto5[:, tf < 0])) / max(1, L)
    perto10 = d_full < 10
    out["superioridade"] = float(np.mean(perto10[:, tf > 0].sum(1) - perto10[:, tf < 0].sum(1)))
    # voronoi local no fim da janela
    ang = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    grid = np.concatenate([bola0 + r * np.c_[np.cos(ang), np.sin(ang)] for r in (3, 8, 15)] + [bola0[None]])
    fim = full[max(0, L - 25):]
    ctrl = []
    for fr in fim[::5]:
        ok = np.isfinite(fr[:, 0])
        if ok.sum() < 6:
            continue
        dd = np.linalg.norm(grid[:, None, :] - fr[None, ok], axis=2)
        ctrl.append(np.mean(tf[ok][np.argmin(dd, axis=1)]))
    out["voronoi"] = float(np.mean(ctrl)) if ctrl else 0.0
    # sincronia + sentido do ataque
    def sinc(T, sent):
        v = _vel(T)
        with np.errstate(all="ignore"):
            u = v / np.linalg.norm(v, axis=2, keepdims=True)
            pol = np.linalg.norm(np.nanmean(u, axis=1), axis=1)
            frente = np.nanmean(u[..., 0], axis=1) * sent
        return np.nanmean(pol * np.sign(frente))
    sh, sa = sinc(H, g["sent_h"][per]), sinc(A, g["sent_a"][per])
    out["sincronia"] = float(np.nan_to_num(sh - sa))
    def contra(T, sent):
        cx = np.nanmean(T[..., 0], axis=1)
        v = np.diff(cx) * FPS * sent
        return np.nanpercentile(v, 90) if np.isfinite(v).any() else 0
    out["contra"] = float(np.nan_to_num(contra(H, g["sent_h"][per]) - contra(A, g["sent_a"][per])))
    ah, aa = agrup(H), agrup(A)
    kk = min(25, L)
    out["dispersao"] = float(np.nan_to_num((np.nanmean(ah[-kk:]) - np.nanmean(ah[:kk])) -
                                           (np.nanmean(aa[-kk:]) - np.nanmean(aa[:kk]))))
    d0 = np.linalg.norm(allp[min(10, len(allp) - 1)] - bola0, axis=1)
    out["_disputa"] = float(np.sum(d0 < 5) >= 2)
    return out


def sortear(g, rng):
    n = len(g["dead"])
    pesos = np.array([w for _, w in FAIXAS], float)
    pesos /= pesos.sum()
    out = []
    tent = 0
    while len(out) < JANELAS_POR_JOGO and tent < 50 * JANELAS_POR_JOGO:
        tent += 1
        lo, hi = FAIXAS[rng.choice(len(FAIXAS), p=pesos)][0]
        L = int(rng.uniform(lo, hi) * FPS)
        a = int(rng.integers(60, n - L - 60))
        b = a + L - 1
        if g["period"][a] != g["period"][b] or np.isnan(g["ball"][a - 1, 0]):
            continue
        out.append((a, b))
    return out


def auc(score, y):
    s = np.asarray(score, float)
    y = np.asarray(y, bool)
    ok = np.isfinite(s)
    s, y = s[ok], y[ok]
    if y.all() or (~y).all():
        return np.nan
    r = np.argsort(np.argsort(s)) + 1
    npos = y.sum()
    return (r[y].sum() - npos * (npos + 1) / 2) / (npos * (~y).sum())


def logistica(X, y, it=3000, lr=0.1):
    mu, sd = np.nanmean(X, 0), np.nanstd(X, 0) + 1e-9
    Z = np.nan_to_num((X - mu) / sd)
    w = np.zeros(Z.shape[1] + 1)
    Zb = np.hstack([Z, np.ones((len(Z), 1))])
    for _ in range(it):
        p = 1 / (1 + np.exp(-Zb @ w))
        w -= lr * Zb.T @ (p - y) / len(y)
    return lambda Xn: np.hstack([np.nan_to_num((Xn - mu) / sd), np.ones((len(Xn), 1))]) @ w


def coletar(match, rng):
    g = preparar(C.carregar(match))
    P1, Y1, P2, Y2, ULT = [], [], [], [], []
    for a, b in sortear(g, rng):
        p1, p2 = sinais(g, a, b)
        morto = g["dead"][a:b + 1].mean() > 0.5
        P1.append(list(p1.values()))
        Y1.append(morto)
        if not morto:
            own = g["owner"][a:b + 1]
            own = own[own > 0]
            antes = g["owner"][max(0, a - 50):a]
            antes = antes[antes > 0]
            if len(own) and len(antes):
                dono = np.bincount(own, minlength=3)[1:].argmax() + 1
                disp = p2.pop("_disputa")
                P2.append(list(p2.values()) + [disp])
                Y2.append(dono)
                ULT.append(antes[-1])
    return (np.array(P1, float), np.array(Y1), np.array(P2, float), np.array(Y2), np.array(ULT),
            list(p1.keys()), [k for k in p2.keys() if k != "_disputa"])


def main():
    rng = np.random.default_rng(SEED)
    dados = {}
    for m in C.DEV + C.RESERVA:
        dados[m] = coletar(m, rng)
        print(f"{m}: {len(dados[m][1])} janelas ({dados[m][1].mean()*100:.0f}% paradas), "
              f"{len(dados[m][3])} rolando com dono", flush=True)
    nomes1, nomes2 = dados[C.DEV[0]][5], dados[C.DEV[0]][6]

    print("\nP1  PARADO x ROLANDO  - AUC por sinal (0,5 = nada; 1 = perfeito)")
    print(f"{'sinal':>14} | " + " | ".join(f"{m:>7}" for m in C.DEV) + " | media dev | " +
          " | ".join(f"{m:>7}" for m in C.RESERVA))
    for j, nome in enumerate(nomes1):
        dv = [auc(dados[m][0][:, j], dados[m][1]) for m in C.DEV]
        rs = [auc(dados[m][0][:, j], dados[m][1]) for m in C.RESERVA]
        print(f"{nome:>14} | " + " | ".join(f"{x:7.3f}" for x in dv) + f" | {np.nanmean(dv):9.3f} | " +
              " | ".join(f"{x:7.3f}" for x in rs))
    X = np.vstack([dados[m][0] for m in C.DEV])
    y = np.concatenate([dados[m][1] for m in C.DEV]).astype(float)
    f = logistica(X, y)
    dv = [auc(f(dados[m][0]), dados[m][1]) for m in C.DEV]
    rs = [auc(f(dados[m][0]), dados[m][1]) for m in C.RESERVA]
    print(f"{'COMBINADO':>14} | " + " | ".join(f"{x:7.3f}" for x in dv) + f" | {np.nanmean(dv):9.3f} | " +
          " | ".join(f"{x:7.3f}" for x in rs))
    ok1 = np.nanmean(dv) >= 0.75 and all(x >= 0.75 for x in rs)
    print(f"-> P1 {'APROVADO' if ok1 else 'REPROVADO'} pela regra declarada")

    print("\nP2  QUAL TIME TEM A BOLA (janelas rolando) - acerto")
    print(f"{'regra':>14} | " + " | ".join(f"{m:>7}" for m in C.DEV) + " | media dev | " +
          " | ".join(f"{m:>7}" for m in C.RESERVA))

    def linha(nome, pred):
        dv = [np.mean(pred(m) == dados[m][3]) for m in C.DEV]
        rs = [np.mean(pred(m) == dados[m][3]) for m in C.RESERVA]
        print(f"{nome:>14} | " + " | ".join(f"{x:7.3f}" for x in dv) + f" | {np.mean(dv):9.3f} | " +
              " | ".join(f"{x:7.3f}" for x in rs))
        return dv, rs

    for m in dados:   # tira a flag de disputa da matriz de sinais
        d = list(dados[m])
        d.append(d[2][:, -1] > 0 if len(d[2]) else np.zeros(0, bool))
        d[2] = d[2][:, :-1] if len(d[2]) else d[2]
        dados[m] = tuple(d)
    base_dv, base_rs = linha("ultimo time", lambda m: dados[m][4])
    melhores = []
    for j, nome in enumerate(nomes2):
        dv, rs = linha(nome, lambda m, j=j: np.where(dados[m][2][:, j] > 0, 1, 2))
        melhores.append((np.mean(dv), nome, dv, rs))
    X2 = np.vstack([np.column_stack([dados[m][2], np.where(dados[m][4] == 1, 1.0, -1.0)]) for m in C.DEV])
    y2 = np.concatenate([dados[m][3] for m in C.DEV]) == 1
    f2 = logistica(X2, y2.astype(float))
    dv, rs = linha("COMBINADO+ult", lambda m: np.where(
        f2(np.column_stack([dados[m][2], np.where(dados[m][4] == 1, 1.0, -1.0)])) > 0, 1, 2))
    ganho_dv = np.mean(dv) - np.mean(base_dv)
    ganho_rs = [r - b for r, b in zip(rs, base_rs)]
    ok2 = ganho_dv >= 0.03 and all(x >= 0.03 for x in ganho_rs)
    print("\n   subamostra DISPUTA (>= 2 jogadores a < 5 m da ultima bola): acerto ultimo time x combinado")
    for m in C.DEV + C.RESERVA:
        s_ = dados[m][7]
        if s_.sum() == 0:
            continue
        X_ = np.column_stack([dados[m][2], np.where(dados[m][4] == 1, 1.0, -1.0)])
        pc = np.where(f2(X_) > 0, 1, 2)
        print(f"   {m}: n={int(s_.sum()):>4} | ultimo {np.mean(dados[m][4][s_] == dados[m][3][s_]):.3f} | "
              f"combinado {np.mean(pc[s_] == dados[m][3][s_]):.3f}")
    print(f"-> P2 combinado vs ultimo time: dev {ganho_dv*100:+.1f} pp | reservados " +
          ", ".join(f"{x*100:+.1f} pp" for x in ganho_rs) + f" -> {'APROVADO' if ok2 else 'REPROVADO'}")


if __name__ == "__main__":
    main()
