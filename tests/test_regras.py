from datetime import date, timedelta
from decimal import Decimal

import pytest

from api.enums import StatusOrcamentoEnum, TipoCombustivelEnum
from api.regras import (
    ano_valido,
    calcular_subtotal,
    calcular_total,
    combustivel_valido,
    emissao_valida,
    transicao_valida,
)

PENDENTE = StatusOrcamentoEnum.PENDENTE
APROVADO = StatusOrcamentoEnum.APROVADO
RECUSADO = StatusOrcamentoEnum.RECUSADO


@pytest.mark.parametrize(
    ("fabricacao", "modelo", "esperado"),
    [
        (2018, 2018, True),
        (2022, 2023, True),
        (2022, 2024, False),
        (2023, 2022, False),
    ],
)
def test_ano_valido(fabricacao, modelo, esperado):
    assert ano_valido(fabricacao, modelo) is esperado


@pytest.mark.parametrize(
    ("combustivel", "cilindrada", "esperado"),
    [
        (TipoCombustivelEnum.ELETRICO, None, True),
        (TipoCombustivelEnum.ELETRICO, Decimal("1.0"), False),
        (TipoCombustivelEnum.FLEX, Decimal("1.0"), True),
        (TipoCombustivelEnum.HIBRIDO, Decimal("1.8"), True),
    ],
)
def test_combustivel_valido(combustivel, cilindrada, esperado):
    assert combustivel_valido(combustivel, cilindrada) is esperado


@pytest.mark.parametrize(("dias", "esperado"), [(-365, True), (0, True), (1, False)])
def test_emissao_valida(dias, esperado):
    assert emissao_valida(date.today() + timedelta(days=dias)) is esperado


@pytest.mark.parametrize(
    ("quantidade", "valor", "esperado"),
    [
        ("2.50", "10.10", "25.25"),
        ("1.00", "100.00", "100.00"),
        ("3.00", "33.33", "99.99"),
        ("4.20", "65.00", "273.00"),
        ("1", "0.00", "0.00"),
    ],
)
def test_calcular_subtotal(quantidade, valor, esperado):
    subtotal = calcular_subtotal(Decimal(quantidade), Decimal(valor))
    assert subtotal == Decimal(esperado)
    assert subtotal.as_tuple().exponent == -2


def test_calcular_total():
    subtotais = [Decimal("25.25"), Decimal("100.00"), Decimal("99.99")]
    assert calcular_total(subtotais) == Decimal("225.24")


def test_calcular_total_sem_itens():
    assert calcular_total([]) == Decimal("0.00")


@pytest.mark.parametrize(
    ("atual", "novo", "esperado"),
    [
        (PENDENTE, APROVADO, True),
        (PENDENTE, RECUSADO, True),
        (PENDENTE, PENDENTE, False),
        (APROVADO, RECUSADO, False),
        (APROVADO, APROVADO, False),
        (APROVADO, PENDENTE, False),
        (RECUSADO, APROVADO, False),
        (RECUSADO, RECUSADO, False),
        (RECUSADO, PENDENTE, False),
    ],
)
def test_transicao_valida(atual, novo, esperado):
    assert transicao_valida(atual, novo) is esperado
