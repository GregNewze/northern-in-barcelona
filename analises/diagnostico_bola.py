"""Diagnostico agregado da bola (so imprime contagens/porcentagens, nenhuma linha de frame).

H1: o tracker ja interpola sumicos curtos -> trechos com aceleracao ~0 (reta perfeita).
H2: quanto tempo a bola visivel esta parada / longe de todo mundo (no ar).
"""
import os, sys
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "analises"))
import analise_sumicos as S  # noqa

of = S.preparar_caminhos(os.path.join(REPO, "oficial"))
import baseline  # noqa

codes = baseline.build()
n = len(codes)
bola = S.ler_bola(os.path.join(of, "data", "tactical", "BAR-ATH_tactical_atd.txt"), n)
L, W = 105.3, 68.0
xy = bola * np.array([L, W])
vis = ~np.isnan(xy[:, 0])

# H1: segunda diferenca (m/frame^2)
d1 = np.diff(xy, axis=0)
d2 = np.diff(xy, n=2, axis=0)
a = np.linalg.norm(d2, axis=1)
v = np.linalg.norm(d1, axis=1) * 25  # m/s
ok2 = ~np.isnan(a)
print("frames com 2a diferenca valida:", int(ok2.sum()))
for thr in (1e-6, 1e-4, 1e-3, 1e-2):
    print(f"  |acel| < {thr:g} m/frame^2: {np.mean(a[ok2] < thr) * 100:5.1f}%")

lin = np.zeros(n, bool)
lin[1:-1] = ok2 & (a < 1e-3)
runs = S.trechos(lin)
dur = np.array([(b - a_ + 1) / 25 for a_, b in runs]) if runs else np.array([])
print("\ntrechos em linha reta perfeita (|acel|<1e-3):", len(runs))
for lo, hi in ((0, .2), (.2, .5), (.5, 1), (1, 2), (2, 5), (5, 1e9)):
    m = (dur >= lo) & (dur < hi)
    print(f"  {lo:>4}-{hi if hi < 1e9 else 'inf':>4}s: {m.sum():>5} trechos, {dur[m].sum():7.1f} s")
movendo = [(a_, b) for a_, b in runs if (b - a_ + 1) >= 10 and np.nanmedian(v[a_:b]) > 1.0]
print("  dos >=0,4 s, com a bola ANDANDO (>1 m/s, reta = interpolacao provavel):", len(movendo),
      f"= {sum(b - a_ + 1 for a_, b in movendo) / 25:.0f} s")

# H2: velocidade da bola visivel
vv = v[vis[1:] & vis[:-1]]
print("\nvelocidade da bola visivel:")
for lo, hi in ((0, .3), (.3, 2), (2, 8), (8, 20), (20, 40), (40, 1e9)):
    print(f"  {lo:>4}-{hi if hi < 1e9 else 'inf':>4} m/s: {np.mean((vv >= lo) & (vv < hi)) * 100:5.1f}%")

# bola parada visivel por >=2 s
parada = np.zeros(n, bool)
parada[1:] = vis[1:] & vis[:-1] & (np.nan_to_num(v, nan=99) < 0.3)
pr = [r for r in S.trechos(parada) if (r[1] - r[0] + 1) >= 50]
print(f"\nbola VISIVEL e parada (<0,3 m/s) por >=2 s: {len(pr)} trechos, {sum(b - a_ + 1 for a_, b in pr) / 25:.0f} s")
print(f"   (= {sum(b - a_ + 1 for a_, b in pr) / n * 100:.1f}% do jogo)")
