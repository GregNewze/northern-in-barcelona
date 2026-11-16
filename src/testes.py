"""testes.py - TODA a bateria de testes da Northern in Barcelona, num arquivo so.

Fica em src/, ao lado do v1_11.py.

    python src/testes.py                                   # so unidade (segundos, sem dados)
    python src/testes.py --oficial "/caminho/more-than-a-hack-2027"   # unidade + jogo real
    (sem --oficial, usa o submodulo ./oficial se data/tactical/ tiver os arquivos)

Sai com codigo 0 se tudo passou e 1 se algo falhou. Rode antes de qualquer commit e
antes de submeter.

UNIDADE (dados sinteticos): cada funcao do pipeline, propriedades em sequencias aleatorias,
e um guarda contra ler o tracking do jeito errado.
INTEGRACAO (jogo real): validador e avaliador OFICIAIS (com bootstrap), sem vazamento de
gabarito, determinismo, regressao, leitura da bola = DATA.md, afirmacoes do documento, snapshot.
"""

import argparse
import builtins
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

import v1_11 as N  # noqa: E402
import v1_12 as V12  # noqa: E402

FPS = N.FPS
NOBODY = -1
OFICIAL = os.environ.get("OFICIAL")
SNAPSHOT = os.path.join(AQUI, "snapshot_v1_11.json")
SNAPSHOT_V12 = os.path.join(AQUI, "snapshot_v1_12.json")
PUB = (11185, 18684)
FAQ = (110808, 113741)
# DATA.md, "The ball is missing 43% of all frames, and 41% of the graded ones"
BOLA_TOTAL_DATA_MD = 113488
BOLA_AVALIADOS_DATA_MD = 94214


def L(s):
    return np.array(list(s), dtype="<U1")


class TestTrechos(unittest.TestCase):
    def test_vazio_e_cheio(self):
        self.assertEqual(N.trechos(np.array([False, False])), [])
        self.assertEqual(N.trechos(np.array([True, True, True])), [(0, 2)])

    def test_misto(self):
        m = np.array([0, 1, 1, 0, 1, 0, 0, 1], dtype=bool)
        self.assertEqual(N.trechos(m), [(1, 2), (4, 4), (7, 7)])


class TestSumicos(unittest.TestCase):
    def test_so_dentro_dos_blocos_e_cortado_na_borda(self):
        codes = np.array([0, -1, -1, 0, -1, -1, -1, 1, -1, -1])
        blocos = [(1, 0, 5), (2, 7, 9)]
        self.assertEqual(N.sumicos(codes, NOBODY, blocos), [(1, 2), (4, 5), (8, 9)])


class TestPreencher(unittest.TestCase):
    def test_mesmo_time_curto_preenche(self):
        c = np.array([0, -1, -1, 0])
        self.assertEqual(list(N.preencher_sumicos(c, [(1, 2)], NOBODY, 1.0)), [0, 0, 0, 0])

    def test_times_diferentes_nao_preenche(self):
        c = np.array([0, -1, -1, 1])
        self.assertEqual(list(N.preencher_sumicos(c, [(1, 2)], NOBODY, 1.0)), [0, -1, -1, 1])

    def test_longo_demais_nao_preenche(self):
        n = FPS * 3
        c = np.array([0] + [-1] * n + [0])
        out = N.preencher_sumicos(c, [(1, n)], NOBODY, 2.6)
        self.assertTrue(np.all(out[1:n + 1] == -1))

    def test_borda_do_vetor_nao_preenche(self):
        c = np.array([-1, -1, 0])
        self.assertEqual(list(N.preencher_sumicos(c, [(0, 1)], NOBODY, 9)), [-1, -1, 0])

    def test_nao_altera_entrada(self):
        c = np.array([0, -1, 0])
        N.preencher_sumicos(c, [(1, 1)], NOBODY, 9)
        self.assertEqual(list(c), [0, -1, 0])


class TestMarcarParada(unittest.TestCase):
    def test_limiar_12_frames_nao_13_sim(self):
        # 12 frames = 0.48 s (< 0.5, fica H); 13 frames = 0.52 s (>= 0.5, vira D)
        lab = L("H" * 60)
        out = N.marcar_parada(lab, [(2, 13), (30, 42)], 0.5)
        self.assertTrue(np.all(out[2:14] == "H"))
        self.assertTrue(np.all(out[30:43] == "D"))
        self.assertTrue(np.all(out[43:] == "H") and np.all(out[14:30] == "H"))

    def test_zero_desliga(self):
        lab = L("HHHH")
        self.assertIs(N.marcar_parada(lab, [(0, 3)], 0), lab)


class TestHisterese(unittest.TestCase):
    def test_posse_curta_entre_iguais_e_absorvida(self):
        lab = L("A" * 60 + "H" * 10 + "A" * 60)
        out = N.histerese(lab, 1.5)
        self.assertTrue(np.all(out == "A"))

    def test_posse_longa_fica(self):
        lab = L("A" * 60 + "H" * 40 + "A" * 60)
        self.assertTrue(np.array_equal(N.histerese(lab, 1.5), lab))

    def test_curta_entre_diferentes_vai_pro_anterior(self):
        lab = L("A" * 60 + "H" * 10 + "D" * 5 + "H" * 60)
        out = N.histerese(lab, 1.5)
        self.assertTrue(np.all(out[60:70] == "A"))

    def test_curta_no_comeco_sem_anterior_fica(self):
        lab = L("H" * 10 + "A" * 60)
        self.assertTrue(np.array_equal(N.histerese(lab, 1.5), lab))

    def test_nao_mexe_em_D(self):
        lab = L("A" * 60 + "D" * 5 + "A" * 60)
        self.assertTrue(np.array_equal(N.histerese(lab, 1.5), lab))


class TestIntersecta(unittest.TestCase):
    def test_tolerancia_inclusiva(self):
        ev = [(100, 110)]
        self.assertTrue(N.intersecta(111, 120, ev, 1))
        self.assertFalse(N.intersecta(112, 120, ev, 1))
        self.assertTrue(N.intersecta(80, 99, ev, 1))
        self.assertFalse(N.intersecta(80, 98, ev, 1))


class TestLerSetPieces(unittest.TestCase):
    def test_parse(self):
        xml = """<file><ALL_INSTANCES>
          <instance><ID>1</ID><start>10.0</start><end>12.0</end><code>SET PIECES</code>
            <label><group>Type</group><text>Corner</text></label></instance>
          <instance><ID>2</ID><start>20.0</start><end>30.0</end><code>ATTACKING TRANSITION</code></instance>
          <instance><ID>3</ID><start>abc</start><end>31.0</end><code>SET PIECES</code></instance>
          <instance><ID>4</ID><start>40.04</start><end>41.0</end><code>SET PIECES</code></instance>
        </ALL_INSTANCES></file>"""
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False) as f:
            f.write(xml)
        try:
            ev = N.ler_set_pieces(f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual(ev, [(250, 300), (1001, 1025)])


class TestDecidir(unittest.TestCase):
    def test_sumico_curto_continua(self):
        lab = L("H" * 50 + "D" * 50 + "A" * 50)
        out = N.decidir_sumicos(lab, [], 0, 18.0)
        self.assertTrue(np.all(out[50:100] == "H"))

    def test_sumico_com_set_piece_fica_D(self):
        lab = L("H" * 50 + "D" * 50 + "A" * 50)
        out = N.decidir_sumicos(lab, [(60, 70)], 0, 18.0)
        self.assertTrue(np.all(out[50:100] == "D"))

    def test_sumico_longo_fica_D(self):
        n = 18 * FPS
        lab = L("H" * 10 + "D" * n + "A" * 10)
        out = N.decidir_sumicos(lab, [], 0, 18.0)
        self.assertTrue(np.all(out[10:10 + n] == "D"))
        out2 = N.decidir_sumicos(L("H" * 10 + "D" * (n - 1) + "A" * 10), [], 0, 18.0)
        self.assertTrue(np.all(out2[10:10 + n - 1] == "H"))

    def test_comeco_sem_posse_vira_X(self):
        out = N.decidir_sumicos(L("D" * 10 + "H" * 10), [], 0, 18.0)
        self.assertTrue(np.all(out[:10] == "X"))


class TestForcar(unittest.TestCase):
    def test_bloco_exato_e_idempotente(self):
        lab = L("H" * 199319)
        out = N.forcar_bola_morta(lab)
        d = np.flatnonzero(out != lab)
        self.assertEqual((len(d), d.min(), d.max()), (2934, 110808, 113741))
        self.assertTrue(np.array_equal(N.forcar_bola_morta(out), out))


class TestPropriedades(unittest.TestCase):
    """Sequencias aleatorias: o que vale SEMPRE, qualquer que seja a entrada."""

    def setUp(self):
        self.rng = np.random.default_rng(13)

    def seq(self):
        n = int(self.rng.integers(30, 3000))
        out = []
        while len(out) < n:
            out += [str(self.rng.choice(list("HADX"), p=[.4, .3, .25, .05]))] * int(self.rng.integers(1, 500))
        return np.array(out[:n], dtype="<U1")

    def test_decidir(self):
        for _ in range(500):
            lab = self.seq()
            ev = [(int(s), int(s) + int(self.rng.integers(0, 300))) for s in self.rng.integers(0, len(lab), 3)]
            out = N.decidir_sumicos(lab, ev, int(self.rng.integers(0, 60)), float(self.rng.choice([1, 5, 18])))
            self.assertEqual(len(out), len(lab))
            self.assertTrue(set(out) <= set("HADX"))
            ha = np.isin(lab, ["H", "A"])
            self.assertTrue(np.array_equal(out[ha], lab[ha]), "decidir mudou frame que ja era H/A")
            self.assertFalse(np.any((out == "D") & (lab != "D")), "decidir criou D novo")
            x = lab == "X"
            self.assertTrue(np.array_equal(out[x], lab[x]), "decidir mudou X")

    def test_histerese(self):
        for _ in range(300):
            lab = self.seq()
            out = N.histerese(lab, 1.5)
            self.assertEqual(len(out), len(lab))
            self.assertTrue(np.array_equal(out == "D", lab == "D"), "histerese mexeu em D")
            self.assertTrue(np.array_equal(out == "X", lab == "X"), "histerese mexeu em X")


class TestSemBugDeLeitura(unittest.TestCase):
    """O formato e 'frame:jogadores:BOLA'. Ler com split(':', 1) e tratar o 1o objeto como
    bola e um erro facil de cometer. Nenhum script pode fazer isso."""

    CONHECIDOS = {"testes.py": "este arquivo: cita o padrao na documentacao do guarda"}

    def test_ninguem_le_objeto_0_como_bola(self):
        pastas = [AQUI]
        arquivos = sorted({f for p in pastas for f in glob.glob(os.path.join(p, "*.py"))})
        ruins = []
        for f in arquivos:
            nome = os.path.basename(f)
            with open(f, encoding="utf-8", errors="replace") as h:
                texto = h.read()
            if re.search(r"split\(\s*['\"]:['\"]\s*,\s*1\s*\)", texto) and "atd.txt" in texto:
                if nome not in self.CONHECIDOS:
                    ruins.append(nome)
        self.assertEqual(ruins, [], "estes scripts leem o tracking do jeito errado: %s" % ruins)


def ler_bola_certo(txt, n):
    bola = np.zeros(n, dtype=bool)
    with open(txt, encoding="utf-8", errors="replace") as f:
        for linha in f:
            parts = linha.rstrip("\n").split(":")
            if len(parts) != 3:
                continue
            idx = int(parts[0]) - 1
            if 0 <= idx < n and parts[2] and parts[2][0] != "N":
                bola[idx] = True
    return bola


def posses_e_duracao(labels, mascara, fps):
    lab = labels.copy()
    lab[~mascara] = "X"
    posses, total = 0, 0
    i, n = 0, len(lab)
    while i < n:
        if lab[i] in ("H", "A"):
            j = i
            while j + 1 < n and lab[j + 1] == lab[i]:
                j += 1
            posses += 1
            total += j - i + 1
            i = j + 1
        else:
            i += 1
    return posses, (total / fps / posses if posses else 0.0)


class TestJogoReal(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # checado AQUI (e nao num decorator) porque o --oficial so e lido depois do import
        if not os.environ.get("OFICIAL"):
            raise unittest.SkipTest("sem --oficial: testes do jogo real pulados")
        cls.N = N
        cls.oficial = N.preparar_caminhos(os.environ["OFICIAL"])
        import baseline
        import games
        import possession_metrics as pm
        cls.baseline, cls.games, cls.pm = baseline, games, pm
        print("\n[setup] gerando rotulos com v1_11.gerar_labels ...")
        cls.labels, cls.et = N.gerar_labels(cls.oficial, devolver_etapas=True)
        cls.n = len(cls.labels)
        cls.fps = games.GAMES[games.GAME]["fps"]
        cls.graded = np.zeros(cls.n, dtype=bool)
        for _, a, b in cls.et["blocos"]:
            cls.graded[a:b + 1] = True
        cls.tmp = tempfile.mkdtemp(prefix="nib_testes_")
        cls.csv = os.path.join(cls.tmp, "v1_11_teste.csv")
        baseline.write_submission(cls.csv, cls.labels)
        cls.gt = pm.label_codes(pm.read_label_csv(
            os.path.join(cls.oficial, "evaluation", "gt", "BAR-ATH_possession_gt_public.csv")))
        cls.res = pm.evaluate(cls.gt, pm.label_codes(cls.labels))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # ---------- formato e scripts oficiais ----------
    def test_01_tamanho_e_alfabeto(self):
        self.assertEqual(self.n, self.games.GAMES[self.games.GAME]["n_video_frames"])
        self.assertTrue(set(np.unique(self.labels)) <= set("HADX"))

    def test_02_validador_oficial(self):
        r = subprocess.run([sys.executable, os.path.join(self.oficial, "evaluation", "validate_submission.py"),
                            self.csv], cwd=self.oficial, capture_output=True, text=True)
        print("\n" + r.stdout + r.stderr)
        self.assertEqual(r.returncode, 0, "validate_submission.py REPROVOU o arquivo")
        self.assertTrue(r.stdout.startswith("OK"))

    def test_03_ida_e_volta_do_csv(self):
        lido = self.pm.label_codes(self.pm.read_label_csv(self.csv))
        self.assertTrue(np.array_equal(lido, self.pm.label_codes(self.labels)))

    def test_04_avaliador_oficial_com_bootstrap(self):
        res_dir = os.path.join(self.tmp, "results")
        out_dir = os.path.join(self.tmp, "out")
        os.makedirs(res_dir, exist_ok=True)
        shutil.copy(self.csv, os.path.join(res_dir, "v1_11.csv"))
        r = subprocess.run([sys.executable, "run_evaluation.py", "--results", res_dir, "--out", out_dir,
                            "--bootstrap", "1000", "--no-detail"],
                           cwd=os.path.join(self.oficial, "evaluation"), capture_output=True, text=True)
        print("\n" + r.stdout[-3000:] + r.stderr[-2000:])
        self.assertEqual(r.returncode, 0, "run_evaluation.py falhou ou pulou o arquivo")

    # ---------- regras ----------
    def test_05_bloco_do_FAQ_todo_D(self):
        seg = self.labels[FAQ[0]:FAQ[1] + 1]
        self.assertTrue(np.all(seg == "D"), "bloco do FAQ tem %d frames que nao sao D" % int(np.sum(seg != "D")))

    def test_06_X_nunca_em_frame_avaliado(self):
        nx = int(np.sum(self.labels[self.graded] == "X"))
        self.assertEqual(nx, 0, "o documento diz que X so aparece fora do jogo; ha %d X em frames avaliados" % nx)

    def test_07_decidir_so_mexe_em_D_e_FAQ_so_no_bloco(self):
        lb, sf = self.et["lab_base"], self.et["sem_faq"]
        ha = np.isin(lb, ["H", "A"])
        self.assertTrue(np.array_equal(sf[ha], lb[ha]))
        dif = np.flatnonzero(self.labels != sf)
        self.assertTrue(len(dif) == 0 or (dif.min() >= FAQ[0] and dif.max() <= FAQ[1]))

    def test_08_deterministico_e_sem_gabarito(self):
        """Gera de novo com o gabarito BLOQUEADO: qualquer leitura dele levanta erro.
        Se passar, o pipeline nao le o gabarito e e deterministico."""
        abrir = builtins.open

        def guarda(file, *a, **k):
            s = str(file)
            if "possession_gt" in s or (os.sep + "gt" + os.sep) in s:
                raise AssertionError("o pipeline tentou abrir o gabarito: " + s)
            return abrir(file, *a, **k)

        with mock.patch("builtins.open", guarda), \
                mock.patch.object(self.pm, "read_label_csv", side_effect=AssertionError("pipeline leu o gabarito")):
            de_novo = self.N.gerar_labels(self.oficial)
        self.assertTrue(np.array_equal(de_novo, self.labels), "segunda execucao deu resultado diferente")

    # ---------- regressao ----------
    def test_09_igual_ao_v1_11_csv_do_disco(self):
        p = os.path.join(self.oficial, "evaluation", "results", "v1_11.csv")
        if not os.path.exists(p):
            self.skipTest("nao ha v1_11.csv no disco")
        disco = self.pm.label_codes(self.pm.read_label_csv(p))
        self.assertTrue(np.array_equal(disco, self.pm.label_codes(self.labels)))

    # ---------- dados de entrada ----------
    def test_11_leitura_da_bola_bate_com_DATA_md_e_com_baseline(self):
        txt = os.path.join(self.oficial, "data", "tactical", "BAR-ATH_tactical_atd.txt")
        bola = ler_bola_certo(txt, self.n)
        self.assertEqual(int(bola.sum()), BOLA_TOTAL_DATA_MD)
        self.assertEqual(int(bola[self.graded].sum()), BOLA_AVALIADOS_DATA_MD)
        vistos = self.et["codes"] != self.baseline.NOBODY
        self.assertEqual(int(np.sum(vistos & ~bola)), 0, "baseline viu bola onde ela nao existe")
        print("\n  frames com bola mas sem resposta do baseline: %d" % int(np.sum(bola & ~vistos)))

    def test_12_set_pieces_sanidade(self):
        ev = self.et["ev"]
        self.assertGreater(len(ev), 0)
        self.assertTrue(all(0 <= s <= e < self.n for s, e in ev), "evento fora do video ou com fim < inicio")
        print("\n  set pieces lidos: %d" % len(ev))

    # ---------- snapshot ----------
    def metricas(self):
        posses, dur = posses_e_duracao(self.labels, self.graded, self.fps)
        vivo = self.graded & np.isin(self.labels, ["H", "A"])
        return {
            "sha256": hashlib.sha256("".join(self.labels.tolist()).encode()).hexdigest(),
            "posses_avaliadas": posses,
            "duracao_media_s": round(dur, 3),
            "D_pct_avaliado": round(float(np.mean(self.labels[self.graded] == "D")) * 100, 3),
            "posses_por_min_vivo": round(posses / (vivo.sum() / self.fps / 60), 3),
            "spellF1_publico": round(float(self.res["spell_f1_mean"]), 4),
            "macroF1_publico": round(float(self.res["macro_f1"]), 4),
        }

    def test_13_snapshot(self):
        m = self.metricas()
        if not os.path.exists(SNAPSHOT) or os.environ.get("ATUALIZAR_SNAPSHOT") == "1":
            with open(SNAPSHOT, "w") as f:
                json.dump(m, f, indent=2)
            self.skipTest("snapshot gravado em src/snapshot_v1_11.json (proximas rodadas comparam com ele)")
        with open(SNAPSHOT) as f:
            antigo = json.load(f)
        self.assertEqual(m, antigo, "a saida mudou em relacao ao snapshot. Se foi de proposito, "
                                    "rode com ATUALIZAR_SNAPSHOT=1 e explique a mudanca no commit.")

    def test_99_resumo(self):
        m = self.metricas()
        print("\n  RESUMO v1_11")
        for k, v in m.items():
            print("   %-22s %s" % (k, v))


# =====================================================================================
# v1.12 = v1.11 + regra da calma
# =====================================================================================

class TestCalmaUnidade(unittest.TestCase):

    def montar(self):
        n = 3000
        lab = np.array(["H"] * n, dtype="<U1")
        v = np.full(n, 2.0, dtype=np.float32)
        gaps = []

        def gap(a, seg, vel):
            b = a + int(seg * FPS) - 1
            gaps.append((a, b))
            v[a:b + 1] = vel
            return a, b
        g = dict(lento=gap(100, 10, 0.8), rapido=gap(500, 10, 2.2), com_sp=gap(900, 10, 0.8),
                 curto=gap(1400, 4, 0.5), longo=gap(1700, 18, 0.5), cinco=gap(2200, 5, 0.5))
        ev = [(g["com_sp"][0] + 50, g["com_sp"][0] + 60)]
        return lab, v, gaps, ev, g

    def test_casos(self):
        lab, v, gaps, ev, g = self.montar()
        out, mud = V12.aplicar_calma(lab, gaps, ev, 0, v, 1.31)
        esperado = dict(lento="D", rapido="H", com_sp="H", curto="H", longo="H", cinco="D")
        for k, (a, b) in g.items():
            self.assertTrue(np.all(out[a:b + 1] == esperado[k]), "caso %s" % k)
        self.assertEqual(len(mud), 2)

    def test_so_muda_dentro_dos_sumicos_e_so_pra_D(self):
        lab, v, gaps, ev, _ = self.montar()
        out, _ = V12.aplicar_calma(lab, gaps, ev, 0, v, 1.31)
        dentro = np.zeros(len(lab), dtype=bool)
        for a, b in gaps:
            dentro[a:b + 1] = True
        dif = out != lab
        self.assertFalse(np.any(dif & ~dentro))
        self.assertTrue(np.all(out[dif] == "D"))

    def test_referencias(self):
        lab, v, gaps, ev, _ = self.montar()
        vis = np.ones(len(lab), dtype=bool)
        for a, b in gaps:
            vis[a:b + 1] = False
        j, p, c = V12.referencias(v, lab, vis, np.ones(len(lab), dtype=bool), gaps, ev, 0)
        self.assertAlmostEqual(j, 2.0, places=5)
        self.assertAlmostEqual(p, 0.8, places=5)
        self.assertAlmostEqual(c, 1.4, places=5)

    def test_velocidade_conhecida(self):
        n = 60
        pos = np.full((n, 8, 2), np.nan, dtype=np.float32)
        t = np.arange(n) / FPS
        pos[:, :4, 0] = (10 + 1.0 * t)[:, None]      # 4 andando a 1 m/s
        pos[:, 4:, 0] = (30 + 5.0 * t)[:, None]      # 4 correndo a 5 m/s
        pos[:, :, 1] = 34.0
        pos[30, 0, 0] = 104.0                          # salto do tracker
        v = V12.atividade_por_frame(pos)
        self.assertTrue(np.all(np.isnan(v[:V12.PASSO])))
        self.assertTrue(np.allclose(v[10:26], 3.0, atol=1e-3))
        self.assertLess(float(np.nanmax(v)), 5.01, "salto do tracker vazou na velocidade")

    def test_ler_jogadores_formato(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.txt")
            with open(p, "w") as f:
                f.write("1:0.10,0.50,1;NaN,NaN,NaN:0.7,0.3,0.1\n2:0.20,0.50,1;0.30,0.40,1:NaN,NaN,NaN\n")
            pos = V12.ler_jogadores(p, 5, 105.0, 68.0)
        self.assertEqual(pos.shape, (5, 2, 2))
        self.assertTrue(np.allclose(pos[0, 0], [10.5, 34.0]))
        self.assertTrue(np.all(np.isnan(pos[0, 1])))
        self.assertTrue(np.allclose(pos[1, 1], [31.5, 27.2]))
        self.assertTrue(np.all(np.isnan(pos[2])))


class TestJogoRealV12(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.environ.get("OFICIAL"):
            raise unittest.SkipTest("sem --oficial: testes do jogo real (v1.12) pulados")
        cls.oficial = N.preparar_caminhos(os.environ["OFICIAL"])
        import baseline
        import games
        import possession_metrics as pm
        cls.baseline, cls.games, cls.pm = baseline, games, pm
        print("\n[setup v1.12] gerando rotulos ...")
        cls.labels, cls.et = V12.gerar_labels(cls.oficial, devolver_etapas=True)
        cls.n = len(cls.labels)
        cls.fps = games.GAMES[games.GAME]["fps"]
        cls.graded = cls.et["graded"]
        cls.tmp = tempfile.mkdtemp(prefix="nib_testes12_")
        cls.csv = os.path.join(cls.tmp, "v1_12_teste.csv")
        baseline.write_submission(cls.csv, cls.labels)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_01_validador_oficial(self):
        r = subprocess.run([sys.executable, os.path.join(self.oficial, "evaluation", "validate_submission.py"),
                            self.csv], cwd=self.oficial, capture_output=True, text=True)
        print("\n" + r.stdout + r.stderr)
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stdout.startswith("OK"))

    def test_02_FAQ_todo_D_e_sem_X_avaliado(self):
        self.assertTrue(np.all(self.labels[FAQ[0]:FAQ[1] + 1] == "D"))
        self.assertEqual(int(np.sum(self.labels[self.graded] == "X")), 0)

    def test_03_unica_diferenca_e_HA_virando_D_nos_sumicos_mudados(self):
        lab11 = self.et["labels_v1_11"]
        dentro = np.zeros(self.n, dtype=bool)
        for a, b, _, _ in self.et["mudados"]:
            dentro[a:b + 1] = True
        dif = np.flatnonzero(self.labels != lab11)
        self.assertTrue(np.all(dentro[dif]), "mudou frame fora dos sumicos elegiveis")
        self.assertTrue(np.all(self.labels[dif] == "D"))
        self.assertTrue(np.all(np.isin(lab11[dif], ["H", "A"])))
        # explica a conta inteira: muda EXATAMENTE o que estava nos sumicos mudados e nao era D
        esperado = dentro & (lab11 != "D")
        self.assertTrue(np.array_equal(self.labels != lab11, esperado))
        ja_D = int(np.sum(dentro & (lab11 == "D")))
        no_faq = int(np.sum(dentro[FAQ[0]:FAQ[1] + 1]))
        print("\n  frames nos sumicos mudados: %d | ja eram D na v1.11: %d | desses, no bloco do FAQ: %d"
              % (int(dentro.sum()), ja_D, no_faq))

    def test_04_v1_11_interna_igual_ao_snapshot_da_v1_11(self):
        if not os.path.exists(SNAPSHOT):
            self.skipTest("sem snapshot da v1.11")
        with open(SNAPSHOT) as f:
            s = json.load(f)
        sha = hashlib.sha256("".join(self.et["labels_v1_11"].tolist()).encode()).hexdigest()
        self.assertEqual(sha, s["sha256"], "a v1.11 usada por dentro da v1.12 nao e a v1.11 validada")

    def test_05_corte_entre_as_referencias(self):
        j, p, c = self.et["ref_jogo"], self.et["ref_parada"], self.et["corte"]
        print("\n  jogo %.3f | parada %.3f | corte %.3f | mudados %d" % (j, p, c, len(self.et["mudados"])))
        self.assertLess(p, c)
        self.assertLess(c, j)
        for a, b, dur, m in self.et["mudados"]:
            self.assertTrue(V12.CALMA_MIN_S <= dur < V12.CALMA_MAX_S and m < c)

    def test_06_deterministico_e_sem_gabarito(self):
        abrir = builtins.open

        def guarda(file, *a, **k):
            s = str(file)
            if "possession_gt" in s or (os.sep + "gt" + os.sep) in s:
                raise AssertionError("o pipeline tentou abrir o gabarito: " + s)
            return abrir(file, *a, **k)

        with mock.patch("builtins.open", guarda), \
                mock.patch.object(self.pm, "read_label_csv", side_effect=AssertionError("pipeline leu o gabarito")):
            de_novo = V12.gerar_labels(self.oficial)
        self.assertTrue(np.array_equal(de_novo, self.labels))

    def test_07_avaliador_oficial_v1_11_e_v1_12(self):
        res_dir = os.path.join(self.tmp, "results")
        os.makedirs(res_dir, exist_ok=True)
        shutil.copy(self.csv, os.path.join(res_dir, "v1_12.csv"))
        self.baseline.write_submission(os.path.join(res_dir, "v1_11.csv"), self.et["labels_v1_11"])
        r = subprocess.run([sys.executable, "run_evaluation.py", "--results", res_dir, "--out",
                            os.path.join(self.tmp, "out"), "--bootstrap", "1000", "--no-detail"],
                           cwd=os.path.join(self.oficial, "evaluation"), capture_output=True, text=True)
        print("\n" + r.stdout[-3000:] + r.stderr[-2000:])
        self.assertEqual(r.returncode, 0)

    def metricas(self):
        posses, dur = posses_e_duracao(self.labels, self.graded, self.fps)
        vivo = self.graded & np.isin(self.labels, ["H", "A"])
        gt = self.pm.label_codes(self.pm.read_label_csv(
            os.path.join(self.oficial, "evaluation", "gt", "BAR-ATH_possession_gt_public.csv")))
        res = self.pm.evaluate(gt, self.pm.label_codes(self.labels))
        return {
            "sha256": hashlib.sha256("".join(self.labels.tolist()).encode()).hexdigest(),
            "corte_ms": round(float(self.et["corte"]), 4),
            "sumicos_mudados": len(self.et["mudados"]),
            "frames_mudados": int(sum(b - a + 1 for a, b, _, _ in self.et["mudados"])),
            "posses_avaliadas": posses,
            "duracao_media_s": round(dur, 3),
            "D_pct_avaliado": round(float(np.mean(self.labels[self.graded] == "D")) * 100, 3),
            "posses_por_min_vivo": round(posses / (vivo.sum() / self.fps / 60), 3),
            "spellF1_publico": round(float(res["spell_f1_mean"]), 4),
            "macroF1_publico": round(float(res["macro_f1"]), 4),
        }

    def test_08_snapshot_v1_12(self):
        m = self.metricas()
        if not os.path.exists(SNAPSHOT_V12) or os.environ.get("ATUALIZAR_SNAPSHOT") == "1":
            with open(SNAPSHOT_V12, "w") as f:
                json.dump(m, f, indent=2)
            self.skipTest("snapshot gravado em src/snapshot_v1_12.json (proximas rodadas comparam com ele)")
        with open(SNAPSHOT_V12) as f:
            self.assertEqual(m, json.load(f), "a saida da v1.12 mudou em relacao ao snapshot")

    def test_99_resumo(self):
        print("\n  RESUMO v1_12")
        for k, val in self.metricas().items():
            print("   %-22s %s" % (k, val))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--oficial", default=None, help="pasta do pacote de dados (ativa os testes de integracao)")
    a = ap.parse_args()
    if a.oficial:
        os.environ["OFICIAL"] = os.path.abspath(a.oficial)
    elif glob.glob(os.path.join(N.OFICIAL_PADRAO, "data", "tactical", "*")):
        # submodulo ./oficial com os dados baixados -> integracao liga sozinha
        os.environ["OFICIAL"] = os.path.abspath(N.OFICIAL_PADRAO)
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    r = unittest.TextTestRunner(verbosity=2).run(suite)
    print("\n" + "=" * 60)
    print("RESULTADO: %d testes | %d falhas | %d erros | %d pulados"
          % (r.testsRun, len(r.failures), len(r.errors), len(r.skipped)))
    print("TUDO OK" if r.wasSuccessful() else "TEM PROBLEMA - leia as falhas acima")
    sys.exit(0 if r.wasSuccessful() else 1)