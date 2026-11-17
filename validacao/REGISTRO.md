# Registro de validação

## Parecer final (2026-11-16 01:10 -0400)

**Candidata aprovada: `src/v1_14.py`.** O CSV `northern-in-barcelona.csv` tem sha256 `2b130bff00b6a7cf74c5ed887d061f4b6f736a9e9e11b36f5f143a49327d7337`.

No fechamento independente (#27):
- 61 testes, 0 falhas, 0 erros, 0 pulados;
- CSV idêntico em duas execuções, com o sha256 acima;
- validador oficial OK (199.319 linhas);
- nenhum dado da partida, nenhum CSV e nenhum caminho pessoal entra no git;
- os pesos `src/modelo_sinais.json` (`472ce7f2…`) saem do experimento aprovado (#12, #21), cujo script tem o mesmo sha256 do pré-registro (`93536efc…`).

Nenhum parâmetro da v1.14 vem do gabarito público:
- janela e histerese foram mantidas pelo IDSSE (#9);
- preenchimento e parada não mudam nada na faixa de 0,5–4,9 s e ficaram em 3,0 s (#14, #19);
- teto de 18 s e regra da calma foram substituídos por P1/P2, aprovados nos reservados do IDSSE (#12).

Não calculei a nota pública de nenhuma versão no fechamento.

**Informativo, fora da entrega:**
- LSTM (#13, aprovado pela regra dele);
- comparação leave-one-out no dev (#24: o LSTM híbrido ganha da v1.14 por +0,067, 5/5 jogos);
- v1.13;
- diagnósticos em `analises/`.

**Decisão em aberto para o usuário: v1.15** (#26). A `src/v1_15.py` (LSTM nos frames sem bola) está pronta e é reprodutível (CSV `527eac9b…`, validador OK). Trocar para ela **contraria a declaração #19**, feita antes do resultado do LSTM. Isso é regra do nosso protocolo interno, não do hackathon. A evidência a favor (#24) foi desenhada depois de ver o resultado e usa jogos que já serviram para desenvolver. **Recomendação do validador: entregar a v1.14.** Se o usuário escolher a v1.15:
- registrar a decisão e o motivo aqui;
- dizer isso no documento técnico;
- versionar `src/modelo_lstm.pt` (já entra no commit);
- passar a usar `requirements-lstm.txt`;
- criar snapshot e testes da v1.15;
- **não** decidir pela nota pública.

**O que falta o usuário fazer:**
1. Corrigir uma frase do `docs/TECHNICAL_DOCUMENT.md` §4. O texto diz que a visibilidade "decays through each half", mas o 2º tempo não cai sempre: medi agora 78 → 59 → 67 → 34 → 54 → 72%. No 1º tempo, os blocos completos vão de 85 a 41%, e o bloco final parcial fica em 20%.
2. Opcional: apagar `saida_bola_fora.txt` e `saida_janela.txt` (ignorados), e tirar `v1_11.csv` e `alternativa_v1_15.csv` de `oficial/evaluation/results/`. Senão, `run_evaluation.py` sem argumentos pontua as versões lado a lado.
3. Revisar e commitar **como GregNewze** (identidade local do repositório). O `git add -A` só pega os 30 arquivos listados no #27. Fazer push do submódulo, se houver mudança nele, e do repositório.
4. Deixar `GregNewze/northern-in-barcelona` **público antes de 17/11** e conferir que um clone limpo com `--recurse-submodules` reproduz o sha256 acima.
5. Enviar o formulário com o CSV, o link do repositório e o documento técnico.

---

Cada entrada é escrita pelo validador seguindo `PROTOCOLO.md`. Só agregados, nunca dados por frame.

| # | Data | Experimento | Dados | Veredito | Entra no pipeline? |
|---|---|---|---|---|---|
| 1 | 2026-11-16 | Linha de base v1.12 (`src/v1_12.py`): testes, determinismo, validador oficial | BAR-ATH (só tracking + smart tagging) | **APROVADO** (item 7) | Já é o pipeline atual |
| 2 | 2026-11-16 | Parâmetros da v1.11 (preenchimento 2,6 s, janela ±75, parada 0,5 s, histerese 1,5 s) e teto `--dmaxseg` 18 s | Escolhidos no gabarito público (histórico) | **RESOLVIDO na v1.14 (ver #18/#19)**: W, H mantidos pelo IDSSE; preenchimento e parada sem efeito, fixados em 3,0 s; teto substituído | Pelos valores re-escolhidos |
| 3 | 2026-11-16 | Regra da calma da v1.12 (corte = ponto médio JOGO/PARADA no próprio jogo) | BAR-ATH sem gabarito; IDSSE J03WPY, J03WN1 (`valida_calma_idsse.py`) | **APROVADO com ressalva** (a regra não usa gabarito; herda o teto de 18 s, PENDENTE) | **Substituída na v1.14** (#19) |
| 4 | 2026-11-16 | Varredura do repositório (item 6 e item 2) | Repositório e histórico git | **APROVADO com resíduos** (atualizado na rodada 2, ver #10); falta `requirements.txt` fixado na raiz | n/a |
| 5 | 2026-11-16 | `analises/analise_sumicos.py` | BAR-ATH tracking + smart tagging | **APROVADO** | Análise (não entra no pipeline) |
| 6 | 2026-11-16 | `analises/diagnostico_bola.py` | BAR-ATH tracking | **APROVADO** (caminho fixo corrigido na rodada 2) | Análise |
| 7 | 2026-11-16 | `analises/causas_sumico.py` | BAR-ATH tracking + smart tagging | **APROVADO** (caminho fixo corrigido na rodada 2) | Análise |
| 8 | 2026-11-16 | `analises/valida_parada_visivel_idsse.py` (detector de bola parada visível) | IDSSE dev: J03WPY, J03WN1, J03WMX, J03WOY, J03WQQ; reserva: J03WR9, J03WOH | **ARQUIVADO**: nunca rodado; detector abandonado por um diagnóstico agregado (bola visível e parada ≥ 2 s em só 64 s do jogo). Nenhum resultado usado | Não |
| 9 | 2026-11-16 | `analises/seleciona_janela_idsse.py` (janela W × histerese H) | IDSSE dev: J03WPY, J03WN1, J03WMX, J03WOY, J03WQQ; reserva: J03WR9, J03WOH | **APROVADO: MANTER W=75, H=1,5** pela regra declarada (1ª execução interrompida, sem resultado aproveitado) | Sim (valores atuais) |
| 10 | 2026-11-16 | Auditoria das correções dos bloqueios do #4 e #6/#7 (git diff) | Código | **APROVADO** com 2 resíduos menores | n/a |
| 11 | 2026-11-16 | PRÉ-REGISTRO sha256 de 6 scripts (antes de qualquer resultado) | n/a | **REGISTRADO** | n/a |
| 12 | 2026-11-16 | `analises/sinais_jogadores_idsse.py` (P1 parado × rolando; P2 qual time) | IDSSE dev 5 / reserva 2 | **APROVADO** P1 e P2 pela regra declarada | Sim, na v1.14 (#19) |
| 13 | 2026-11-16 | `analises/lstm_posse_idsse.py` + `src/posse_lstm.py` (Bi-LSTM; candidato HÍBRIDO) | IDSSE dev 5 (treino) / reserva 2 (teste) | **APROVADO pela regra dele** (4/4 nos reservados); **INFORMATIVO** pela declaração #19 | Não |
| 14 | 2026-11-16 | `analises/sensibilidade_parametros.py` | BAR-ATH tracking + smart tagging, sem gabarito | **APROVADO**: preenchimento e parada sem efeito em 0,5–4,9 s; teto importa | Embasa o #19 |
| 15 | 2026-11-16 | `analises/cache_idsse.py` | IDSSE (7 jogos) | **APROVADO** | Ferramenta de análise |
| 16 | 2026-11-16 | Dependência `torch==2.5.1+cpu` em `oficial/.venv` | n/a | **APROVADO** com condições de reprodutibilidade | Só se o #13 passar |
| 17 | 2026-11-16 | Limitação: reuso dos jogos reservados J03WR9/J03WOH | n/a | **LIMITAÇÃO REGISTRADA** | n/a |
| 18 | 2026-11-16 | Resultados da rodada 3 (#9, #12, #14) conferidos contra as regras pré-registradas | Log agregado IDSSE + contagens BAR-ATH | **CONFERIDO** (as 3 regras foram seguidas; hashes iguais ao pré-registro) | n/a |
| 19 | 2026-11-16 00:35 | DECLARAÇÃO v1.14 (antes do resultado do LSTM) | n/a | **REGISTRADA**; a v1.14 em si fica PENDENTE (código não auditado, testes não rodados) | Candidata declarada |
| 20 | 2026-11-16 00:38 | DECLARAÇÃO complementar: sumíco sem bola visível no frame anterior (antes de qualquer nota) | n/a | **REGISTRADA** | Parte da v1.14 |
| 21 | 2026-11-16 | Auditoria de código da v1.14 (`src/v1_14.py`, `src/modelo_sinais.json`, `analises/exporta_sinais_idsse.py`, testes novos) | IDSSE dev (pesos); BAR-ATH sem gabarito | **APROVADO** (C1, C2 e C3 atendidas, ver #25) | **Sim, candidata** |
| 22 | 2026-11-16 | `src/v1_13.py` + `src/posse_lstm.py` (LSTM, informativo) | IDSSE (treino) | **APROVADO como informativo**; não é candidata | Não |
| 23 | 2026-11-16 | Correção dos resíduos do #10 (`v1_11.py main`, `testes.py` `cls.res`/`test_04`) | Código | **RESOLVIDO** | n/a |
| 24 | 2026-11-16 00:44 | `analises/comparacao_final_dev.py` (v1.14 × LSTM híbrido, deixando um jogo dev de fora por vez) | IDSSE dev 5 (sem os reservados) | **INFORMATIVO** (B − A = +0,0668, B ganha 5/5). Não troca a candidata | Não muda a candidata |
| 25 | 2026-11-16 00:44 | Fechamento parcial da v1.14 (C1, C2, C3) | BAR-ATH sem gabarito; IDSSE (reexportação) | **APROVADO** (números informados pelo coordenador; confirmo de forma independente no fechamento) | Candidata |
| 26 | 2026-11-16 | ALTERNATIVA PREPARADA `src/v1_15.py` (base da v1.14 + LSTM nos frames sem bola) | IDSSE (modelo); BAR-ATH sem gabarito | **NÃO É A CANDIDATA**. Usá-la contraria a declaração #19 (protocolo interno). Decisão do usuário | Só se o usuário decidir |
| 27 | 2026-11-16 01:10 | FECHAMENTO independente da v1.14 | BAR-ATH sem gabarito | **APROVADO**, com pendências de documentação e higiene para o usuário | **Entrega** |

## Entradas

### #1: Linha de base da v1.12

- **Código:** `src/v1_12.py` (importa `src/v1_11.py`), testes em `src/testes.py`, snapshot `src/snapshot_v1_12.json`.
- **Testes:** `oficial/.venv/bin/python src/testes.py` → `RESULTADO: 52 testes | 0 falhas | 0 erros | 0 pulados`, `TUDO OK` (integração ligada, porque `oficial/data/tactical/` existe). Só a linha de resultado foi lida.
- **Determinismo:** gerei duas vezes pelo `v1_12.gerar_labels`, com um script de apoio que só imprime sha256 (a saída do `main()` não foi usada, ver #4):
  - sha256 dos rótulos: `964e52e18de160a32092542dec2276532184be565492e279005ab5d01cd0cf1e` nas duas execuções, **igual ao snapshot**.
  - sha256 do CSV: `d444d78cffc4177a11e69de8a1d75df70d55ba919aa7d717fed28d4e878e2e26` nas duas execuções; `cmp` diz que são idênticos.
- **Validador oficial** (`evaluation/validate_submission.py`): `OK`, 199.319 linhas, frames 0..199318. H 34,0%, A 25,4%, D 40,6%, X 0%. Ele conta 342 posses de 13,8 s em média no arquivo inteiro; o snapshot conta 301 só nos frames avaliados, e a diferença vem dessa escolha de contagem.
- **Leitura do gabarito:** os testes `test_08`/`test_06` bloqueiam `open` no gabarito durante a geração e passaram. A geração não lê o gabarito.
- **Nota pública:** não consultei como critério. Ela fica para a checagem final da candidata.
- **Veredito:** **APROVADO** quanto ao item 7 (reprodutível, válido, testes passam). Não diz nada sobre a legitimidade dos parâmetros (ver #2).

### #2: Parâmetros herdados da v1.11 e teto de 18 s

- **Onde:** `src/v1_11.py`, função `base()` (`preencher_sumicos(..., 2.6)`, `smooth(c, 75)`, `marcar_parada(..., 0.5)`, `histerese(..., 1.5)`) e `--dmaxseg 18.0` em `gerar_labels`/`decidir_sumicos`. Também `CALMA_MAX_S = 18.0` na v1.12.
- **Origem declarada pela equipe:** esses valores saíram de uma maximização no gabarito público. Isso viola RULES.md §2, EVALUATION.md ("never to choose between two versions") e o item 2 do PROTOCOLO.
- **O que precisa acontecer:** re-escolher cada um no IDSSE (regra de decisão no docstring antes de rodar, com jogos de desenvolvimento e reservados separados) ou por argumento físico declarado antes de medir.
  - Janela ±75 e histerese 1,5 s: cobertas por `seleciona_janela_idsse.py` (#9).
  - Preenchimento 2,6 s, parada 0,5 s e teto 18 s: **ainda sem experimento**. O IDSSE tem a bola sempre visível, então esses três (que agem nos sumícos) precisam de outro desenho, por exemplo apagar a bola artificialmente no IDSSE com uma distribuição de sumícos parecida com a do nosso jogo, ou um argumento físico declarado.
- **Veredito:** **PENDENTE**. Não pode ir para a entrega final com esses valores sem re-escolha registrada aqui.

### #3: Regra da calma (v1.12)

- **Código:** `src/v1_12.py`, `referencias()` e `aplicar_calma()`.
- **Auditoria:** o corte (ponto médio entre a velocidade dos jogadores com bola visível e H/A e a velocidade em sumícos com set piece) vem só do tracking e do smart tagging do jogo, sem gabarito e sem frame fixo. É pseudo-rótulo de algoritmo, permitido pela RULES.md §1. O guarda de gabarito do `test_06` passa.
- **Dados externos:** `valida_calma_idsse.py` usou J03WPY e J03WN1 (validação cruzada entre os dois, sem reserva separada). Os reservados J03WR9/J03WOH não aparecem em nenhum script anterior, então continuam reservados.
- **Ressalvas:** `CALMA_MAX_S = 18` herda o teto PENDENTE do #2. `CALMA_MIN_S = 5` é inócuo neste jogo, porque `analise_sumicos.py` mostra que não há sumíco entre 1 e 5 s. A faixa de 5 a 8 s tem pouca prova no IDSSE (a própria equipe declara n=3).
- **Veredito:** **APROVADO com ressalva**. A regra é legítima; os limites dependem do #2.

### #4: Varredura do repositório

**Item 6 (dados e caminhos):**
- `git ls-files`: só código, docs, `.gitignore`, `.gitmodules`, snapshots JSON (sha256 + agregados) e o submódulo. **Nenhum** arquivo de `oficial/data/`, CSV de resultado, vídeo, XML ou export por frame.
- No histórico (`git log --all --name-only`), os únicos arquivos de dados ou suspeitos são os dois snapshots JSON (agregados). Limpo.
- Submódulo `oficial/`: só arquivos do repositório oficial (inclusive o gabarito público e os baselines que o próprio oficial versiona), commits só do organizador e `git status` limpo. O `.gitignore` do oficial exclui `data/*` e `evaluation/results/*.csv`.
- O `.gitignore` raiz exclui `data/`, `*.csv`, `*.txt`, `*.xml`, `*.mp4`, `*.png`, `*.gif` e `evaluation/results/`.
- Na raiz há `saida_bola_fora.txt` (138 B) e `saida_janela.txt` (22 B), ignorados pelo git (`*.txt`). Não abri. Recomendo apagar ou mover para fora do repositório, porque o padrão `*.txt` ignorado é a única proteção.
- **Caminhos pessoais:** `analises/diagnostico_bola.py:9` e `analises/causas_sumico.py:5` usam `REPO = "<caminho absoluto pessoal>"`. Os dois estão fora do git hoje. **Não podem ser versionados assim**: trocar por `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`, como os outros scripts. O docstring de `valida_parada_visivel_idsse.py` cita `~/Documentos/more-than-a-hack-2027` no exemplo de uso; trocar por `oficial` (cosmético). `cache_idsse.py` usa `~/.cache` via `expanduser`, que é portátil e aceito.

**Item 3 (frames fixos):** os únicos números de frame no código entregue são o bloco do FAQ (110808–113741, documentação oficial) e a janela pública (11185–18684), usada só para relatório. Nenhum frame tirado de olhar o jogo.

**Item 2 (gabarito público), encontrei comparações de versões pela nota pública:**
- `src/v1_12.py`, `main()`, linhas 203–210: toda execução (inclusive o comando de reprodução do README) imprime spellF1/macroF1 públicos da **v1.11 e da v1.12 lado a lado**.
- `src/testes.py`, `test_07_avaliador_oficial_v1_11_e_v1_12`: roda o `run_evaluation.py` público com as duas versões no mesmo placar.
- `src/snapshot_v1_11.json` e `src/snapshot_v1_12.json` gravam `spellF1_publico` das duas versões, e esse par já está no git.
- `analises/analisa_gaps_longos.py`, linhas 131–132: ablação "com / sem preenchimento 2,6 s" pela nota pública.
- Atenuante: nada indica que a escolha v1.11 → v1.12 tenha sido feita por essa nota, porque a nota pública da v1.12 no snapshot não é maior que a da v1.11. Mesmo assim, o PROTOCOLO pede que a nota pública só seja rodada na candidata final, sem comparar versões.
- **Correção pedida (não fiz, porque não altero o pipeline):** tirar do `main()` da v1.12 a linha da v1.11 (ou tirar a nota pública do `main()` e deixá-la só num passo de checagem final); fazer o `test_07` pontuar só a versão candidata; tirar a ablação pública do `analisa_gaps_longos.py`. Os campos `spellF1_publico` nos snapshots podem ficar como checagem de regressão, mas só para a versão candidata.

**Veredito:** **PENDENTE**. Duas correções antes da entrega: (a) caminhos fixos nos dois scripts novos, se forem versionados; (b) retirar as comparações v1.11 × v1.12 pela nota pública.

### #5: `analises/analise_sumicos.py`

- **Código:** só agregados (contagens, %, histogramas de duração e de posição por terço do campo). Não lê o gabarito. Caminho relativo (`--oficial` com padrão do próprio repositório). Lê a bola no formato correto `frame:jogadores:bola`.
- **Resultado informado (já rodado):** 150 sumícos, 43,1% dos frames sem bola, nenhum sumíco entre 1 e 5 s, 56% começam perto de linha. "Sumíco" aqui é um trecho `NOBODY` do `baseline.build`, recortado pelos blocos avaliados.
- **Veredito:** **APROVADO**. Itens 1–6 ok.

### #6: `analises/diagnostico_bola.py`

- **Código:** só imprime agregados (porcentagens de aceleração/velocidade, contagens de trechos e somas em segundos). Não lê o gabarito. Não está no git.
- **Resultado informado:** sem sinal de interpolação linear; 1,8% dos frames visíveis com a bola acima de 40 m/s.
- **Problemas:** caminho fixo `/home/<usuário>/...` (item 6). Usa comprimento de campo 105,3 m, enquanto a v1.12 usa o valor de `baseline.GAMES`; isso é só uma inconsistência menor de análise.
- **Veredito:** **APROVADO como análise** (itens 1–5 ok). **REPROVADO para versionar** até trocar o caminho fixo (item 6).

### #7: `analises/causas_sumico.py`

- **Código:** só agregados por faixa de velocidade, faixa lateral e bloco de 10 min (% visível por bloco, com os limites do bloco em frames, derivados dos blocos oficiais e não de eventos do jogo). Não lê o gabarito. Não está no git.
- **Resultado informado:** 135 de 149 sumícos começam com a bola lenta; a visibilidade cai ao longo de cada tempo (85% → 20% no 1º, 78% → 34% no 2º); saltos acima de 40 m/s em 133 rajadas. O n de 149 contra 150 do #5 é o sumíco sem posição da bola antes, que o script descarta.
- **Problemas:** caminho fixo `/home/<usuário>/...` (item 6); campo 105,3 m.
- **Veredito:** **APROVADO como análise / REPROVADO para versionar** até trocar o caminho fixo.

### #8: `analises/valida_parada_visivel_idsse.py` (não versionado)

- **O que testa:** detector de bola parada com a bola visível (bola < B m/s e jogadores < k × mediana do jogo por ≥ T s → D), com grade B ∈ {0,5; 1; 2}, k ∈ {0,6; 0,7; 0,78; 0,9}, T ∈ {2; 3; 5}.
- **Dados:** IDSSE, desenvolvimento J03WPY, J03WN1, J03WMX, J03WOY, J03WQQ; reservados J03WR9, J03WOH. Bola viva/morta real do `ball_state`. Nada do BAR-ATH é lido.
- **Regra de decisão no docstring:** (1) entre as combinações com precisão média ≥ 0,90 no desenvolvimento, vence a de maior recall médio; (2) só vira candidata se, nos dois reservados, tiver precisão ≥ 0,90 **e** spellF1 maior que sem detector. O código implementa exatamente isso (`elegiveis`, `max(... recall)` e o teste `passa` nos reservados).
- **Saída:** só agregados por jogo IDSSE (dado aberto). Pode rodar.
- **Observações:**
  1. O arquivo não está no git, então não consigo provar que a regra foi escrita antes de rodar. **Recomendo commitar o script antes de rodar**, como foi feito com o `seleciona_janela_idsse.py`.
  2. Os mesmos dois reservados também servem ao #9. Cada experimento que olha para eles gasta um pouco do valor deles como teste. Registrar quantas decisões já usaram J03WR9/J03WOH.
  3. A condição "spellF1 > sem detector" é estrita e sem margem de ruído; um ganho minúsculo passa. A regra vale como declarada, mas fica a ressalva no parecer.
  4. No IDSSE a bola está sempre visível e os sumícos do nosso jogo não existem lá. O detector só age com bola visível, o que é coerente, mas a transferência do `k` depende de a mediana de referência ser calculada igual nos dois lados, como o docstring diz.
- **Veredito:** **PENDENTE** (não rodado). O código e a regra estão conformes.

### #9: `analises/seleciona_janela_idsse.py` (janela W e histerese H)

- **Código:** versionado no commit `15c2e88` (2026-11-15 23:05), sem mudança desde então (`git diff` vazio). A execução começou em 2026-11-16 00:01. **A regra foi declarada antes de rodar**, e o git prova isso.
- **Desenho:** a bola morta real vira D nos dois lados, então só se mede a divisão das posses. Grade W ∈ {0, 12, 25, 38, 50, 75, 100, 125} × H ∈ {0; 0,5; 1; 1,5; 2; 3}, com a atual (75; 1,5) incluída.
- **Regra:** (1) vence a de maior spellF1 médio nos 5 de desenvolvimento; (2) só substitui (75; 1,5) se também ganhar da atual nos **dois** reservados; senão fica a atual. O código implementa exatamente isso.
- **Estado do log** (`<scratchpad da sessão>/janela_idsse.log`): 2 de 7 jogos prontos (J03WPY: 421 posses no gabarito, 44% de bola morta; J03WN1: 500 posses, 52% de bola morta), carregando J03WMX. O processo está vivo, mas a máquina está sem memória livre (7 GB no total, cerca de 0 disponível). Há risco de OOM; se morrer, rodar de novo com `cache_idsse.py` antes.
- **Limite do escopo:** mesmo com veredito, isso só legitima W e H. Preenchimento 2,6 s, parada 0,5 s e teto 18 s continuam PENDENTES (#2).
- **Veredito:** **PENDENTE** (não terminou). Quando terminar, conferir se a decisão impressa segue a regra e atualizar o #2.

---

## Rodada 2 (2026-11-16, ~00:17 -0400)

Restrição desta rodada, pedida pelo coordenador por causa da memória: não rodei `src/testes.py` nem nada que carregue o tracking. Só leitura de código, sha256 e `git diff`. **Os testes e o determinismo precisam rodar de novo depois destas mudanças** (snapshot e testes foram alterados), quando houver memória.

### #9 (atualização): primeira execução da seleção de janela

- O processo iniciado às 00:01 (versão do commit `15c2e88`, que lia o kloppy jogo a jogo sem liberar memória) foi **interrompido por falta de memória no 4º jogo**. Ele não produziu resultado de decisão, e **nada dele foi aproveitado**. O log parcial tinha só a contagem de posses e a % de bola morta do gabarito IDSSE de J03WPY e J03WN1, que não são resultado do experimento.
- A nova versão (#11) muda só o `carregar()`. Veja abaixo.

### #10: Auditoria das correções (git diff contra `15c2e88`)

| Bloqueio (#4/#6/#7) | Correção vista no diff | Status |
|---|---|---|
| `src/v1_12.py` `main()` imprimia nota pública da v1.11 e da v1.12 | O bloco com o gabarito público foi removido; o `main()` agora imprime só posses, duração média e D% das duas | **Resolvido** |
| `src/testes.py` `test_07` punha v1.11 e v1.12 no mesmo placar público | Virou `test_07_avaliador_oficial_roda_na_candidata`: só a v1.12, só confere o `returncode`, sem imprimir o placar | **Resolvido** |
| `metricas()` (v1.11 e v1.12) e os snapshots gravavam `spellF1_publico`/`macroF1_publico` | Campos removidos dos dois `metricas()` e dos dois JSON; o resto do snapshot (sha256 etc.) está igual | **Resolvido** |
| `analises/analisa_gaps_longos.py`: ablação pela nota pública | Leitura do gabarito e o print foram removidos; o docstring agora diz "Nada aqui lê o gabarito." | **Resolvido** |
| Caminho fixo `/home/<usuário>/...` em `diagnostico_bola.py` e `causas_sumico.py` | `REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` nos dois. `grep` por `/home/`, `~/` e `Documentos` em `src/`, `analises/` e README não acha mais nada (o exemplo do docstring do `valida_parada_visivel_idsse.py` também saiu) | **Resolvido** |

**Resíduos (não bloqueiam, mas recomendo corrigir antes da entrega):**
1. `src/testes.py`, `TestJogoReal`: o `setUpClass` (linhas 307–308) ainda calcula `cls.res` no gabarito público para a v1.11, sem uso agora. O `test_04` ainda roda o `run_evaluation.py` na **v1.11** e imprime `r.stdout[-3000:]`, ou seja, mostra a nota pública de uma versão que não é a candidata. Sugiro tirar o print (como foi feito no `test_07`) e o `cls.res`.
2. `src/v1_11.py` `main()` (linha 247 em diante) ainda imprime a nota pública da v1.11. Sozinho não compara versões, mas rodar os dois `main()` permite comparar. Sugiro remover, como na v1.12.

**Veredito:** **APROVADO**. Os bloqueios do #4 (item 2) e do item 6 dos #6/#7 foram resolvidos. A reprodutibilidade (item 7) precisa ser revalidada assim que os testes puderem rodar.

### #11: PRÉ-REGISTRO (sha256 calculado em 2026-11-16 00:17:23 -0400, antes de qualquer resultado)

Nenhum destes scripts tinha resultado quando o hash foi tirado. Qualquer mudança no arquivo depois disso invalida o pré-registro do experimento correspondente, a menos que seja registrada aqui antes de rodar.

| Arquivo | sha256 | mtime |
|---|---|---|
| `analises/sinais_jogadores_idsse.py` | `93536efcfec48ebd73bac9ade4f6d7b97b038153b4728805e61cf4063d8e5ff5` | 00:11:34 |
| `analises/lstm_posse_idsse.py` | `dc493524afd2b27e2dbef8622af63d248ba97130a78e7ac7e0ff7f841d2407e3` | 00:16:24 |
| `src/posse_lstm.py` | `9a31015e38eb4df8db8ee9b028e8ecfd1c86136106defe81fae87349450ee32c` | 00:15:43 |
| `analises/sensibilidade_parametros.py` | `8910e4dc6d9b9a45e73be5e4c567a25e9b43da1d7159dee9fa5f3ea8f59b7bb8` | 00:12:30 |
| `analises/seleciona_janela_idsse.py` | `1dbf78238bd54a3fff1ce40085a0fbd675d4ecd6a66acead7c7e9786a8faef90` | 00:13:14 |
| `analises/cache_idsse.py` | `4c2bd1ce13536664273ee3ab22b3b406832e95852cd1fb4fefc6cfe3e2cd14bf` | 00:07:07 |

Conferência do `seleciona_janela_idsse.py` pelo `git diff`: **só o `carregar()` mudou**. Docstring, regra de decisão, grade `JANELAS`/`HISTS`, `ATUAL`, `prever()`, `posses()` e `main()` estão idênticos ao commit `15c2e88`. A regra continua a declarada antes da 1ª execução. O novo `carregar()` faz a mesma conta (jogador mais perto da bola, em metros; bola morta → D; `owner` 1/2 → H/A, 0 → D) a partir do cache. Diferenças possíveis, desprezíveis: float32 no cache em vez de float64, e o empate exato de distância agora vai para o mandante.

**Recomendação:** commitar estes arquivos antes de rodar. O git é prova mais forte que o hash neste registro, que não é versionado sozinho.

### #12: `analises/sinais_jogadores_idsse.py`

- **Dados:** só o cache do IDSSE (5 dev + 2 reservados). Não lê o BAR-ATH. As durações dos sumícos simulados (`FAIXAS` = 38/31/19/44 sumícos em 5–8/8–12/12–20/20+ s) vêm do histograma agregado do `analise_sumicos.py`, ou seja, do tracking do nosso jogo **sem gabarito**. É uma estatística descritiva do dado, permitida (RULES §1: inspecionar o dado para desenhar features).
- **Saída:** só AUC e acertos agregados por jogo IDSSE. Pode rodar.
- **Regra P1 no código:** `ok1 = média AUC dev ≥ 0,75 e AUC ≥ 0,75 nos dois reservados`, conforme o docstring. Observação: a AUC de dev é dentro da amostra (a logística é treinada nos mesmos 5 jogos); o critério que vale é o dos reservados.
- **Regra P2, ambiguidade a fixar antes de rodar:** o docstring fala em "regra 'time vencedor por sinal'", mas o código decide **só pelo `COMBINADO+ult`** (logística com todos os sinais mais o último time). Os sinais individuais são impressos e há uma lista `melhores` que não é usada. **Fica registrado que o objeto de decisão do P2 é o `COMBINADO+ult`, como implementado.** Escolher depois o melhor sinal individual olhando os reservados violaria o item 2.
- **Limitações:**
  - O "último time" de referência usa o dono **real** antes da janela; no nosso jogo ele vem do nearest-player. Isso é otimista para os dois lados da comparação.
  - As janelas são sorteadas em qualquer ponto do jogo, não onde o tracker realmente perde a bola (no nosso jogo, 135 de 149 sumícos começam com a bola lenta e 56% perto de linha). A transferência do resultado para o nosso jogo não está provada.
- **Veredito:** **PENDENTE** (não rodado). Código conforme o protocolo.

### #13: `analises/lstm_posse_idsse.py` + `src/posse_lstm.py` (Bi-LSTM)

- **Dados:** treino só nos 5 jogos dev do IDSSE (6 sorteios de sumícos simulados por jogo); teste nos 2 reservados, com 2 cenários fixos (85%/15% e 70%/25%). O BAR-ATH não aparece. O simulador usa as mesmas `FAIXAS` agregadas do nosso tracking (permitido, ver #12).
- **Regra no código:** `veredito` recebe `sh - sr >= 0.02` só para os reservados × 2 cenários, e `ok = len == 4 and all`. Bate com o docstring (4 de 4, ganho ≥ 0,02 do HÍBRIDO sobre as REGRAS). O LSTM puro e o dev são informativos.
- **Determinismo:** `torch.manual_seed(2027)`, `use_deterministic_algorithms(True)`, 4 threads, `default_rng(2027)` para os sorteios e `default_rng(100+k)` para os cenários. Isso deve dar o mesmo resultado na mesma máquina; entre máquinas ou CPUs o torch não garante bit a bit (ver #16).
- **Ressalvas metodológicas (registradas antes do resultado):**
  1. **As REGRAS no IDSSE ficam sem smart tagging** (`decidir_sumicos(lab, [], ...)`) e sem a regra da calma da v1.12. No BAR-ATH, a regra do set piece é o que transforma em D boa parte dos sumícos longos. A comparação HÍBRIDO × REGRAS no IDSSE é contra uma linha de base **mais fraca que o pipeline real**, então um ganho lá superestima o ganho esperado aqui.
  2. **Antes de aplicar no BAR-ATH, declarar aqui como o HÍBRIDO convive com o smart tagging** (por exemplo: set piece → D tem prioridade sobre o LSTM, ou o LSTM recebe o set piece como sinal), sem olhar a nota pública. Essa integração não foi testada no IDSSE.
  3. O teste usa sumícos **simulados** pelo mesmo gerador do treino (só os parâmetros mudam), então mede generalização para o simulador, não para o tracker real.
  4. As REGRAS usam os parâmetros da v1.11 ainda PENDENTES (#2). Se eles mudarem por causa do #9, a comparação precisa ser refeita com os novos.
  5. Ganho mínimo de 0,02 por comparação é menor que o ruído oficial de spellF1 (~0,04 no jogo inteiro); exigir 4 de 4 compensa em parte.
- **Artefato:** o modelo é salvo em `src/modelo_lstm.pt`. O `.gitignore` não exclui `*.pt`. Ver #16.
- **Veredito:** **PENDENTE** (não rodado). Código e regra conformes; as ressalvas 1 e 2 precisam ser tratadas antes de qualquer uso no pipeline.

### #14: `analises/sensibilidade_parametros.py`

- **Código:** reconstrói o pipeline da v1.11 variando um parâmetro por vez (preenchimento, parada, teto) e conta os **frames avaliados que mudam** em relação aos valores atuais. **Não lê o gabarito**; imprime só contagens e %. Caminho relativo.
- **Leitura declarada:** "0 frames mudam numa faixa → parâmetro inerte, fixar por argumento físico; muitos mudam → precisa de escolha externa". É legítimo: mede o efeito do parâmetro, não a qualidade.
- **Cuidado (registrado antes):** a contagem não pode virar critério para "ficar perto dos valores atuais", porque os atuais vieram do gabarito público. Só vale para declarar inércia. Onde o parâmetro importar, a escolha tem que vir do IDSSE ou de argumento físico.
- **Veredito:** **APROVADO para rodar** (carrega o tracking: esperar memória). Resultado PENDENTE.

### #15: `analises/cache_idsse.py`

- Só IDSSE (kloppy `sportec.load_open_tracking_data`), salva `.npz` em `~/.cache/northern/idsse` (ou `IDSSE_CACHE`), um jogo por vez com `gc`. Não imprime dado por frame. Caminho portátil.
- Detalhe: um jogador presente nos frames mas fora de `team.players` daria `KeyError`. Seria uma falha visível, não silenciosa. Aceito.
- **Veredito:** **APROVADO**.

### #16: Dependência `torch==2.5.1+cpu`

- **Protocolo:** o torch é público, BSD-3, e roda em CPU, sem modelo pré-treinado privado. Os pesos saem de treino só no IDSSE, que é dado aberto de outros jogos. Itens 4 e 5 ok; RULES ("a public model... an open dataset") ok. A licença do IDSSE deve ser citada no documento técnico.
- **Condições para entrar no pipeline (se o #13 passar):**
  1. **O repositório não tem `requirements.txt` fixado na raiz.** O README manda instalar `oficial/requirements.txt`, que não tem kloppy nem torch. O `oficial/requirements-starter.txt` fixa `kloppy==3.18.0`, mas o venv tem **kloppy 3.19.1**. Criar `requirements.txt` na raiz (já é exceção no `.gitignore`) com numpy, `kloppy==3.19.1` e `torch==2.5.1` (com a instrução `--index-url https://download.pytorch.org/whl/cpu`).
  2. **RULES §3 (mesmo arquivo):** o treino do torch não garante bit a bit entre máquinas. Para a entrega, **versionar `src/modelo_lstm.pt`** (é derivado só do IDSSE, então pode ser publicado, com a licença do IDSSE), gravar o sha256 dele no snapshot e fazer o pipeline só **carregar** os pesos. A inferência em CPU com `use_deterministic_algorithms` deve ser checada por sha256 do CSV em duas execuções.
  3. O `testes.py` precisa de um teste que confira o sha256 do `.pt` e o determinismo da inferência.
- **Veredito:** **APROVADO** como dependência, condicionado aos 3 pontos acima.

### #17: Limitação: reuso dos jogos reservados J03WR9 e J03WOH

- Os mesmos dois reservados são usados como teste final por **4 análises**: `seleciona_janela_idsse.py` (#9), `valida_parada_visivel_idsse.py` (#8), `sinais_jogadores_idsse.py` (#12) e `lstm_posse_idsse.py` (#13). O `cache_idsse.py` só os carrega.
- Cada decisão tomada olhando os reservados gasta um pouco do valor deles como teste independente. Com 4 experimentos aceitos ou rejeitados neles, a chance de um aprovado por sorte aumenta, e decisões encadeadas (por exemplo, o LSTM comparado a regras cujos W e H foram escolhidos por um experimento que também olhou os reservados) deixam de ser independentes.
- **Medidas pedidas:**
  - Não rodar de novo nenhum desses experimentos com regra ou grade alterada depois de ver os reservados.
  - Não criar um 5º experimento nesses reservados sem registrar aqui.
  - Se houver mais jogos IDSSE disponíveis, separar um novo par reservado para a decisão final da candidata.
  - Citar esta limitação no documento técnico.

---

## Rodada 3 (2026-11-16, 00:35:07 -0400)

Fonte: `<log local da sessão>/b9sw5ssw8.output`. Só agregados: IDSSE e contagens de frames do BAR-ATH, sem gabarito. **Os sha256 dos 6 scripts às 00:35 são iguais ao pré-registro do #11.** O LSTM ainda está treinando (processo vivo, sem `src/modelo_lstm.pt`).

### #18: Resultados conferidos contra as regras pré-registradas

**#14 sensibilidade (sem gabarito, frames avaliados que mudam em relação aos valores atuais):**
- Preenchimento: 0 s → 10 frames (0,01%); de 0,5 a 4,9 s → **0 frames**.
- Parada: 0,1 s → 102 frames (0,06%); de 0,5 a 4,9 s → **0 frames**.
- Teto: 8 s 3,60% · 12 s 1,50% · 15 s 1,02% · 20 s 0,60% · 25 s 3,00% · 30 s 3,67% · 45 s 4,25% · 60 s 6,61% · sem teto 7,70% → **importa**.
- Isso é coerente com o `analise_sumicos.py`, que não acha nenhum sumíco entre 1 e 5 s. Pela leitura declarada, preenchimento e parada são inertes em 0,5–4,9 s, e o teto precisa de escolha externa ou de substituição.

**#9 janela e histerese:** o melhor do dev foi W=50, H=1,5 (spellF1 médio 0,4934); a atual, W=75, H=1,5, ficou em 0,4738, 14º de 48. Nos reservados: J03WR9 melhor 0,4837 contra atual 0,4851 (perde); J03WOH 0,5419 contra 0,5080 (ganha). A regra pede ganho nos **dois**, então **MANTER W=75, H=1,5**. Regra seguida.
- Observação: no dev a atual fica atrás da melhor por cerca de 0,02. Isso é sinal fraco de que uma janela menor talvez seja melhor, mas pela regra não muda nada, e testar de novo nos reservados não é permitido (#17).

**#12 sinais:**
- P1 (combinado): AUC média dev **0,949**, reservados **0,926** e **0,957**, todas ≥ 0,75 → **APROVADO**. Os sinais mais fortes são intensidade (dev 0,936) e sprint (0,912); `convergencia` fica abaixo de 0,5 (sinal invertido ou nulo), mas entra só pelo combinado.
- P2 (`COMBINADO+ult`, o objeto de decisão fixado no #12): acerto dev 0,841 contra 0,755 do último time (**+8,5 pp**); J03WR9 0,876 contra 0,788 (**+8,8 pp**); J03WOH 0,862 contra 0,761 (**+10,1 pp**). Todos ≥ 3 pp → **APROVADO**. Subamostra "disputa": o combinado ganha nos 7 jogos (informativo).
- Os sinais individuais (por exemplo, `espalhar` 0,853 em J03WR9) **não** podem ser escolhidos agora no lugar do combinado.

### #19: DECLARAÇÃO da v1.14, registrada em 2026-11-16 00:35:07 -0400, antes de sair o resultado do LSTM

Texto declarado pelo coordenador, registrado sem alteração de conteúdo:

1. **Preenchimento e parada fixados em 3,0 s**, por argumento físico: é o meio da faixa de 1 a 5 s, onde o jogo não tem nenhum sumíco. Como 3,0 está dentro de 0,5–4,9 s (0 frames mudam), a saída fica idêntica e o ajuste antigo no gabarito público deixa de ter efeito.
   - *Validador:* **aceito**. A inércia não depende do resto do pipeline: os dois passos só agem em sumícos com duração dentro do limiar, e não há sumícos de 1 a 5 s. Confirmar na v1.14 com um teste que troca 3,0 por 2,6 e espera sha256 igual.
2. **O teto de 18 s e a regra da calma são substituídos pelos classificadores do #12.** Em cada sumíco ≥ 5 s, sem set piece e fora do bloco do FAQ: P1 (probabilidade > 0,5) decide D ou rolando; se rolando, P2 decide o time, com "último time" = último H/A da v1.12 antes do sumíco. Sumíco com set piece continua D. Pesos: a logística treinada só nos 5 dev, com a semente do script aprovado (`SEED = 7`), exportada para `src/modelo_sinais.json`.
   - *Validador:* **aceito como desenho**, declarado antes de qualquer saída da v1.14 e sem gabarito. Com isso, o teto de 18 s (origem ilegítima) sai do pipeline e o #2 fica resolvido.
   - Condições para aprovar a v1.14:
     - (i) o `src/modelo_sinais.json` tem que ser **idêntico** aos pesos que o script aprovado produz. Exigir um teste que retreine e compare, ou o sha256 do JSON gerado por `analises/exporta_sinais_idsse.py` (novo, ainda **não auditado**).
     - (ii) os sinais no BAR-ATH têm que ser calculados pelas mesmas funções do script aprovado.
     - (iii) "probabilidade > 0,5" equivale a logit > 0 na `logistica()`, que devolve o logit; conferir no código.
     - (iv) definir o que acontece com sumícos sem bola visível no frame anterior (no treino, eles foram excluídos).
     - (v) testes, determinismo e validador oficial passando.
3. **Candidata final = v1.14.** O LSTM fica só informativo, mesmo que passe na regra dele, para não haver um 5º uso decisório dos reservados. Ele só vira candidato se a v1.14 falhar num teste de correção.
   - *Validador:* **aceito**. Isso preserva o #17. O resultado do LSTM não pode alterar o desenho da v1.14 depois de visto.
4. **Ressalvas** (registradas):
   - (a) no treino, o "último time" do P2 é o dono real; no BAR-ATH vem da v1.12 (nearest-player), então o ganho esperado é menor que os +8,8 a +10,1 pp;
   - (b) a referência de velocidade usa frames vivos no IDSSE e frames com bola visível no BAR-ATH, uma diferença de normalização entre domínios;
   - (c) sumícos com mais de 60 s ficam fora da faixa de treino (5–60 s).
   - *Validador acrescenta:*
     - (d) a aprovação do #12 foi por AUC e acerto por janela, não por spellF1 de ponta a ponta;
     - (e) as janelas do treino foram sorteadas em qualquer ponto do jogo, não onde o tracker perde a bola (#12);
     - (f) a probabilidade de D no IDSSE foi treinada com cerca de 45% de janelas paradas; no BAR-ATH a proporção pode ser outra, e o limiar 0,5 não está calibrado para ela.

**Veredito:** a declaração está **REGISTRADA** às 00:35:07, antes do resultado do LSTM. A **v1.14 fica PENDENTE**: `src/v1_13.py`, `analises/exporta_sinais_idsse.py`, `src/modelo_sinais.json` (ainda não existe) e a mudança em `src/v1_11.py` aparecem no `git status` e não foram auditados; os testes ainda não rodaram.

---

## Rodada 4 (2026-11-16, 00:38:13 -0400)

Só leitura de código e sha256; não rodei nada. O coordenador está rodando o `src/testes.py`, e o log ainda não chegou.

sha256 às 00:38:13:

| Arquivo | sha256 |
|---|---|
| `analises/sinais_jogadores_idsse.py` | `93536efcfec48ebd73bac9ade4f6d7b97b038153b4728805e61cf4063d8e5ff5` (**igual ao pré-registro #11**) |
| `src/modelo_sinais.json` | `472ce7f27949033a469961a76dc775845484c5c76c06e22eea01e7d40c59d73a` |
| `src/v1_14.py` | `d17640ab4b83e85082d202c59712d64a42422bffa92566c1502187937813eb3c` |
| `analises/exporta_sinais_idsse.py` | `e1621a265133e166aee6a394dfe2b6e3d3ce4bd26d43982203114e286ee70b77` |
| `src/v1_13.py` | `49837f81dc89f5161ddc4e12d498016280a146ed7cc829a3b680e1b7b48535d7` |
| `src/posse_lstm.py` | `9a31015e38eb4df8db8ee9b028e8ecfd1c86136106defe81fae87349450ee32c` (igual ao #11) |

### #20: DECLARAÇÃO complementar (00:38:13, antes de qualquer nota da v1.14)

Um sumíco sem bola visível no frame anterior (ou que começa no frame 0) **não** é decidido pelos jogadores. Ele fica como na base, com a continuação do `decidir_sumicos` (set piece → D; senão, o último time), o mesmo comportamento da v1.11 para sumícos não decididos. O coordenador afirma que nenhuma nota da v1.14 foi vista. **Registrado.** O código (`if a < 1 or not np.isfinite(bola[a - 1, 0]): continue`) bate com a declaração.

### #21: Auditoria de código da v1.14

**Respostas às condições do #19:**

| Condição | O que encontrei | Status |
|---|---|---|
| (i) pesos = experimento aprovado | `exporta_sinais_idsse.py` usa `default_rng(S.SEED)` e chama `S.coletar` nos 5 DEV na mesma ordem. O script aprovado coleta DEV antes de RESERVA com o mesmo `rng`, então a sequência de sorteios dos DEV é idêntica. P2 tira a coluna de disputa e acrescenta o último time igual ao script aprovado; os rótulos são os mesmos. O `assert` confere os logits exportados contra `S.logistica` nos mesmos dados. O JSON tem 7 sinais / 8 pesos no P1 e 12 sinais / 13 pesos no P2, todos finitos, com origem "IDSSE dev … seed 7". As contagens declaradas (3000 / 1648) batem com o log aprovado (5 × 600; 331+290+344+302+381). | **Aceito**, com a ressalva C1 abaixo |
| (ii) mesmas funções | `v1_14` importa `analises/sinais_jogadores_idsse.py` e usa `S.preparar` e `S.sinais`, sem cópia. A ordem das features é a mesma (`p2.pop("_disputa")`, depois `list(p2.values()) + [ult]`). | **Aceito** |
| (iii) logit > 0 ⇔ prob > 0,5 | `score()` devolve o logit `z·w + b`, e a decisão é `> 0`. O `TestModeloSinais.test_02` confere o sinal e o empate em 0. | **Aceito** |
| (iv) sumíco sem bola antes | Declarado no #20; o código bate. | **Aceito** |
| (v) 2,6/0,5 → 3,0/3,0 inerte | `TestJogoRealV14.test_03` compara as bases como arrays idênticos. | **Aceito** (falta o log) |
| (vi) testes, determinismo, validador | `test_01` validador, `test_05` determinismo com o gabarito bloqueado, `test_06` snapshot com o sha256 do modelo. Sem nenhuma nota pública. | **PENDENTE** (log) |

**Fluxo conferido contra a declaração do #19:** base com preenchimento e parada de 3,0 s, W=75, H=1,5. `decidir_sumicos(..., teto=1e9)` faz set piece → D e o resto vira continuação, ou seja, **o teto de 18 s e a regra da calma saíram**. Depois, cada sumíco com ≥ 5 s, sem set piece, fora do bloco do FAQ e com bola visível no frame anterior passa por P1 > 0 → D; senão, P2 decide o time. Por fim, o FAQ → D. Não lê o gabarito, não tem frame fixo além do FAQ. Não precisa de torch nem de kloppy: o `cache_idsse` e o `posse_lstm` importam essas libs só dentro de funções. **Conforme.**

**Observações (não bloqueiam):**
- O "último time" é o último H/A do vetor de trabalho da v1.14 antes do sumíco, não "da v1.12" como diz o #19. Na parte com bola visível os dois são iguais (mesma base); a diferença só aparece se não houver frame H/A entre dois sumícos decididos. Registro como imprecisão de texto, não de método.
- Ressalva (g), nova: no BAR-ATH os 46 slots são *tracklets*, não jogadores (o docstring do `baseline.team_of_each_track` avisa). No IDSSE um slot é um jogador. Sinais por jogador ao longo da janela (`receptor`, `saida`, `sincronia`) podem degradar quando o tracklet troca. É mais uma diferença de domínio, a somar às ressalvas (a)–(f).
- A `v1_14` importa a `v1_13` só para o `ler_bola`, acoplando a candidata ao módulo informativo do LSTM. Recomendo levar o `ler_bola` para a `v1_14` ou a `v1_11`. Isso não afeta nenhum pré-registro.
- O primeiro `test_06` vai **gravar** o snapshot e marcar o teste como pulado, sem comparar nada. A prova de que o resultado se repete entre execuções fica com o `test_05` (determinismo dentro da mesma execução). Uma segunda rodada é necessária para o snapshot ser de fato comparado.

**Condições restantes para aprovar a v1.14:**
- **C1:** o snapshot só trava o JSON atual, não prova que ele saiu do experimento aprovado. **Rodar `analises/exporta_sinais_idsse.py` de novo** (usa só o cache IDSSE, não carrega o BAR-ATH) e conferir que sai o mesmo sha256 `472ce7f2…`.
- **C2:** acrescentar um teste que confira o sha256 do `analises/sinais_jogadores_idsse.py` = `93536efc…`. Isso trava as funções que a candidata importa, e o pré-registro passa a valer também como garantia de execução.
- **C3:** o log do `testes.py` com 0 falhas e 0 erros (o pulo esperado do `test_06` aceito na primeira vez), o sha256 do CSV igual em duas execuções e o validador oficial OK.

**Resultado agregado informado (sem nota):** 58 sumícos decididos pelos jogadores (D 18 / 416 s; H 15 / 153 s; A 25 / 289 s); 295 posses avaliadas, de 14,0 s em média; D em 35,1% dos frames avaliados. Validador oficial OK. Sanidade: a proporção de D cai em relação à v1.12 (38,96%) porque a regra da calma e o teto saíram; a contagem de posses fica perto das versões anteriores (286/301). Nada fora do esperado.

**Pergunta do coordenador: o `src/` pode importar um módulo de `analises/`?**
**Pode, e recomendo manter assim.** RULES e PROTOCOLO pedem que tudo esteja no repositório público e explicado; não exigem que fique em `src/`. `analises/` é versionado, e o `sinais_jogadores_idsse.py` só depende de numpy e de `cache_idsse` (sem kloppy no import). Mover as funções quebraria a prova do pré-registro (#11) e criaria uma cópia que pode divergir do que foi aprovado. Para manter: (1) commitar o `analises/sinais_jogadores_idsse.py` sem mudança; (2) a C2 acima; (3) dizer no README e no documento técnico que a candidata usa esse módulo. Se mais tarde quiserem mover, que seja numa mudança separada, com um teste provando que os sinais são idênticos em dados sintéticos e que o sha256 do CSV não muda.

**Veredito:** **APROVADO no código**. A v1.14 fica **PENDENTE** até C1, C2 e C3.

### #22: `src/v1_13.py` + `src/posse_lstm.py` (só informativo)

- O LSTM é aplicado nos frames sem bola, exceto em sumícos com set piece, depois a histerese 1,5 s e o FAQ. Não lê o gabarito. O `posse_lstm` só importa torch dentro de funções. O `torch.load(..., weights_only=False)` carrega um arquivo próprio e local, aceito.
- **Atenção:** a v1.13 **não é** o HÍBRIDO testado no IDSSE. Lá, a base eram as regras da v1.11 sem set piece e com teto de 18 s; aqui, é a v1.12 (com calma e set piece). Se a v1.13 um dia virar candidata (só se a v1.14 falhar, #19.3), essa diferença precisa ser declarada antes, e a v1.13 precisa ser reconstruída sobre a mesma base da candidata.
- **Veredito:** **APROVADO como informativo**. Não é candidata. O `src/modelo_lstm.pt` só precisa ser versionado se ela virar candidata (#16).

### #23: Resíduos do #10

- `src/v1_11.py` `main()`: o gabarito público e a nota foram removidos (diff conferido).
- `src/testes.py`: o `cls.gt`/`cls.res` saíram do `TestJogoReal.setUpClass`, e o `test_04` só confere o `returncode`, sem imprimir o placar.
- Um `grep` por `gt_public` em `src/` e `analises/` não acha mais nada fora dos scripts IDSSE, que usam gabarito do IDSSE.
- **Veredito:** **RESOLVIDO**.

---

## Rodada 5 (2026-11-16, 00:44:12 -0400)

sha256 às 00:44:12: `analises/comparacao_final_dev.py` `75c2b51d…c31b226` (bate com o que o coordenador declarou); `src/v1_14.py` `dd69ce3d…7f97423`; `src/testes.py` `9a4ee5bc…10639`; `src/modelo_sinais.json` `472ce7f2…` (igual ao #21); `src/modelo_lstm.pt` `8992e71b…1ad2a0`; `analises/sinais_jogadores_idsse.py` `93536efc…` (igual ao #11).

### #13 (atualização): resultado do LSTM

Log: `<log local da sessão>/bk77kyjqb.output`. Só IDSSE.

- Reservados, HÍBRIDO − REGRAS: J03WR9 **+0,0450** / **+0,0573**; J03WOH **+0,1126** / **+0,0739**. As 4 comparações têm ganho ≥ 0,02, então o **HÍBRIDO é APROVADO pela regra pré-registrada**, que foi seguida.
- Informativo:
  - O LSTM puro tem spellF1 de 0,44 a 0,62 nos reservados, contra 0,35 a 0,37 das REGRAS. No desenvolvimento ele chega a 0,79–0,93 dentro da amostra.
  - A queda forte do desenvolvimento para os reservados indica que o modelo decora os jogos de treino.
  - Ressalva 1 do #13 continua: as REGRAS do IDSSE rodam sem smart tagging, mais fracas que o pipeline real.
- **Situação pela declaração #19.3: INFORMATIVO.** Ele não vira candidato porque a v1.14 passou nos testes de correção (#25).

### #24: `analises/comparacao_final_dev.py`, julgamento do desenho

- **Pré-registro:** sha256 `75c2b51d55b62aff0e5bca324cd7b33e8c579e1ccf2fffc39404fd368c31b226`, tirado às 00:44:12, antes de rodar com dados reais (o coordenador diz que só rodou com jogos falsos).
- **Código:** é um leave-one-game-out nos 5 jogos de desenvolvimento, sem os reservados. A v1.14 (P1/P2) e o LSTM são retreinados nos 4 jogos restantes de cada dobra. A regra de troca (média de B ≥ média de A + 0,02 **e** B ganha em ≥ 4 de 5 jogos) está implementada como descrita. Tecnicamente está bem feito.
- **Julgamento: NÃO é aceitável como critério para trocar a candidata.**
  1. A declaração #19 (00:35:07) não proibia só usar os reservados. Ela fixou o **critério de escolha** entre os dois: "a v1.14 é a candidata; o LSTM fica só informativo, mesmo que aprovado pela regra dele; ele só passa a candidato se a v1.14 falhar em algum teste de correção". Esse critério foi declarado **antes** do resultado do LSTM, e é ele que vale.
  2. O #24 foi criado **depois** de ver que o LSTM passou com folga (e tem gráficos de desenvolvimento muito acima das regras). Abrir um caminho de decisão novo por causa do resultado observado é exatamente o que o PROTOCOLO quer evitar: muda a regra depois de ver o dado, o que dá uma segunda chance ao método que pareceu melhor, e não à v1.14.
  3. Os 5 jogos de desenvolvimento não estão "limpos": as features, a grade e os hiperparâmetros dos dois métodos foram montados olhando esses jogos (o LSTM, inclusive, com resultados dentro da amostra já vistos). Um leave-one-game-out neles mede um pouco melhor que dentro da amostra, mas não é um teste independente.
- **Pode rodar só como INFORMATIVO** (para o documento técnico), e o resultado **não muda a candidata, seja qual for**, como o próprio coordenador ofereceu. Se no futuro houver jogos IDSSE novos, nunca usados, uma comparação pré-registrada neles seria um caminho legítimo para rever a escolha; registrar aqui antes.
- **Veredito:** **REPROVADO como critério de troca** (PROTOCOLO, item 2: regra de decisão alterada depois do resultado; contradiz o #19). **APROVADO como informativo.**

### #25: Fechamento parcial da v1.14 (C1, C2, C3)

Números informados pelo coordenador. Não reexecutei, por restrição de memória; **confirmo no fechamento final**, como pede o PROTOCOLO.

- **C3:** `src/testes.py` com 61 testes, 0 falhas, 0 erros, 0 pulados (na 2ª rodada o `test_06` já comparou com o snapshot). CSV gerado duas vezes com sha256 `2b130bff00b6a7cf74c5ed887d061f4b6f736a9e9e11b36f5f143a49327d7337` nas duas. Validador oficial OK, 199.319 linhas.
- **C1:** a reexportação dos pesos deu de novo `472ce7f2…`, o mesmo JSON.
- **C2:** conferi no código. `SHA_SINAIS_PRE_REGISTRO = "93536efc…"` (`src/testes.py:623`) e o teste está em `TestJogoRealV14`.
- **Snapshot da v1.14** (`src/snapshot_v1_14.json`, lido): sha256 dos rótulos `ebffdd97…` (é o sha da string de rótulos, diferente do sha do arquivo CSV), `sha256_modelo_sinais` `472ce7f2…`, 58 sumícos decididos (D 18 / H 15 / A 25), 295 posses, 13,973 s de duração média, D 35,128%. Sem nota pública.
- **Correção do `test_03`:** o teste antigo comparava uma etapa intermediária, em que a parada 0,5 → 3,0 muda 22 frames de sumícos < 1 s, depois absorvidos. O novo compara a **saída final** com 2,6/0,5 e com 3,0/3,0 (0 frames de diferença). Isso é coerente com o `sensibilidade_parametros.py`, que também mede a saída final. O texto do #19.1 ("nenhum frame muda") vale para a saída final, não para cada etapa. **Aceito.**
- **Desacoplamento:** o `ler_bola` agora está em `src/v1_14.py:49`, e a v1.14 não importa mais a v1.13. Conferido.
- **Veredito:** **v1.14 APROVADA como candidata**, com a confirmação independente pendente no fechamento. Os itens 1–7 do checklist estão atendidos pelo que foi auditado. Faltam: o README e o documento técnico citarem o módulo `analises/sinais_jogadores_idsse.py`, as ressalvas (a)–(g) e a limitação do #17; e o `requirements.txt` fixado (#16), mesmo sem torch se a candidata for a v1.14.

---

## Rodada final (2026-11-16, 01:10:25 -0400)

### #24 (resultado): comparação deixando um jogo dev de fora por vez, INFORMATIVA

Log local da sessão (só IDSSE). O sha256 do script na hora de rodar é `75c2b51d…`, o mesmo do pré-registro.
- Média de spellF1: A (v1.14) **0,3238**, B (LSTM híbrido) **0,3906**, B − A **+0,0668**. B ganha em **5/5** jogos e nas 10/10 medidas.
- O script imprime "TROCAR", mas pelo parecer do #24 (que contradiz o #19) **isso não muda a candidata**. O coordenador confirmou que não houve troca.
- Leitura honesta para o documento técnico: no IDSSE, com sumícos simulados e sem smart tagging, o LSTM híbrido é consistentemente melhor que a v1.14. O ganho vem de jogos já usados no desenvolvimento, com um desenho criado depois do resultado.

### #8 (atualização): arquivado

O `valida_parada_visivel_idsse.py` nunca rodou. O documento técnico diz que o detector foi abandonado porque a bola fica visível e parada por ≥ 2 s em só 64 s do jogo (diagnóstico agregado, `diagnostico_bola.py`). Nenhum resultado dele foi usado, e o uso nos reservados no #17 não aconteceu. Fica registrado.

### #26: ALTERNATIVA PREPARADA `src/v1_15.py`

- sha256 `a29d290785a757e37d056ad3558e9f1d99029a317c131f8a47f173446a822d6c`. Modelo `src/modelo_lstm.pt`, sha256 `8992e71bf46330f00bd04f8cf7bbb57fff5a9d9d7c29be0bc1beb532af1ad2a0`, treinado só nos 5 jogos dev pelo `lstm_posse_idsse.py`.
- Código lido: usa a base da v1.14, troca os frames sem bola pela classe do LSTM, mantém set piece → D e o FAQ. **Não lê o gabarito**; o `pm` só é usado no validador.
- Informado pelo coordenador: o CSV `alternativa_v1_15.csv` tem sha256 `527eac9b…` nas duas execuções e o validador deu OK. Conferi o sha256 do arquivo no disco: `527eac9bd4dd8b6b8c465db300b7369e47fe5fe07ab7055fbb10ab227c3e90d9`. Agregados: 311 posses, 12,3 s, D 39,9%.
- **Status: NÃO É A CANDIDATA.** Usá-la contraria a declaração #19, que é regra do nosso protocolo interno e não do hackathon. Pelas regras oficiais ela seria aceitável: dados de outros jogos, modelo público e reprodutível, sem gabarito. **A decisão fica com o usuário.** Recomendação do validador: v1.14. As condições para a v1.15 estão no Parecer final.

### #27: FECHAMENTO independente da v1.14

| Verificação | Resultado |
|---|---|
| `src/testes.py` | `RESULTADO: 61 testes \| 0 falhas \| 0 erros \| 0 pulados`, `TUDO OK` (só a linha de resultado foi lida) |
| Determinismo | duas gerações independentes pelo `v1_14.gerar_labels`: sha256 dos rótulos `ebffdd97…` (= snapshot), sha256 do CSV **`2b130bff00b6a7cf74c5ed887d061f4b6f736a9e9e11b36f5f143a49327d7337`** nas duas, `cmp` idêntico; igual a `oficial/evaluation/results/northern-in-barcelona.csv` e `v1_14.csv` |
| `validate_submission.py` | `OK`, 199.319 linhas, frames 0..199318; H 37,9%, A 32,0%, D 28,0%, X 2,1% no arquivo inteiro. O X só aparece fora dos frames avaliados, como garante o `test_02` do `TestJogoRealV14` |
| Nota pública | **não calculada** para nenhuma versão |
| Pré-registros | `sinais_jogadores_idsse.py` `93536efc…` e `comparacao_final_dev.py` `75c2b51d…` sem mudança; `modelo_sinais.json` `472ce7f2…` = snapshot |

**Varredura do repositório:**
- `git add -A --dry-run` pegaria 30 arquivos: código em `src/` e `analises/`, `README.md`, `.gitignore`, `docs/TECHNICAL_DOCUMENT.md`, `requirements.txt`, `requirements-lstm.txt`, `src/modelo_sinais.json` (2 KB), `src/modelo_lstm.pt` (680 KB, derivado só do IDSSE), os snapshots e `validacao/`. **Nenhum** arquivo de `oficial/data/`, CSV, XML, vídeo, imagem ou export por frame.
- Ignorados e fora do commit: `saida_bola_fora.txt` e `saida_janela.txt` (recomendo apagar).
- `oficial/evaluation/results/` (ignorado pelo submódulo) guarda `v1_11.csv`, `v1_14.csv`, `northern-in-barcelona.csv` e `alternativa_v1_15.csv`. Recomendo deixar só a entrega, para que `run_evaluation.py` sem argumentos não compare versões.
- Caminhos pessoais: `grep` por `/home/`, `~/`, `Documentos` e `erico` em `src/`, `analises/`, `docs/`, `README.md`, `requirements*.txt` e `.gitignore` não acha nada. Neste `REGISTRO.md`, troquei pelos marcadores `<scratchpad da sessão>`, `<log local da sessão>` e `<caminho absoluto pessoal>` os caminhos de log e os caminhos citados na rodada 1.
- `requirements.txt`: numpy 2.5.5, pandas 3.1.1, lxml 6.1.3, kloppy 3.19.1 (= venv, Python 3.12.3). `requirements-lstm.txt`: torch 2.5.1+cpu com o índice CPU. O `.gitignore` abre exceção para os dois. Cumpre o #16 (1).
- O `src/modelo_lstm.pt` entra versionado. Isso cumpre o #16 (2) caso a v1.15 seja escolhida; sem efeito na v1.14, que não importa torch.

**README e documento técnico:**
- `analises/sinais_jogadores_idsse.py` é citado nos dois (README, passo 5; documento §7 e §8).
- As ressalvas estão todas no documento §7: (a) último time; (b) referência de velocidade; (c) > 60 s; (d) aprovação por janela, não spellF1; (e) janelas sorteadas em qualquer ponto; (f) limiar de 0,5 não calibrado; (g) tracklets.
- O #17 (reservados reusados) está no documento §7 e no README.
- §5 descreve o #13 e o #24 como informativos, e a v1.15 como alternativa mantida por transparência. Está correto.
- O §6 afirma que o gabarito público só serviu para checagem e que os parâmetros ajustados nele foram substituídos. Isso é coerente com o #2, o #19 e o #21.
- **Imprecisão a corrigir no §4:** o texto diz que a visibilidade "decays through each half (85% → 41% … 78% → 34% …)". Rodei agora o `causas_sumico.py` (só agregados): no 1º tempo os blocos de 10 min dão 85,5 → 74,4 → 60,3 → 47,0 → 41,3%, com um bloco final parcial de 19,9%. No 2º tempo: 77,6 → 59,4 → 67,3 → 34,4 → 53,9 → 71,7%, ou seja, **não cai sempre**. Sugiro algo como "drops sharply through the first half; in the second half it falls to 34% and recovers towards the end". O mesmo vale para a frase "78% → 34%" que registrei na rodada 1 a partir do resumo recebido.

**Veredito:** **v1.14 APROVADA para entrega.** Itens 1–7 do checklist conferidos. Pendências do usuário: o parágrafo do §4, a higiene opcional, o commit e push como GregNewze, o repositório público antes de 17/11 e o formulário.
