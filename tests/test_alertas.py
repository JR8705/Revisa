import copy
from decimal import Decimal

import pytest

from api import alertas
from api.alertas import (
    LIMITE_MAO_OBRA,
    ORDEM_SEVERIDADE,
    alerta_duplicado,
    alerta_mao_obra,
    alerta_valor_zerado,
    gerar_alertas,
    normalizar_descricao,
)
from api.enums import SeveridadeAlertaEnum, TipoAlertaEnum, TipoItemEnum
from api.regras import calcular_subtotal

PECA = TipoItemEnum.PECA
MAO = TipoItemEnum.MAO_OBRA
ALTA = SeveridadeAlertaEnum.ALTA
MEDIA = SeveridadeAlertaEnum.MEDIA
DUPLICADO = TipoAlertaEnum.ITEM_DUPLICADO
ZERADO = TipoAlertaEnum.VALOR_ZERADO
MAO_ALTA = TipoAlertaEnum.MAO_OBRA_ALTA


def item(id_item, descricao, tipo, quantidade, valor_unitario):
    quantidade = Decimal(quantidade)
    valor_unitario = Decimal(valor_unitario)
    return {
        "id": id_item,
        "id_categoria": 1,
        "descricao": descricao,
        "tipo": tipo,
        "quantidade": quantidade,
        "valor_unitario": valor_unitario,
        "subtotal": calcular_subtotal(quantidade, valor_unitario),
    }


def resumo(alertas):
    return [(a["tipo"], a["severidade"], a["id_item"]) for a in alertas]


SEED_5 = [
    item(21, "Óleo 0W20 sintético (litro)", PECA, "4", "70.00"),
    item(22, "Filtro de óleo", PECA, "1", "55.00"),
    item(23, "Mão de obra troca de óleo", MAO, "1", "350.00"),
]
SEED_3 = [
    item(10, "Kit correia dentada + tensor", PECA, "1", "690.00"),
    item(11, "Bomba d'água", PECA, "1", "380.00"),
    item(12, "Bomba d'água", PECA, "1", "380.00"),
    item(13, "Material diverso", PECA, "1", "150.00"),
    item(14, "Líquido de arrefecimento (litro)", PECA, "3", "32.00"),
    item(15, "Mão de obra correia e bomba d'água", MAO, "1", "450.00"),
]
SEED_11 = [
    item(47, "Bateria 60Ah", PECA, "1", "590.00"),
    item(48, "Lâmpada farol H11 (par)", PECA, "1", "0.00"),
    item(49, "Diagnóstico com scanner", MAO, "1", "120.00"),
    item(50, "Mão de obra instalação", MAO, "1", "40.00"),
]


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Bomba d'água", "bombadagua"),
        ("BOMBA DAGUA", "bombadagua"),
        ("  bomba d agua ", "bombadagua"),
        ("Bomba-d'água", "bombadagua"),
        ("Óleo 5W-30", "oleo5w30"),
        ("Ação / Coração", "acaocoracao"),
        ("Disco 11", "disco11"),
        ("---", ""),
        ("", ""),
    ],
)
def test_normalizar_descricao(texto, esperado):
    assert normalizar_descricao(texto) == esperado


@pytest.mark.parametrize(
    ("itens", "esperado"),
    [
        (SEED_5, [(MAO_ALTA, MEDIA, None)]),
        (SEED_3, [(DUPLICADO, ALTA, 12)]),
        (SEED_11, [(ZERADO, ALTA, 48)]),
        ([], []),
        (
            [item(1, "Lâmpada", PECA, "1", "0"), item(2, "Mão de obra", MAO, "1", "0")],
            [(ZERADO, ALTA, 1), (ZERADO, ALTA, 2)],
        ),
        (
            [
                item(1, "Peça", PECA, "1", "100"),
                item(2, "Mão de obra", MAO, "1", "100"),
            ],
            [],
        ),
        (
            [
                item(1, "Mão de obra", MAO, "1", "500"),
                item(2, "Filtro", PECA, "1", "10"),
                item(3, "Lâmpada", PECA, "1", "0"),
                item(4, "filtro", PECA, "1", "10"),
            ],
            [(ZERADO, ALTA, 3), (DUPLICADO, ALTA, 4), (MAO_ALTA, MEDIA, None)],
        ),
    ],
    ids=[
        "seed-5-mao-de-obra",
        "seed-3-duplicado",
        "seed-11-zerado",
        "vazio",
        "todos-zerados-sem-divisao-por-zero",
        "mao-de-obra-exatamente-50",
        "ordem-alta-por-id-depois-media",
    ],
)
def test_gerar_alertas(itens, esperado):
    assert resumo(gerar_alertas(itens)) == esperado


def test_duplicado_varias_escritas():
    itens = [
        item(1, "Bomba d'água", PECA, "1", "380"),
        item(2, "BOMBA DAGUA", PECA, "1", "380"),
        item(3, "  bomba d agua ", PECA, "1", "380"),
        item(4, "Bomba-d'água", PECA, "1", "390"),
        item(5, "Bomba d'água 2", PECA, "1", "380"),
    ]
    assert [a["id_item"] for a in alerta_duplicado(itens)] == [2, 3, 4]


def test_duplicado_tres_iguais_gera_dois():
    itens = [item(i, "Filtro de ar", PECA, "1", "40") for i in (7, 8, 9)]
    assert [a["id_item"] for a in alerta_duplicado(itens)] == [8, 9]


def test_duplicado_com_preco_diferente_ainda_alerta():
    itens = [
        item(1, "Bomba d'água", PECA, "1", "380"),
        item(2, "Bomba d'água", PECA, "1", "390"),
    ]
    assert resumo(alerta_duplicado(itens)) == [(DUPLICADO, ALTA, 2)]


def test_valor_zerado_olha_o_valor_unitario():
    itens = [item(1, "Lâmpada", PECA, "3", "0"), item(2, "Filtro", PECA, "1", "0.01")]
    assert [a["id_item"] for a in alerta_valor_zerado(itens)] == [1]


@pytest.mark.parametrize(
    ("mao_de_obra", "alerta"),
    [("100.00", False), ("100.01", True), ("99.99", False)],
)
def test_limite_da_mao_de_obra_e_estrito(mao_de_obra, alerta):
    itens = [item(1, "Peça", PECA, "1", "100"), item(2, "Mão", MAO, "1", mao_de_obra)]
    assert bool(alerta_mao_obra(itens)) is alerta


def test_limite_passado_por_parametro():
    assert alerta_mao_obra(SEED_5, limite=Decimal("0.60")) == []
    assert LIMITE_MAO_OBRA == Decimal("0.50")


def test_mensagem_da_mao_de_obra_traz_o_percentual():
    assert "51.09" in alerta_mao_obra(SEED_5)[0]["mensagem"]


def test_ordem_das_severidades():
    assert sorted(SeveridadeAlertaEnum, key=ORDEM_SEVERIDADE.get) == [
        SeveridadeAlertaEnum.ALTA,
        SeveridadeAlertaEnum.MEDIA,
        SeveridadeAlertaEnum.BAIXA,
    ]


def test_ordem_usa_a_severidade_e_nao_o_texto(monkeypatch):
    def falso(tipo, severidade, id_item):
        return {
            "tipo": tipo,
            "severidade": severidade,
            "id_item": id_item,
            "mensagem": "x",
        }

    monkeypatch.setattr(
        alertas, "alerta_mao_obra", lambda itens: [falso(MAO_ALTA, MEDIA, None)]
    )
    monkeypatch.setattr(
        alertas,
        "alerta_duplicado",
        lambda itens: [falso(DUPLICADO, SeveridadeAlertaEnum.BAIXA, 1)],
    )
    monkeypatch.setattr(
        alertas, "alerta_valor_zerado", lambda itens: [falso(ZERADO, ALTA, 9)]
    )
    assert [a["severidade"] for a in alertas.gerar_alertas([])] == [
        ALTA,
        MEDIA,
        SeveridadeAlertaEnum.BAIXA,
    ]


def test_alerta_tem_os_quatro_campos():
    for alerta in gerar_alertas(SEED_3 + SEED_5 + SEED_11):
        assert set(alerta) == {"tipo", "severidade", "id_item", "mensagem"}
        assert isinstance(alerta["mensagem"], str) and alerta["mensagem"]


def test_nao_altera_os_itens_recebidos():
    itens = copy.deepcopy(SEED_3)
    gerar_alertas(itens)
    assert itens == SEED_3
