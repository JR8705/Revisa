import time
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from api.config import JWT_ALGORITMO, JWT_SECRET
from api.database import engine
from api.models import ItemOrcamento, Orcamento, Usuario

SENHA = "senhaSegura123"
ID_OFICINA = 1
APROVAR = {"status": "APROVADO"}
RECUSAR = {"status": "RECUSADO"}
VEICULO_VALIDO = {
    "marca": "Fiat",
    "modelo": "Argo",
    "motor": "Firefly",
    "placa": "TST1A23",
    "combustivel": "FLEX",
    "cilindrada": "1.3",
    "turbo": False,
    "ano_fabricacao": 2021,
    "ano_modelo": 2022,
    "km_atual": 30000,
}


def token_de(headers):
    return headers["Authorization"].removeprefix("Bearer ")


def id_do_token(headers):
    payload = jwt.decode(token_de(headers), JWT_SECRET, algorithms=[JWT_ALGORITMO])
    return int(payload["sub"])


def cabecalho(valor):
    return {} if valor is None else {"Authorization": valor}


def apagar_usuario(headers):
    with Session(engine) as s:
        s.execute(delete(Usuario).where(Usuario.id == id_do_token(headers)))
        s.commit()


def status_no_banco(id_orcamento):
    with Session(engine) as s:
        return s.get(Orcamento, id_orcamento).status.value


def contar_itens(id_orcamento):
    with Session(engine) as s:
        return s.scalar(
            select(func.count())
            .select_from(ItemOrcamento)
            .where(ItemOrcamento.id_orcamento == id_orcamento)
        )


def tokens_forjados(headers_validos):
    id_usuario = str(id_do_token(headers_validos))
    validade = datetime.now(UTC) + timedelta(minutes=30)
    token = token_de(headers_validos)
    meio = len(token) // 2
    trocado = token[:meio] + ("A" if token[meio] != "A" else "B") + token[meio + 1 :]

    def assinar(payload, chave=JWT_SECRET, alg="HS256"):
        return "Bearer " + jwt.encode(payload, chave, algorithm=alg)

    return {
        "sem cabeçalho": None,
        "texto qualquer": "Bearer TOKEN",
        "sem a palavra Bearer": token,
        "um caractere trocado": "Bearer " + trocado,
        "assinatura cortada": "Bearer " + token[:-5],
        "chave errada": assinar({"sub": id_usuario, "exp": validade}, "x" * 40),
        "alg none": assinar({"sub": id_usuario, "exp": validade}, None, "none"),
        "sem exp": assinar({"sub": id_usuario}),
        "expirado": assinar({"sub": id_usuario, "exp": int(time.time()) - 60}),
        "sub não numérico": assinar({"sub": "abc", "exp": validade}),
        "sem sub": assinar({"exp": validade}),
    }


TOKENS_FORJADOS = [
    "sem cabeçalho",
    "texto qualquer",
    "sem a palavra Bearer",
    "um caractere trocado",
    "assinatura cortada",
    "chave errada",
    "alg none",
    "sem exp",
    "expirado",
    "sub não numérico",
    "sem sub",
]
