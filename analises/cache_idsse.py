"""cache_idsse.py - carrega os jogos abertos do IDSSE (kloppy) uma vez e salva arrays .npz.

IDSSE e dado aberto de OUTROS jogos (Bundesliga). Nada aqui toca no jogo da competicao.

Salva por jogo (metros, campo 105 x 68):
  ball   (n, 2)      posicao da bola
  home   (n, P, 2)   jogadores do mandante (NaN quando fora)
  away   (n, P, 2)   jogadores do visitante
  dead   (n,)        bola morta (ball_state real)
  owner  (n,)        1 = mandante, 2 = visitante, 0 = nenhum
  period (n,)        1 ou 2

Uso:
    python analises/cache_idsse.py                 # 7 jogos (5 dev + 2 reservados)
    python analises/cache_idsse.py --matches J03WPY
"""

import argparse
import gc
import os
import time

import numpy as np

PITCH_X, PITCH_Y = 105.0, 68.0
DEV = ["J03WPY", "J03WN1", "J03WMX", "J03WOY", "J03WQQ"]
RESERVA = ["J03WR9", "J03WOH"]
CACHE = os.environ.get("IDSSE_CACHE", os.path.join(os.path.expanduser("~"), ".cache", "northern", "idsse"))


def caminho(match):
    return os.path.join(CACHE, f"{match}.npz")


def salvar(match):
    from kloppy import sportec
    tr = sportec.load_open_tracking_data(match_id=match, limit=None, only_alive=False)
    home, away = tr.metadata.teams[0], tr.metadata.teams[1]
    slots = {home: {}, away: {}}
    for t in (home, away):
        for i, p in enumerate(t.players):
            slots[t][p.player_id] = i
    ph, pa = len(home.players), len(away.players)
    n = len(tr.frames)
    ball = np.full((n, 2), np.nan, np.float32)
    H = np.full((n, ph, 2), np.nan, np.float32)
    A = np.full((n, pa, 2), np.nan, np.float32)
    dead = np.zeros(n, bool)
    owner = np.zeros(n, np.int8)
    period = np.zeros(n, np.int8)
    for i, fr in enumerate(tr.frames):
        dead[i] = "DEAD" in str(getattr(fr, "ball_state", "")).upper()
        bot = getattr(fr, "ball_owning_team", None)
        owner[i] = 1 if bot == home else (2 if bot == away else 0)
        period[i] = fr.period.id if fr.period is not None else 0
        bc = fr.ball_coordinates
        if bc is not None and bc.x is not None and bc.y is not None:
            ball[i] = (bc.x * PITCH_X, bc.y * PITCH_Y)
        for player, pt in (fr.players_coordinates or {}).items():
            if pt is None or pt.x is None or pt.y is None:
                continue
            if player.team == home:
                H[i, slots[home][player.player_id]] = (pt.x * PITCH_X, pt.y * PITCH_Y)
            else:
                A[i, slots[away][player.player_id]] = (pt.x * PITCH_X, pt.y * PITCH_Y)
    os.makedirs(CACHE, exist_ok=True)
    np.savez_compressed(caminho(match), ball=ball, home=H, away=A, dead=dead, owner=owner, period=period)
    del tr
    gc.collect()
    return n


def carregar(match):
    z = np.load(caminho(match))
    return {k: z[k] for k in z.files}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--matches", default=",".join(DEV + RESERVA))
    a = p.parse_args()
    for m in a.matches.split(","):
        if os.path.exists(caminho(m)):
            print(f"{m}: ja em cache")
            continue
        t = time.time()
        n = salvar(m)
        print(f"{m}: {n} frames salvos ({time.time() - t:.0f} s)", flush=True)


if __name__ == "__main__":
    main()
