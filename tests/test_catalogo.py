from pathlib import Path

import pytest

BANCO = Path(__file__).resolve().parent.parent / "database"
TABELAS = ["oficinas", "categorias_item", "precos_referencia"]
SO_NO_SEED = ["usuarios", "veiculos", "orcamentos", "itens_orcamento"]


def bloco(texto, tabela):
    inicio = texto.index(f"INSERT INTO {tabela} ")
    return texto[inicio : texto.index("\n\n", inicio)]


@pytest.fixture(scope="module")
def arquivos():
    seed = (BANCO / "seed.sql").read_text(encoding="utf-8")
    catalogo = (BANCO / "catalogo.sql").read_text(encoding="utf-8")
    return seed, catalogo


@pytest.mark.parametrize("tabela", TABELAS)
def test_catalogo_igual_ao_seed(arquivos, tabela):
    seed, catalogo = arquivos
    assert bloco(catalogo, tabela) == bloco(seed, tabela)


def test_catalogo_nao_tem_dados_de_teste_nem_apaga_nada(arquivos):
    _, catalogo = arquivos
    for tabela in SO_NO_SEED:
        assert f"INSERT INTO {tabela} " not in catalogo
    for comando in ("TRUNCATE", "DELETE", "DROP"):
        assert comando not in catalogo.upper()
