# O desafio (tradução do CHALLENGE.md)

> Tradução livre para a equipe Northern in Barcelona. Em caso de dúvida, vale o original em inglês.

## A tarefa

Dada uma partida inteira de futebol (dois vídeos, tracking automático com a bola, marcação tática automática e homografia), produzir **um rótulo para cada foto (frame)**, dizendo qual time está com a posse ou que a bola não está em jogo.

199.319 fotos. 25 fotos por segundo. Cerca de 2h15 de vídeo, das quais uns 106 minutos de jogo (158.857 fotos) contam para a nota.

Esse é o problema inteiro da Fase 1. O arquivo de resposta é avaliado diretamente, mas vocês também entregam o código e um documento técnico explicando como implementaram a proposta.

---

## Os quatro rótulos

| rótulo | significado |
|---|---|
| `H` | time da **casa** (Barça) com a posse, bola em jogo |
| `A` | time **visitante** (Athletic) com a posse, bola em jogo |
| `D` | **bola morta**: a bola não está em jogo |
| `X` | **sem resposta**: o sistema prefere não chutar, ou a foto não tem gabarito |

**`X` é uma opção real, não é pegadinha.** Fotos que o gabarito não cobre (antes do início, intervalo, depois do apito final) nunca contam, então um `X` ali não custa nada.

Nas fotos que contam, as duas métricas tratam o `X` de forma diferente, e vale saber disso antes de planejar em cima dele. O `macroF1` conta um `X` como erro, igual a uma resposta errada. O `spellF1` (a métrica do ranking) nunca vê o `X`: antes de comparar as posses, o avaliador preenche cada `X` com o último rótulo que você deu naquele tempo. Então, no ranking, um `X` custa o mesmo que repetir a resposta anterior: **nada no meio de uma posse, muito numa troca de posse**, porque o rótulo antigo "vaza" para o novo estado. O EVALUATION.md mostra o custo medido de cada caso.

Para que ele serve de verdade: um sistema que sabe que perdeu a bola pode dizer isso, em vez de inventar um rótulo, e o avaliador trata um buraco dentro de uma posse real como buraco, e não como duas posses com uma troca no meio.

**Não é pedido o "dono" da bola morta.** O tracking indica um time mesmo com a bola fora de jogo (quem vai repor, ou quem tocou por último), mas o gabarito descarta isso, porque descobrir quem "é dono" de uma bola morta é outro problema, bem mais ambíguo. Bola morta é sempre `D`.

---

## Regras de posse

### A definição operacional

Posse não é um conceito perfeitamente preciso, e alguns casos podem ser interpretados de mais de um jeito. Vocês não precisam adivinhar como eles são resolvidos: os **5 minutos de gabarito público** são a referência.

**Bola em jogo: a parte sem ambiguidade.** Quem decide se a bola está em jogo é o árbitro. Enquanto ela está, **um dos dois times sempre tem a posse**: não existe estado neutro. Em bola solta (uma dividida, uma bola correndo livre depois de um carrinho), **o time que tinha a posse continua com ela**.

**Toda reposição tem um dono claro.** Sempre que o jogo recomeça depois de uma parada (saída de bola, lateral, escanteio, tiro de meta, falta), um time está claramente com a posse. Então o verdadeiro desafio não é dar a posse foto a foto, e sim **detectar quando ela muda**.

**Quando a posse muda.** A posse passa para o outro time quando um jogador dele fica com a bola **sob controle**. Decidir o que é "controle" é onde está a ambiguidade: só com os dados, nem sempre é fácil separar uma recepção dominada de um rebote.

**Não** são trocas de posse:

- um único toque na bola sem controle;
- um passe desviado, mas não interceptado;
- uma disputa aérea ganha, sem que a bola seja dominada depois.

Além disso, os organizadores incentivam vocês a explorar e propor os próprios critérios de "controle" e medir como eles se comparam. O documento técnico é o lugar para explicar o critério escolhido.

**O gabarito público é a referência.** Ele aplica essas regras foto a foto em 17 posses. Se a sua leitura dos dados discordar dele, o gabarito está certo, e avisar os organizadores sobre a discordância é útil.

### O que já está decidido

- **Três estados, não mais.** Toda foto que conta é `H`, `A` ou `D`. No gabarito não existe "disputada", "transição" nem "desconhecido".
- **Uma posse é a maior sequência contínua de um time com a bola em jogo.** `H H H A A` são duas posses. `H H D D H H` são duas posses com uma parada no meio, e não uma. Essa é a definição em que a métrica do ranking se baseia, então vale fixar bem.
- **Bola morta é parada, nunca posse.**
- **O gabarito foi gerado a partir do tracking corrigido**, e não por uma pessoa assistindo ao vídeo nem a partir de dados de eventos. A geração é mecânica: a foto é `D` onde o tracking corrigido marca a bola como morta, e nas outras recebe o time que o tracking indica como dono. Nada é suavizado, interpolado ou ajustado à mão depois.

  Então a pergunta que importa não é *como* os rótulos foram calculados, e sim o que o tracking corrigido entende por "morta" e por "dono", que é o que a definição acima descreve.

---

## Escopo: o que este desafio não é

**Não** é um problema de rastreamento de vários objetos e **não** é reconstrução do estado do jogo.

O tracking, as marcações e a homografia são entregues para que ninguém precise reconstruir detecção, reidentificação e calibração de câmera antes de chegar à pergunta de verdade: *o que a geometria de 22 jogadores e uma bola diz sobre quem está no controle?*

Tudo o que é entregue é **automático, não corrigido**. O tracking tem buracos, trilhas quebradas e troca de identidade, não traz quem é cada jogador, e **a bola está ausente em 41% das fotos que contam**. As marcações automáticas (Smart Tagging) também são inferidas. Lidar com esse ruído faz parte do problema, não é um obstáculo a ele (veja o DATA.md).

Melhorar os dados entregues, ou substituí-los pela sua própria detecção e tracking, é totalmente permitido. Eles são um ponto de partida, não uma restrição.

---

## O que pode ser usado

**Qualquer método**, desde que os organizadores consigam acessá-lo e inspecioná-lo e que o documento técnico o explique. Qualquer linguagem, framework, modelo ou dado externo; LLMs comerciais ou abertos.

**O que não pode é anotar os dados à mão**: os rótulos precisam sair de um algoritmo. Regras completas no RULES.md.

---

## Entregas e nota

Três coisas, por um único formulário: o arquivo de posse, um repositório de código público e um documento técnico curto (veja o SUBMISSION.md).

A nota decide o ranking; o repositório e o documento são o que dá sentido a ela. O ranking é pelo **`spellF1`**, com o **`macroF1`** ao lado como primeiro critério de desempate. Os dois discordam com frequência, de propósito, e entender por que é a maior parte do trabalho. O EVALUATION.md mostra isso com um baseline que vocês podem rodar.
