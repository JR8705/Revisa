from datetime import date
from decimal import Decimal

import pytest

from api.formatos import meses_entre, reais


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (Decimal("0"), "R$ 0,00"),
        (Decimal("590.00"), "R$ 590,00"),
        (Decimal("1500"), "R$ 1.500,00"),
        (Decimal("2146.00"), "R$ 2.146,00"),
        (Decimal("1234567.89"), "R$ 1.234.567,89"),
        (Decimal("0.5"), "R$ 0,50"),
    ],
)
def test_reais(valor, esperado):
    assert reais(valor) == esperado


@pytest.mark.parametrize(
    ("inicio", "fim", "esperado"),
    [
        (date(2026, 4, 5), date(2026, 6, 1), 1),
        (date(2026, 4, 5), date(2026, 6, 5), 2),
        (date(2025, 11, 10), date(2026, 11, 10), 12),
        (date(2025, 11, 10), date(2026, 11, 9), 11),
        (date(2026, 1, 31), date(2026, 2, 28), 0),
        (date(2026, 9, 20), date(2026, 9, 20), 0),
        (date(2026, 6, 1), date(2026, 4, 5), -2),
    ],
    ids=[
        "seed-4-para-5",
        "dois-meses-cheios",
        "um-ano",
        "um-dia-antes-do-ano",
        "fim-de-mes",
        "mesmo-dia",
        "fim-antes-do-inicio",
    ],
)
def test_meses_entre(inicio, fim, esperado):
    assert meses_entre(inicio, fim) == esperado
