import statistics
import time
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import update
from sqlalchemy.orm import Session

from api.config import JWT_ALGORITMO, JWT_SECRET
from api.database import engine
from api.models import Usuario
from api.seguranca import criar_token, ler_token
from apoio import (
    SENHA,
    TOKENS_FORJADOS,
    apagar_usuario,
    cabecalho,
    id_do_token,
    tokens_forjados,
)

HASH_PLACEHOLDER = "$2b$12$PLACEHOLDER.gerar.pela.aplicacao.0000000000000000000"


def assinado(payload):
    validade = datetime.now(UTC) + timedelta(minutes=5)
    return jwt.encode({**payload, "exp": validade}, JWT_SECRET, algorithm=JWT_ALGORITMO)


def test_token_ida_e_volta():
    assert ler_token(criar_token(7)) == 7


@pytest.mark.parametrize("sub", ["abc", "", "7.5"])
def test_token_com_sub_invalido(sub):
    assert ler_token(assinado({"sub": sub})) is None


def test_token_sem_sub():
    assert ler_token(assinado({})) is None


@pytest.fixture
def conta(fabrica):
    headers = fabrica.usuario()
    email = fabrica.emails[-1]
    return email, headers


def login(client, email, senha):
    return client.post("/login", json={"email": email, "senha": senha})


def test_cadastro_com_email_repetido_409(client, conta):
    corpo = {"nome": "Outro", "email": conta[0].upper(), "senha": SENHA}
    r = client.post("/usuarios", json=corpo)
    assert (r.status_code, r.json()["detail"]) == (409, "E-mail já cadastrado.")


def test_login_correto(client, conta):
    r = login(client, conta[0], SENHA)
    assert r.status_code == 200
    dados = r.json()
    assert dados["token_type"] == "bearer"  # noqa: S105
    assert ler_token(dados["access_token"]) == id_do_token(conta[1])


def test_login_erros_identicos(client, conta):
    senha_errada = login(client, conta[0], "errada-123456")
    email_inexistente = login(client, "naoexiste@teste.com", "errada-123456")
    assert senha_errada.status_code == email_inexistente.status_code == 401
    assert senha_errada.json() == email_inexistente.json()


def test_login_email_em_maiuscula(client, conta):
    assert login(client, conta[0].upper(), SENHA).status_code == 200


@pytest.mark.parametrize(
    "extra",
    [{"senha": "a" * 129}, {"admin": True}],
    ids=["senha de 129", "campo extra"],
)
def test_login_corpo_invalido(client, conta, extra):
    corpo = {"email": conta[0], "senha": SENHA, **extra}
    assert client.post("/login", json=corpo).status_code == 422


def test_login_com_hash_invalido_no_banco(client, conta):
    with Session(engine) as s:
        s.execute(
            update(Usuario)
            .where(Usuario.email == conta[0])
            .values(senha_hash=HASH_PLACEHOLDER)
        )
        s.commit()
    assert login(client, conta[0], SENHA).status_code == 401


@pytest.mark.lento
def test_login_tempo_parecido(client, conta):
    def mediana(email):
        tempos = []
        for _ in range(7):
            inicio = time.perf_counter()
            login(client, email, "errada-123456")
            tempos.append(time.perf_counter() - inicio)
        return statistics.median(tempos)

    diferenca = abs(mediana(conta[0]) - mediana("naoexiste@teste.com"))
    assert diferenca < 0.08, f"diferença de {diferenca:.3f} s denuncia e-mails"


def test_rota_protegida_com_token_valido(client, fabrica):
    headers = fabrica.usuario()
    id_veiculo = fabrica.veiculo(headers)
    assert client.get(f"/veiculos/{id_veiculo}", headers=headers).status_code == 200


@pytest.mark.parametrize("nome", TOKENS_FORJADOS)
def test_token_forjado(client, fabrica, nome):
    headers = fabrica.usuario()
    id_veiculo = fabrica.veiculo(headers)
    valor = tokens_forjados(headers)[nome]
    r = client.get(f"/veiculos/{id_veiculo}", headers=cabecalho(valor))
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == "Bearer"


def test_token_de_usuario_apagado(client, fabrica):
    headers = fabrica.usuario()
    apagar_usuario(headers)
    assert client.get("/veiculos/1", headers=headers).status_code == 401
