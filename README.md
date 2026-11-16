# Northern in Barcelona

Entrega da equipe **Northern in Barcelona** para o [More Than A Hack 2027](https://github.com/metrica-sports/more-than-a-hack-2027) (Metrica Sports + FC Barcelona Innovation Hub).

O desafio: a partir do tracking automático de BAR × ATH (LaLiga 24-25), dizer quem tem a bola em cada frame do vídeo tático (`H`, `A`, `D` ou `X`, 199.319 frames a 25 fps).

## Abordagem

Método clássico, sem aprendizado e sem rótulos humanos do jogo da competição. Ele usa o tracking (`*_atd.txt`) e o smart tagging (`*_smart_tagging.xml`) fornecidos.

1. **Nearest-player**: o time do jogador mais perto da bola, como no baseline oficial.
2. **Sumiço curto da bola**: se o mesmo time tinha a bola antes e depois, o sumiço vira desse time.
3. **Voto de maioria** numa janela de ±3 s.
4. **Histerese**: posses curtas demais para serem reais são absorvidas.
5. **Sumiços longos**:
   - Se coincidem com um *set piece* do smart tagging, viram `D`.
   - Se duram ≥ 18 s, viram `D`.
   - Se forem calmos (jogadores lentos), viram `D`. O corte de velocidade vem do próprio jogo, sem gabarito (`src/v1_12.py`).
   - Senão, a posse continua com o último time.
6. **Intervalo**: os frames 110808–113741 são `D`, como diz o FAQ oficial.

Dados externos: jogos abertos do IDSSE (Bundesliga, via `kloppy`), usados só para validar regras e parâmetros (`analises/*idsse*.py`).

## Estrutura

```
src/
  v1_11.py          pipeline base
  v1_12.py          v1_11 + regra da calma (bola parada sem set piece)
  testes.py         testes de unidade e de integração com o avaliador oficial
  snapshot_*.json   sha256 e números esperados de cada versão
analises/           validações (sumiços, posses, IDSSE)
docs/pt/            desafio e avaliação traduzidos
oficial/            submódulo: fork do repositório oficial (os dados não vão para o git)
```

## Como reproduzir

```bash
git clone --recurse-submodules https://github.com/GregNewze/northern-in-barcelona.git
cd northern-in-barcelona

# dados: seguir oficial/DATA.md e colocar os arquivos em oficial/data/tactical/
python -m venv oficial/.venv
oficial/.venv/bin/pip install -r oficial/requirements.txt

oficial/.venv/bin/python src/v1_12.py --saida northern-in-barcelona.csv
oficial/.venv/bin/python oficial/evaluation/validate_submission.py oficial/evaluation/results/northern-in-barcelona.csv
oficial/.venv/bin/python src/testes.py
```

No Windows, use `oficial\.venv\Scripts\python`. Para apontar para outra cópia do repositório oficial, passe `--oficial <pasta>` ou defina a variável `OFICIAL`.

O resultado é determinístico. O `src/testes.py` confere o sha256 dos rótulos gerados contra `src/snapshot_v1_12.json`.

## Dados

Nenhum dado da partida está neste repositório. O `.gitignore` exclui tracking, vídeo, XML e CSVs de resultado.
