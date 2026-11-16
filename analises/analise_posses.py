"""analise_posses.py - olha as POSSES geradas no JOGO COMPLETO (sem gabarito).

Procura "posses pequenas impossiveis". Pra cada CSV em
evaluation/results/, mede a distribuicao de duracao das posses (runs de H ou A)
e aponta:
  - posses "impossiveis" (< 2s): rapidas demais pra serem posse de verdade.
  - "sanduiches": posse curta de um time encravada entre dois trechos do outro
    (A...B...A) - ruido de alternancia.

Nao mede nota (nao usa gabarito). So descreve a saida pra a gente escolher a
versao mais plausivel e achar ruido pra limpar.

Uso:
    python analises/analise_posses.py
    python analises/analise_posses.py --foco v1_11,v1_12
"""

import argparse
import glob
import os

FPS = 25


def ler_labels(csv_path):
    labels = []
    with open(csv_path, encoding="utf-8", errors="replace") as f:
        for i, linha in enumerate(f):
            linha = linha.strip()
            if not linha:
                continue
            if i == 0 and ("frame" in linha.lower() or "label" in linha.lower()):
                continue
            parts = linha.split(",")
            if len(parts) >= 2:
                labels.append(parts[1].strip())
    return labels


def posses(labels):
    """Lista (inicio, fim, time) de cada run de H ou A. D e X quebram."""
    out = []
    n = len(labels)
    i = 0
    while i < n:
        if labels[i] in ("H", "A"):
            j = i
            while j + 1 < n and labels[j + 1] == labels[i]:
                j += 1
            out.append((i, j, labels[i]))
            i = j + 1
        else:
            i += 1
    return out


def resumo(labels):
    ps = posses(labels)
    durs = [(b - a + 1) / FPS for a, b, _ in ps]
    if not durs:
        return None
    durs_ord = sorted(durs)
    n = len(durs)
    mediana = durs_ord[n // 2]
    media = sum(durs) / n
    imp2 = sum(1 for d in durs if d < 2.0)
    imp3 = sum(1 for d in durs if d < 3.0)
    # sanduiches: posse curta (<3s) entre duas posses do OUTRO time
    sand = 0
    for k in range(1, len(ps) - 1):
        a, b, t = ps[k]
        dur = (b - a + 1) / FPS
        if dur < 3.0 and ps[k - 1][2] != t and ps[k + 1][2] != t and ps[k - 1][2] == ps[k + 1][2]:
            sand += 1
    return {"n": n, "mediana": mediana, "media": media, "min": min(durs), "max": max(durs),
            "imp2": imp2, "imp3": imp3, "sand": sand, "durs": durs}


def histograma(durs):
    buckets = [(0, 2), (2, 5), (5, 10), (10, 20), (20, 40), (40, 1e9)]
    rot = ["<2s", "2-5s", "5-10s", "10-20s", "20-40s", "40s+"]
    cont = [0] * len(buckets)
    for d in durs:
        for i, (lo, hi) in enumerate(buckets):
            if lo <= d < hi:
                cont[i] += 1
                break
    tot = max(1, len(durs))
    for i, r in enumerate(rot):
        larg = int(round(cont[i] / tot * 40))
        print(f"  {r:>7} | {'#'*larg}{'.'*(40-larg)} {cont[i]:>4} ({cont[i]/tot*100:4.1f}%)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--oficial", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "oficial"))
    p.add_argument("--foco", default="v1_11,v1_12",
                   help="versoes pro histograma detalhado (nomes dos CSV sem .csv)")
    a = p.parse_args()

    results = os.path.join(os.path.abspath(a.oficial), "evaluation", "results")
    arquivos = sorted(glob.glob(os.path.join(results, "*.csv")))
    if not arquivos:
        print("Nenhum CSV em evaluation/results/")
        return

    print()
    print("POSSES NO JOGO COMPLETO  (so a nossa saida, sem gabarito)")
    print("alvo saudavel: poucas posses < 2s (impossiveis) e poucos sanduiches")
    print("=" * 90)
    print(f"{'versao':>22} | {'posses':>6} | {'mediana':>7} | {'media':>6} | {'<2s':>10} | {'<3s':>6} | {'sanduic':>7}")
    print("-" * 90)
    dados = {}
    for arq in arquivos:
        nome = os.path.splitext(os.path.basename(arq))[0]
        try:
            r = resumo(ler_labels(arq))
        except Exception as e:
            print(f"{nome:>22} | erro: {e}")
            continue
        if not r:
            continue
        dados[nome] = r
        print(f"{nome:>22} | {r['n']:>6} | {r['mediana']:>5.1f}s | {r['media']:>4.1f}s | "
              f"{r['imp2']:>3} ({r['imp2']/r['n']*100:4.1f}%) | {r['imp3']:>5} | {r['sand']:>7}")
    print("=" * 90)

    foco = [s.strip() for s in a.foco.split(",") if s.strip()]
    for nome in foco:
        if nome in dados:
            print(f"\nDISTRIBUICAO DE DURACAO - {nome}  ({dados[nome]['n']} posses, "
                  f"mediana {dados[nome]['mediana']:.1f}s)")
            histograma(dados[nome]["durs"])
    print("\nleitura: posses <2s sao fisicamente improvaveis (ruido).")
    print("sanduiches = posse curta de um time no meio do dominio do outro (A...B...A).")
    print("menos impossiveis + menos sanduiches = saida mais limpa/plausivel.")


if __name__ == "__main__":
    main()