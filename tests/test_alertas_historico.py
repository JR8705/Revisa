import copy
from datetime import date
from decimal import Decimal

import pytest

from api.alertas import (
    LIMITE_PRECO_ALTA,
    alerta_preco_acima,
    alerta_troca_recente,
    gerar_alertas,
)
from api.enums import SeveridadeAlertaEnum, TipoAlertaEnum, TipoItemEnum
from api.regras import calcular_subtotal

PECA = TipoItemEnum.PECA
MAO = TipoItemEnum.MAO_OBRA
ALTA = SeveridadeAlertaEnum.ALTA
MEDIA = SeveridadeAlertaEnum.MEDIA
PRECO = TipoAlertaEnum.PRECO_ACIMA_MEDIA
TROCA = TipoAlertaEnum.TROCA_RECENTE
DUPLICADO = TipoAlertaEnum.ITEM_DUPLICADO
ZERADO = TipoAlertaEnum.VALOR_ZERADO
MAO_ALTA = TipoAlertaEnum.MAO_OBRA_ALTA

TETOS = {
    1: Decimal("45.00"),
    2: Decimal("80.00"),
    6: Decimal("90.00"),
    9: Decimal("90.00"),
    10: Decimal("200.00"),
    13: Decimal("500.00"),
    17: Decimal("320.00"),
    19: Decimal("1200.00"),
    25: Decimal("520.00"),
    26: Decimal("70.00"),
    27: Decimal("950.00"),
}
INTERVALOS = {
    1: (10000, 12),
    2: (10000, 12),
    3: (None, 24),
    6: (10000, 12),
    7: (15000, 12),
    9: (15000, 12),
    16: (None, None),
    28: (None, None),
}
DATA_5 = date(2026, 6, 1)
KM_5 = 37200


def item(id_item, id_categoria, descricao, tipo, quantidade, valor_unitario):
    quantidade = Decimal(quantidade)
    valor_unitario = Decimal(valor_unitario)
    return {
        "id": id_item,
        "id_categoria": id_categoria,
        "descricao": descricao,
        "tipo": tipo,
        "quantidade": quantidade,
        "valor_unitario": valor_unitario,
        "subtotal": calcular_subtotal(quantidade, valor_unitario),
    }


def troca(id_categoria, data, km):
    return {"id_categoria": id_categoria, "data_emissao": data, "km": km}


def resumo(alertas):
    return [(a["tipo"], a["severidade"], a["id_item"]) for a in alertas]


HISTORICO_4 = [troca(c, date(2026, 4, 5), 35000) for c in (2, 6, 7, 9, 28)]

SEED_3 = [
    item(10, 13, "Kit correia dentada + tensor", PECA, "1", "690.00"),
    item(11, 17, "Bomba d'água", PECA, "1", "380.00"),
    item(12, 17, "Bomba d'água", PECA, "1", "380.00"),
    item(13, 29, "Material diverso", PECA, "1", "150.00"),
    item(14, 4, "Líquido de arrefecimento (litro)", PECA, "3", "32.00"),
    item(15, 28, "Mão de obra correia e bomba d'água", MAO, "1", "450.00"),
]
SEED_5 = [
    item(21, 2, "Óleo 0W20 sintético (litro)", PECA, "4", "70.00"),
    item(22, 6, "Filtro de óleo", PECA, "1", "55.00"),
    item(23, 28, "Mão de obra troca de óleo", MAO, "1", "350.00"),
]
SEED_8 = [
    item(32, 27, "Kit embreagem (platô, disco, rolamento)", PECA, "1", "980.00"),
    item(33, 5, "Óleo de câmbio 75W80 (litro)", PECA, "2", "65.00"),
    item(34, 29, "Estopa, graxa e desengripante", PECA, "1", "120.00"),
    item(35, 28, "Mão de obra troca de embreagem", MAO, "1", "550.00"),
]
SEED_11 = [
    item(47, 25, "Bateria 60Ah", PECA, "1", "590.00"),
    item(48, 26, "Lâmpada farol H11 (par)", PECA, "1", "0.00"),
    item(49, 30, "Diagnóstico com scanner", MAO, "1", "120.00"),
    item(50, 28, "Mão de obra instalação", MAO, "1", "40.00"),
]
SEED_13 = [
    item(57, 19, "Bico injetor diesel", PECA, "4", "1500.00"),
    item(58, 30, "Diagnóstico com scanner", MAO, "1", "150.00"),
    item(59, 28, "Mão de obra substituição dos bicos", MAO, "1", "600.00"),
]


@pytest.mark.parametrize(
    ("itens", "esperado"),
    [
        (SEED_3, [(PRECO, ALTA, 10), (PRECO, MEDIA, 11), (PRECO, MEDIA, 12)]),
        (SEED_8, [(PRECO, MEDIA, 32)]),
        (SEED_11, [(PRECO, MEDIA, 47)]),
        (SEED_13, [(PRECO, ALTA, 57)]),
        ([item(55, 9, "Filtro de cabine", PECA, "1", "90.00")], []),
        ([item(1, 9, "Filtro de cabine", PECA, "1", "90.01")], [(PRECO, MEDIA, 1)]),
        ([item(1, 10, "Pastilha", PECA, "1", "240.00")], [(PRECO, MEDIA, 1)]),
        ([item(1, 10, "Pastilha", PECA, "1", "240.01")], [(PRECO, ALTA, 1)]),
        ([item(1, 28, "Mão de obra", MAO, "1", "9999.00")], []),
        ([item(1, 30, "Peça sem teto", PECA, "1", "9999.00")], []),
        ([item(1, 10, "Troca de pastilha", MAO, "1", "900.00")], []),
        ([item(1, 1, "Óleo (litro)", PECA, "10", "40.00")], []),
        ([], []),
    ],
    ids=[
        "seed-3",
        "seed-8",
        "seed-11",
        "seed-13-exatamente-25",
        "igual-ao-teto",
        "um-centavo-acima",
        "exatamente-20-media",
        "acima-de-20-alta",
        "mao-de-obra-sem-teto",
        "categoria-sem-teto",
        "mao-de-obra-em-categoria-com-teto",
        "unitario-e-nao-subtotal",
        "vazio",
    ],
)
def test_preco_acima(itens, esperado):
    assert resumo(alerta_preco_acima(itens, TETOS)) == esperado


def test_limite_do_preco():
    assert LIMITE_PRECO_ALTA == Decimal("0.20")


def test_mensagem_do_preco():
    mensagem = alerta_preco_acima(SEED_13, TETOS)[0]["mensagem"]
    assert mensagem == (
        "O item 'Bico injetor diesel' custa R$ 1.500,00, 25.00% acima do teto "
        "de referência (R$ 1.200,00)."
    )


@pytest.mark.parametrize(
    ("itens", "historico", "km", "data", "esperado"),
    [
        (SEED_5, HISTORICO_4, KM_5, DATA_5, [(TROCA, ALTA, 21), (TROCA, ALTA, 22)]),
        (SEED_5[:1], HISTORICO_4, 45000, DATA_5, []),
        (SEED_5[:1], HISTORICO_4, 44999, DATA_5, [(TROCA, ALTA, 21)]),
        (SEED_5[:1], HISTORICO_4, 36000, date(2027, 4, 5), []),
        (SEED_5[:1], HISTORICO_4, 36000, date(2027, 4, 4), [(TROCA, ALTA, 21)]),
        (
            [item(1, 3, "Fluido de freio", PECA, "1", "35.00")],
            [troca(3, date(2024, 7, 1), 10000)],
            90000,
            date(2026, 6, 30),
            [(TROCA, ALTA, 1)],
        ),
        (
            [item(1, 3, "Fluido de freio", PECA, "1", "35.00")],
            [troca(3, date(2024, 7, 1), 10000)],
            10500,
            date(2026, 7, 1),
            [],
        ),
        (
            [item(1, 16, "Bobina", PECA, "1", "200.00")],
            [troca(16, date(2026, 5, 1), 36000)],
            KM_5,
            DATA_5,
            [],
        ),
        (
            [item(1, 18, "Bico injetor flex", PECA, "1", "200.00")],
            [troca(18, date(2026, 5, 1), 36000)],
            KM_5,
            DATA_5,
            [],
        ),
        (SEED_5, [], KM_5, DATA_5, []),
        (SEED_5[:1], [troca(6, date(2026, 4, 5), 35000)], KM_5, DATA_5, []),
        (
            SEED_5[:1],
            [troca(2, date(2026, 4, 5), 35000), troca(2, date(2025, 1, 10), 20000)],
            KM_5,
            DATA_5,
            [(TROCA, ALTA, 21)],
        ),
        (
            SEED_5[:1],
            [troca(2, date(2025, 1, 10), 20000), troca(2, date(2026, 4, 5), 35000)],
            KM_5,
            DATA_5,
            [(TROCA, ALTA, 21)],
        ),
        (
            SEED_5[:1],
            [troca(2, date(2026, 4, 5), 36000), troca(2, date(2026, 4, 5), 27000)],
            KM_5,
            DATA_5,
            [(TROCA, ALTA, 21)],
        ),
        (
            SEED_5[:1],
            [troca(2, date(2026, 4, 5), 27000), troca(2, date(2026, 4, 5), 36000)],
            KM_5,
            DATA_5,
            [(TROCA, ALTA, 21)],
        ),
        (
            [item(1, 2, "Troca de óleo", MAO, "1", "80.00")],
            HISTORICO_4,
            KM_5,
            DATA_5,
            [],
        ),
        (SEED_5[:1], HISTORICO_4, 30000, DATA_5, [(TROCA, ALTA, 21)]),
    ],
    ids=[
        "seed-5",
        "km-atingido",
        "um-km-antes",
        "meses-atingidos",
        "um-dia-antes-dos-meses",
        "so-meses-23",
        "so-meses-24",
        "sem-intervalo",
        "categoria-fora-dos-intervalos",
        "sem-historico",
        "historico-de-outra-categoria",
        "mais-recente-primeiro",
        "mais-recente-por-ultimo",
        "mesmo-dia-maior-km-primeiro",
        "mesmo-dia-maior-km-por-ultimo",
        "mao-de-obra-nao-gera-troca",
        "km-menor-que-o-anterior",
    ],
)
def test_troca_recente(itens, historico, km, data, esperado):
    assert (
        resumo(alerta_troca_recente(itens, historico, INTERVALOS, km, data)) == esperado
    )


def test_mensagem_da_troca():
    mensagem = alerta_troca_recente(SEED_5, HISTORICO_4, INTERVALOS, KM_5, DATA_5)[0][
        "mensagem"
    ]
    assert (
        mensagem
        == "O item 'Óleo 0W20 sintético (litro)' foi trocado há 2200 km e 1 meses."
    )


@pytest.mark.parametrize(
    ("itens", "historico", "esperado"),
    [
        (
            SEED_3,
            [],
            [
                (PRECO, ALTA, 10),
                (DUPLICADO, ALTA, 12),
                (PRECO, MEDIA, 11),
                (PRECO, MEDIA, 12),
            ],
        ),
        (
            SEED_5,
            HISTORICO_4,
            [(TROCA, ALTA, 21), (TROCA, ALTA, 22), (MAO_ALTA, MEDIA, None)],
        ),
        (SEED_11, [], [(ZERADO, ALTA, 48), (PRECO, MEDIA, 47)]),
    ],
    ids=["seed-3", "seed-5", "seed-11"],
)
def test_gerar_alertas_junta_e_ordena(itens, historico, esperado):
    alertas = gerar_alertas(itens, TETOS, historico, INTERVALOS, KM_5, DATA_5)
    assert resumo(alertas) == esperado


def test_nao_altera_o_que_recebe():
    itens, historico = copy.deepcopy(SEED_5), copy.deepcopy(HISTORICO_4)
    tetos, intervalos = dict(TETOS), dict(INTERVALOS)
    gerar_alertas(itens, tetos, historico, intervalos, KM_5, DATA_5)
    assert (itens, historico, tetos, intervalos) == (
        SEED_5,
        HISTORICO_4,
        TETOS,
        INTERVALOS,
    )
