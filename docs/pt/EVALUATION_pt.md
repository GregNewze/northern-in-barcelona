# Como a nota funciona (tradução do EVALUATION.md)

> Tradução livre para a equipe Northern in Barcelona. Em caso de dúvida, vale o original em inglês.

A métrica do ranking não é acerto (accuracy) e não é F1 por foto.
Um sistema ajustado para qualquer uma dessas pode tirar ótimas notas por foto, mas gerar um número de posses completamente irreal, e ainda assim ficar mal no ranking.
Saber disso agora vale mais do que qualquer ajuste depois.

---

## Rode você mesmo

```bash
python evaluation/run_evaluation.py
```

Dá nota a todo `*.csv` dentro de `evaluation/results/`, comparando com o gabarito **público** de 5 minutos, e mostra uma tabela ordenada. Num clone novo, são os quatro baselines, então funciona antes de você escrever qualquer coisa.

`--gt` recebe um **nome**, não um caminho: `public` (o padrão, vem no repositório), `private` (o jogo inteiro, só os organizadores têm) ou o caminho para qualquer CSV no formato `frame,label`.

Um arquivo que falha na validação é **pulado, não trava tudo**: ele aparece no fim da tabela com o motivo, então um arquivo quebrado não esconde o resultado dos outros.

**Este é o arquivo que produz o resultado oficial.** Os organizadores rodam exatamente esse script contra o gabarito privado do jogo inteiro; o ranking publicado é a saída dele. Não existe uma versão mais rígida escondida.

---

## Os dois números principais

### macroF1: rótulo certo na foto certa

A média dos F1 de cada classe (`H`, `A` e `D`), considerando todas as fotos que contam. Exato foto a foto.

Fazer a média das três classes com o mesmo peso, em vez de contar fotos, importa porque bola morta é uma parte grande de todas as fotos. Uma conta de acerto simples daria a um chute "sempre bola morta" algo que parece um resultado; o macroF1 dá a ele uma nota perto do mínimo, que é a resposta honesta.

- **O mínimo não é 0.** Um chute constante ainda tira alguma coisa, então a faixa útil é mais ou menos `[0,16 ; 1,0]`, e não `[0 ; 1]`.
- **Diferenças menores que ~0,01 são ruído.** Um jogo tem muitas fotos que contam, mas bem menos trechos, e o número de trechos é o tamanho real da amostra.

### spellF1: posses certas

**É por ele que o ranking é ordenado.**

Cada posse é tratada como **um objeto só**, e não como algumas centenas de fotos. Uma posse é a maior sequência contínua de `H` ou de `A`; trechos de bola morta são paradas, não posses.

As posses previstas são pareadas uma a uma com as reais pela **sobreposição no tempo (IoU temporal)**, e o F1 desse pareamento é calculado com limites de 0,3, 0,4, 0,5, 0,6 e 0,7 e depois feita a média. É o truque do mAP do COCO, só que aplicado ao tempo em vez do espaço.

> **O que é IoU temporal:** pegue a posse prevista e a real. Divida o tempo em que as duas se sobrepõem pelo tempo total coberto pelas duas juntas. Se for 1, coincidem perfeitamente; se for 0,5, metade. Uma posse prevista só "acerta" uma real se o IoU passar do limite.

A métrica existe porque **nenhuma métrica por foto consegue representar posse**: a grande maioria das fotos fica no meio de uma posse, onde nada acontece; a bola morta ocupa uma parte bem maior das fotos do que dos trechos; e a posse mais longa do jogo conta centenas de vezes mais que a mais curta, embora um treinador conte cada uma uma vez.

A faixa vai de 0 a 1 de verdade: um chute constante tira exatamente 0.

| caso | spellF1 |
|---|---|
| perfeito | 1,0000 |
| perfeito, mas 1 foto atrasado | **1,0000** (1 foto de atraso é de graça) |
| perfeito, mas 3 / 8 fotos atrasado | 0,9818 / 0,8933 |
| perfeito, mas 1 s atrasado | 0,6539 |
| rótulos aleatórios ou qualquer chute constante | 0,0000 |

**Diferenças menores que ~0,04 são ruído** no jogo inteiro: 3 a 4 vezes a faixa do macroF1, porque a amostra real são as posses, avaliadas como acerto ou erro, e não cada foto. As distâncias entre as submissões crescem na mesma proporção, então ele não é um critério de ranking pior.

---

## Como a abstenção (X) é avaliada

`X` significa coisas diferentes para as duas métricas, e essa diferença decide onde vale a pena usá-lo.

- **`macroF1`** conta todo `X` numa foto que conta como erro, exatamente como uma resposta errada.
- **`spellF1`** nunca vê o `X`. Antes de qualquer métrica de tempo, o avaliador preenche cada `X` com o último rótulo que não é `X` no mesmo tempo (no começo de um tempo, preenche com o próximo). Quando as posses são comparadas, não sobra nenhuma abstenção.

Então, na métrica do ranking, `X` não quer dizer "sem resposta". Quer dizer **"repete a minha resposta anterior"**, e custa o que isso custar.

Consequência: ficar em silêncio durante uma oclusão **dentro** de uma posse é de graça no ranking, e mais seguro do que um chute que pode partir a posse em duas. Numa troca de posse é o contrário: **chute**, porque senão o preenchimento vai levar a sua resposta anterior por cima da troca.

---

## Veja a discordância com os próprios olhos

Os quatro baselines em `evaluation/results/` são **o mesmo algoritmo quatro vezes**: o jogador rastreado mais perto da bola, depois uma votação por maioria numa janela. A única coisa que muda é a janela.

Nota no jogo inteiro:

| baseline | macroF1 | spellF1 |
|---|---|---|
| `baseline_raw` | 0,6532 | 0,0486 |
| `baseline_smooth25` | **0,6752** | 0,1996 |
| `baseline_smooth50` | 0,6724 | **0,2433** |
| `baseline_smooth125` | 0,6356 | 0,2242 |

O `macroF1` varia 0,04 na comparação toda e escolhe o `smooth25`. O `spellF1` varia cinco vezes e escolhe o `smooth50`. Gere os arquivos de novo com `python starter/baseline.py`, avalie contra a janela pública ou acompanhe pelo `starter/03_first_submission.ipynb`.

**O `baseline_smooth50` é o piso publicado: spellF1 0,2433.** Superem.

O número de posses e a duração por trás dessas notas não são publicados, porque entregariam as contagens do próprio gabarito para vocês ajustarem em cima. As contagens da sua submissão são suas para olhar: o `validate_submission.py` mostra, e a tabela mostra ao lado das do gabarito sempre que você avalia contra um gabarito que tem.

---

## A janela pública não é um ranking

O gabarito deste repositório cobre **5 minutos, 17 posses**, e essa é toda a amostra que vocês conseguem medir. Os baselines mostram exatamente quanto isso custa:

| baseline | spellF1 **público** | spellF1 **jogo inteiro** |
|---|---|---|
| `baseline_smooth50` | 0,3256 | **0,2433** ← na verdade é melhor |
| `baseline_smooth125` | **0,4242** ← parece melhor | 0,2242 |

**Ajustar a janela de suavização pela janela pública escolhe a errada**, e isso com um único parâmetro num baseline trivial, sem nada de proposital. Aqui, uma posse perdida muda o `spellF1` em uns seis pontos.

Use a janela pública para conferir se o pipeline está **correto** (fotos alinhadas, arquivo bem formado, rótulos significando o que você acha), nunca para escolher entre duas versões dele. Quando uma diferença parecer real, rode `--bootstrap 1000` e veja se os intervalos se sobrepõem. Quase sempre vão se sobrepor.

---

## As definições estão no código

`evaluation/possession_metrics.py` é a especificação. Todo número da tabela é definido ali, em cerca de 720 linhas de numpy com a explicação nos comentários, incluindo por que macroF1 e não acerto, por que o pareamento de trocas é um a um e não "o mais próximo", e como os limites de ruído foram medidos.

Se este documento e esse arquivo discordarem, o arquivo está certo.
