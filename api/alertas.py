import unicodedata
from decimal import Decimal

from api.enums import SeveridadeAlertaEnum, TipoAlertaEnum, TipoItemEnum
from api.formatos import meses_entre, reais

LIMITE_MAO_OBRA = Decimal("0.50")
LIMITE_PRECO_ALTA = Decimal("0.20")
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


def alerta_preco_acima(itens, tetos):
    alertas = []

    for item in itens:
        if item["tipo"] != TipoItemEnum.PECA:
            continue
        teto = tetos.get(item["id_categoria"])
        if teto is None:
            continue
        valor = item["valor_unitario"]
        if valor <= teto:
            continue
        excesso = valor / teto - 1
        if excesso > LIMITE_PRECO_ALTA:
            severidade = SeveridadeAlertaEnum.ALTA
        else:
            severidade = SeveridadeAlertaEnum.MEDIA
        alertas.append(
            {
                "tipo": TipoAlertaEnum.PRECO_ACIMA_MEDIA,
                "severidade": severidade,
                "id_item": item["id"],
                "mensagem": f"O item '{item['descricao']}' custa {reais(valor)}, {excesso * 100:.2f}% acima do teto de referência ({reais(teto)}).",
            }
        )
    return alertas


def alerta_troca_recente(itens, historico, intervalos, km, data_emissao):
    alertas = []

    for item in itens:
        if item["tipo"] != TipoItemEnum.PECA:
            continue

        intervalo_km, intervalo_meses = intervalos.get(
            item["id_categoria"], (None, None)
        )

        if intervalo_km is None and intervalo_meses is None:
            continue

        anterior = None

        for troca in historico:
            if troca["id_categoria"] != item["id_categoria"]:
                continue

            if anterior is None or (troca["data_emissao"], troca["km"]) > (
                anterior["data_emissao"],
                anterior["km"],
            ):
                anterior = troca

        if anterior is None:
            continue

        km_rodado = km - anterior["km"]
        meses = meses_entre(anterior["data_emissao"], data_emissao)

        prazo_km_atingido = intervalo_km is not None and km_rodado >= intervalo_km

        prazo_meses_atingido = intervalo_meses is not None and meses >= intervalo_meses

        if not prazo_km_atingido and not prazo_meses_atingido:
            alertas.append(
                {
                    "tipo": TipoAlertaEnum.TROCA_RECENTE,
                    "severidade": SeveridadeAlertaEnum.ALTA,
                    "id_item": item["id"],
                    "mensagem": (
                        f"O item '{item['descricao']}' foi trocado há "
                        f"{km_rodado} km e {meses} meses."
                    ),
                }
            )

    return alertas


def gerar_alertas(itens, tetos, historico, intervalos, km, data_emissao):

    todos_alertas = []
    todos_alertas.extend(alerta_mao_obra(itens))
    todos_alertas.extend(alerta_duplicado(itens))
    todos_alertas.extend(alerta_valor_zerado(itens))
    todos_alertas.extend(alerta_preco_acima(itens, tetos))
    todos_alertas.extend(
        alerta_troca_recente(itens, historico, intervalos, km, data_emissao)
    )

    todos_alertas.sort(
        key=lambda x: (
            ORDEM_SEVERIDADE[x["severidade"]],
            x["id_item"] is None,
            x["id_item"] if x["id_item"] is not None else 0,
        )
    )

    return todos_alertas
