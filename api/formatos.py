from datetime import date
from decimal import Decimal


def reais(valor: Decimal) -> str:

    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")

    return f"R$ {texto}"


def meses_entre(inicio: date, fim: date) -> int:

    meses = (fim.year - inicio.year) * 12 + (fim.month - inicio.month)

    if fim.day < inicio.day:
        meses -= 1

    return meses
