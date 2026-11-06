import unicodedata
from decimal import Decimal

from api.enums import SeveridadeAlertaEnum, TipoAlertaEnum, TipoItemEnum

LIMITE_MAO_OBRA = Decimal("0.50")
ORDEM_SEVERIDADE = {
    SeveridadeAlertaEnum.ALTA: 0,
    SeveridadeAlertaEnum.MEDIA: 1,
    SeveridadeAlertaEnum.BAIXA: 2,
}


def normalizar_descricao(texto: str) -> str:

    texto_decomposto = unicodedata.normalize("NFD", texto)

    caracteres_limpos = []
    for caractere in texto_decomposto:
        if caractere.isalnum():
            caracteres_limpos.append(caractere.lower())

    texto_final = "".join(caracteres_limpos)
    return unicodedata.normalize("NFC", texto_final)


def alerta_mao_obra(itens, limite=LIMITE_MAO_OBRA):

    total_geral = Decimal("0.00")
    total_mao_obra = Decimal("0.00")

    for item in itens:
        valor_total_item = item["subtotal"]
        total_geral += valor_total_item

        if item["tipo"] == TipoItemEnum.MAO_OBRA:
            total_mao_obra += valor_total_item

    if total_geral == 0:
        return []

    proporcao = total_mao_obra / total_geral
    if proporcao > limite:
        return [
            {
                "tipo": TipoAlertaEnum.MAO_OBRA_ALTA,
                "severidade": SeveridadeAlertaEnum.MEDIA,
                "id_item": None,
                "mensagem": f"Mão de obra representa {proporcao * 100:.2f}% do total (limite de {limite * 100:.0f}%).",
            }
        ]

    return []


def alerta_duplicado(itens):

    alertas = []
    vistos = set()

    for item in itens:
        descricao_normalizada = normalizar_descricao(item["descricao"])
        chave_item = descricao_normalizada

        if chave_item in vistos:
            alertas.append(
                {
                    "tipo": TipoAlertaEnum.ITEM_DUPLICADO,
                    "severidade": SeveridadeAlertaEnum.ALTA,
                    "id_item": item["id"],
                    "mensagem": f"O item '{item.get('descricao')}' está duplicado no orçamento.",
                }
            )
        else:
            vistos.add(chave_item)

    return alertas


def alerta_valor_zerado(itens):

    alertas = []

    for item in itens:
        valor = item["valor_unitario"]
        if valor == 0:
            alertas.append(
                {
                    "tipo": TipoAlertaEnum.VALOR_ZERADO,
                    "severidade": SeveridadeAlertaEnum.ALTA,
                    "id_item": item["id"],
                    "mensagem": f"O item '{item.get('descricao')}' possui valor zerado.",
                }
            )

    return alertas


def gerar_alertas(itens):

    todos_alertas = []
    todos_alertas.extend(alerta_mao_obra(itens))
    todos_alertas.extend(alerta_duplicado(itens))
    todos_alertas.extend(alerta_valor_zerado(itens))

    todos_alertas.sort(
        key=lambda x: (
            ORDEM_SEVERIDADE[x["severidade"]],
            x["id_item"] is None,
            x["id_item"] if x["id_item"] is not None else 0,
        )
    )

    return todos_alertas
