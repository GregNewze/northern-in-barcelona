# Northern in Barcelona

Entrega da equipe **Northern in Barcelona** para o [More Than A Hack 2027](https://github.com/metrica-sports/more-than-a-hack-2027) (Metrica Sports + FC Barcelona Innovation Hub).

O desafio: a partir do tracking automático de BAR × ATH (LaLiga 24-25), dizer quem tem a bola em cada frame do vídeo tático (`H`, `A`, `D` ou `X`, 199.319 frames a 25 fps).

## Abordagem

Regras sobre o tracking fornecido, com a parte difícil (os frames em que a bola some) decidida pelos **jogadores**. Nenhum rótulo humano do jogo da competição é usado. Os dois classificadores que decidem os sumiços foram treinados **só** em jogos abertos de outras partidas (IDSSE, Bundesliga) e apenas aplicados aqui. Detalhes em [docs/TECHNICAL_DOCUMENT.md](docs/TECHNICAL_DOCUMENT.md).

Entrega final: **`src/v1_14.py`**.

1. **Nearest-player**: o time do jogador mais perto da bola, como no baseline oficial.
2. **Sumiço curto** (≤ 3 s): se o mesmo time tinha a bola antes e depois, o sumiço vira desse time.
3. **Voto de maioria** em ±3 s e **histerese** de 1,5 s.
4. **Sumiço com *set piece*** do smart tagging (±2 s): `D`.
5. **Sumiço de ≥ 5 s sem *set piece***: os jogadores decidem.
   - **P1, parado ou rolando:** intensidade, sprint, queda de intensidade quando a bola some, agrupamento, distância à última bola, jogador parado na linha e jogadores nas áreas.
   - **P2, qual time:** avanço, espalhamento, receptor, saída com a bola, permanência, superioridade numérica, controle de espaço (Voronoi), sincronia, contra-ataque, dispersão e último time.
   - Os sinais e a regra de decisão estão em `analises/sinais_jogadores_idsse.py`, que a `v1_14` importa sem cópia. Os pesos estão em `src/modelo_sinais.json`.
6. **Intervalo**: os frames 110808–113741 são `D`, como diz o FAQ oficial.

Os 3 s do passo 2 e da parada ficam no meio da faixa de 1 a 5 s, onde o jogo não tem nenhum sumiço. Qualquer valor entre 0,5 e 4,9 s dá exatamente o mesmo arquivo (`analises/sensibilidade_parametros.py` e `test_03`).

## Validação

O gabarito público dos 5 minutos não escolhe nada: ele serve só para conferir que o pipeline está correto. Cada experimento tem a regra de decisão escrita antes de rodar, com 5 jogos IDSSE de desenvolvimento e 2 reservados. Tudo está registrado em [`validacao/REGISTRO.md`](validacao/REGISTRO.md), com o sha256 de cada script tirado antes do resultado. O checklist está em [`validacao/PROTOCOLO.md`](validacao/PROTOCOLO.md).

Limitações principais (lista completa no documento técnico):
- os sumiços do IDSSE são simulados;
- os mesmos 2 jogos reservados foram o teste final de 4 experimentos;
- no nosso jogo, os slots do tracking são trechos de trajetória, e não jogadores.

## Estrutura

```
src/
  v1_14.py             ENTREGA: pipeline final
  v1_11.py, v1_12.py   versões anteriores (base reaproveitada pela v1_14)
  modelo_sinais.json   pesos de P1/P2 (treinados só no IDSSE)
  posse_lstm.py, v1_13.py, v1_15.py, modelo_lstm.pt   experimento Bi-LSTM (informativo)
  testes.py            testes de unidade e integração (validador e avaliador oficiais)
  snapshot_*.json      sha256 e números esperados de cada versão
analises/              diagnósticos e validações (IDSSE, sensibilidade, sumiços)
validacao/             protocolo e registro de cada experimento
docs/                  documento técnico; docs/pt/ desafio e avaliação traduzidos
oficial/               submódulo: fork do repositório oficial (os dados não vão para o git)
```

## Como reproduzir

```bash
git clone --recurse-submodules https://github.com/GregNewze/northern-in-barcelona.git
cd northern-in-barcelona

# dados: seguir oficial/DATA.md e colocar os arquivos em oficial/data/tactical/
python3.12 -m venv oficial/.venv
oficial/.venv/bin/pip install -r requirements.txt

oficial/.venv/bin/python src/v1_14.py --saida northern-in-barcelona.csv
oficial/.venv/bin/python oficial/evaluation/validate_submission.py oficial/evaluation/results/northern-in-barcelona.csv
oficial/.venv/bin/python src/testes.py
```

No Windows, use `oficial\.venv\Scripts\python`. Para apontar para outra cópia do repositório oficial, passe `--oficial <pasta>` ou defina a variável `OFICIAL`.

O resultado é determinístico. O `src/testes.py` confere o sha256 dos rótulos e dos pesos contra `src/snapshot_v1_14.json`. Para refazer os pesos do zero a partir do IDSSE, veja a seção 8 do documento técnico. O experimento com LSTM pede `pip install -r requirements-lstm.txt`.

## Dados

Nenhum dado da partida está neste repositório. O `.gitignore` exclui tracking, vídeo, XML e CSVs de resultado.
