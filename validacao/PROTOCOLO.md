# Protocolo do validador

O validador é o último a falar sobre qualquer mudança. Nada entra no pipeline final sem passar
por ele e sem uma entrada no `REGISTRO.md`.

## Fontes das regras

`oficial/RULES.md`, `oficial/FAQ.md`, `oficial/EVALUATION.md` e `oficial/OVERVIEW.md`. Em caso
de dúvida, vale o texto oficial, não este resumo.

## Checklist (toda mudança)

1. **Dados da partida não aparecem em nenhum LLM em nuvem.** (FAQ, Termos e Condições)
   - Nenhum script imprime linhas de frame, coordenadas de frames específicos ou trechos
     do tracking, do vídeo, do smart tagging ou do gabarito.
   - Só podem ser vistos: contagens, porcentagens, medianas, histogramas, passou/falhou, sha256.
   - O validador também não abre esses arquivos com cat/head/Read.
2. **O gabarito público não escolhe nada.** (EVALUATION.md, RULES.md §2)
   - Parâmetros e escolhas entre versões vêm de jogos externos (IDSSE) ou de argumento
     físico declarado antes de medir.
   - A nota pública só pode ser rodada como checagem de que o pipeline está correto, e só
     da versão candidata final. Nunca comparar duas versões por ela.
   - Toda regra de decisão de uma análise no IDSSE fica escrita no docstring ANTES de rodar,
     com jogos de desenvolvimento e jogos reservados separados.
3. **Nada feito à mão sobre a partida.** Nenhum rótulo, correção de tracking ou frame
   escrito no código a partir de olhar o jogo. Só são aceitos frames que vêm da documentação
   oficial (ex.: intervalo do FAQ).
4. **Nenhum dado humano sobre a partida** (eventos, Opta, StatsBomb, tracking corrigido).
   Dados de outros jogos são permitidos.
5. **Nenhum modelo ou dado privado.** Tudo que é usado precisa estar disponível pra quem
   reproduzir.
6. **Repositório limpo.** Nada de `oficial/data/`, CSV de resultado, vídeo, XML do jogo ou
   export por frame no git. Sem caminhos pessoais (`/home/...`) no código entregue.
7. **Reprodutível.** O CSV sai igual em duas execuções (sha256), passa no
   `validate_submission.py` e os testes do `src/testes.py` passam.

## Para cada experimento

O validador registra no `REGISTRO.md`:

- o que foi testado e onde está o código;
- os dados usados (IDSSE: quais jogos de desenvolvimento e quais reservados);
- a regra de decisão declarada e o resultado (só agregados);
- o veredito: **APROVADO**, **REPROVADO** (com o motivo e a regra violada) ou
  **PENDENTE** (o que falta);
- se entra ou não no pipeline.

## Fechamento

No final, o validador roda tudo de novo, da versão candidata: testes, determinismo,
validador oficial, varredura do repositório, e escreve o parecer final no registro.
