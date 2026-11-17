"""Rastro de cada causa de perda da bola nas coordenadas (so agregados)."""
import os, sys
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "analises"))
import analise_sumicos as S  # noqa

of = S.preparar_caminhos(os.path.join(REPO, "oficial"))
import baseline, games  # noqa

codes = baseline.build()
n = len(codes)
gaps = S.sumicos(codes, baseline.NOBODY, games.half_video_blocks(games.GAME))
bola = S.ler_bola(os.path.join(of, "data", "tactical", "BAR-ATH_tactical_atd.txt"), n)
xy = bola * np.array([105.3, 68.0])
v = np.full(n, np.nan)
v[1:] = np.linalg.norm(np.diff(xy, axis=0), axis=1) * 25
sps = S.ler_set_pieces(os.path.join(of, "data", "tactical", "BAR-ATH_tactical_smart_tagging.xml"))
spf = [(int(s * 25), int(e * 25)) for s, e, _ in sps]
tem_sp = lambda a, b: any(a <= e + 50 and b >= s - 50 for s, e in spf)

def antes(a, k=5):
    j = slice(max(0, a - k), a)
    return xy[j], v[j]

rows = []
for a, b in gaps:
    p, vv = antes(a)
    ok = ~np.isnan(p[:, 0])
    if not ok.any():
        continue
    x, y = p[ok][-1]
    vel = np.nanmedian(vv) if np.isfinite(vv).any() else np.nan
    linha = y < 6.8 or y > 61.2 or x < 6.3 or x > 99
    rows.append(((b - a + 1) / 25, x, y, vel, linha, tem_sp(a, b), a))
R = np.array(rows, dtype=float)
dur, X, Y, VEL, LIN, SP, A0 = R.T
print(f"sumicos com posicao antes: {len(R)}")

print("\n[motion blur] velocidade da bola nos 0,2 s antes de sumir:")
for lo, hi in ((0, 2), (2, 8), (8, 20), (20, 999)):
    m = (VEL >= lo) & (VEL < hi)
    print(f"  {lo:>3}-{hi:<3} m/s: {m.sum():>4} sumicos | mediana dur {np.median(dur[m]) if m.any() else 0:5.1f}s | perto da linha {LIN[m].mean()*100 if m.any() else 0:4.0f}% | set piece {SP[m].mean()*100 if m.any() else 0:4.0f}%")
print(f"  (referencia: bola visivel em geral >8 m/s em ~36% dos frames)")

print("\n[resolucao / campo de visao] lado do campo ao sumir (y):")
for nome, m in (("lateral y<10% ", Y < 6.8), ("faixa 10-50%  ", (Y >= 6.8) & (Y < 34)),
                ("faixa 50-90%  ", (Y >= 34) & (Y <= 61.2)), ("lateral y>90% ", Y > 61.2)):
    print(f"  {nome}: {m.sum():>4} sumicos ({m.mean()*100:4.1f}%) | set piece {SP[m].mean()*100 if m.any() else 0:4.0f}%")

print("\n[iluminacao / mudanca ao longo do jogo] taxa de bola visivel por bloco de 10 min:")
vis = ~np.isnan(xy[:, 0])
for _, p0, p1 in games.half_video_blocks(games.GAME):
    for s in range(p0, p1 + 1, 25 * 600):
        e = min(s + 25 * 600, p1 + 1)
        print(f"  frames {s:>6}-{e:>6}: {vis[s:e].mean()*100:5.1f}% visivel")

print("\n[confianca baixa / falso positivo] saltos > 40 m/s:")
salto = np.flatnonzero(v > 40)
perto_gap = sum(1 for f in salto if any(a - 10 <= f <= a or b <= f <= b + 10 for a, b in gaps))
print(f"  {len(salto)} frames; {perto_gap} ({perto_gap/max(1,len(salto))*100:.0f}%) a <=0,4 s de um sumico")
rs = S.trechos(v > 40)
print(f"  em {len(rs)} rajadas; rajadas de 1 frame: {sum(1 for a,b in rs if a==b)}")

print("\n[oclusao] sumicos LONGE da linha, sem set piece, bola lenta antes:")
m = (~LIN.astype(bool)) & (~SP.astype(bool)) & (VEL < 8)
print(f"  {m.sum()} sumicos | duracao mediana {np.median(dur[m]) if m.any() else 0:.1f}s | soma {dur[m].sum():.0f}s")
m2 = (~LIN.astype(bool)) & (~SP.astype(bool))
print(f"  todos longe da linha e sem set piece: {m2.sum()} | soma {dur[m2].sum():.0f}s")
