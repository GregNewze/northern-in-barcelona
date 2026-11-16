"""explora_idsse.py - olha o que tem dentro de um jogo do IDSSE (via kloppy).

Igual aos nossos explora.py: NAO valida nada ainda, so confere o formato pra
depois a gente construir a validacao externa com seguranca.

Confirma:
  - fps, numero de frames, sistema de coordenadas (0..1? metros?)
  - se cada frame tem ball_owning_team (a POSSE rotulada = nosso gabarito externo)
  - se tem ball_state (bola viva/morta = o D)
  - posicao da bola e dos jogadores num frame de exemplo (com time de cada um)

Antes de rodar, instale o kloppy UMA vez:
    pip install kloppy --break-system-packages

Uso:
    python explora_idsse.py
    python explora_idsse.py --match J03WPY
"""

import argparse


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--match", default="J03WPY", help="id do jogo IDSSE (ex: J03WPY)")
    p.add_argument("--limit", type=int, default=3000, help="so os N primeiros frames (amostra)")
    a = p.parse_args()

    try:
        from kloppy import sportec
    except ImportError:
        print("Instale o kloppy primeiro:  pip install kloppy --break-system-packages")
        return

    print(f"carregando tracking do jogo {a.match} (only_alive=False pra manter bola morta)...")
    tr = sportec.load_open_tracking_data(match_id=a.match, limit=a.limit, only_alive=False)

    md = tr.metadata
    print("\n=== METADADOS ===")
    print("fps / frame_rate :", getattr(md, "frame_rate", "?"))
    print("coordenadas      :", getattr(md, "coordinate_system", "?"))
    try:
        print("pitch dimensions :", md.coordinate_system.pitch_dimensions)
    except Exception as e:
        print("pitch dimensions : (nao achei:", e, ")")
    times = getattr(md, "teams", [])
    print("times            :", [str(t) for t in times])
    print("total de frames na amostra:", len(tr.frames))

    # checa campos do frame
    f0 = tr.frames[0]
    print("\n=== CAMPOS DE UM FRAME ===")
    print("atributos:", [x for x in dir(f0) if not x.startswith("_")])

    # procura o primeiro frame com posse E bola E jogadores pra mostrar
    mostrados = 0
    com_posse = 0
    com_ballstate = 0
    for fr in tr.frames:
        bot = getattr(fr, "ball_owning_team", None)
        if bot is not None:
            com_posse += 1
        if getattr(fr, "ball_state", None) is not None:
            com_ballstate += 1

    print("\n=== GABARITO EXTERNO (o que importa) ===")
    print(f"frames com ball_owning_team: {com_posse}/{len(tr.frames)}  <- a posse rotulada")
    print(f"frames com ball_state      : {com_ballstate}/{len(tr.frames)}  <- bola viva/morta (D)")

    print("\n=== EXEMPLO DE 1 FRAME (o 500o) ===")
    fr = tr.frames[min(500, len(tr.frames) - 1)]
    print("frame_id   :", getattr(fr, "frame_id", "?"))
    print("timestamp  :", getattr(fr, "timestamp", "?"))
    print("ball_coord :", getattr(fr, "ball_coordinates", "?"))
    print("ball_owning:", getattr(fr, "ball_owning_team", "?"))
    print("ball_state :", getattr(fr, "ball_state", "?"))
    # jogadores
    pd = getattr(fr, "players_data", None) or getattr(fr, "players_coordinates", None)
    if pd:
        print("n jogadores no frame:", len(pd))
        print("exemplo de 3 jogadores (player -> time -> coord):")
        for i, (player, data) in enumerate(pd.items()):
            coord = getattr(data, "coordinates", data)
            time = getattr(player, "team", "?")
            print(f"   {player}  time={time}  coord={coord}")
            if i >= 2:
                break
    else:
        print("nao achei players_data/players_coordinates no frame")

    # tipos de evento (pode ajudar a achar set pieces no IDSSE)
    try:
        print("\n=== EVENTOS (amostra de tipos) ===")
        ev = sportec.load_open_event_data(match_id=a.match)
        tipos = {}
        for e in ev.events:
            t = type(e).__name__
            tipos[t] = tipos.get(t, 0) + 1
        for t, c in sorted(tipos.items(), key=lambda x: -x[1])[:15]:
            print(f"   {t}: {c}")
    except Exception as e:
        print("(nao carreguei eventos agora:", e, ")")

    print("\nOK. cola essa saida que eu monto a validacao adaptada ao formato real.")


if __name__ == "__main__":
    main()