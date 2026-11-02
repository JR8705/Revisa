import secrets
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from api.database import engine

BANCO_DE_TESTE = "bdrevisa_teste"

if engine.url.database != BANCO_DE_TESTE:
    pytest.exit(
        f"Abortado: o DATABASE_URL aponta para '{engine.url.database}'. "
        f"Os testes só rodam no {BANCO_DE_TESTE}.",
        returncode=2,
    )

from api.main import app  # noqa: E402
from api.models import CategoriaItem, ItemOrcamento, Orcamento, Usuario, Veiculo  # noqa: E402
from api.seguranca import gerar_hash  # noqa: E402
from apoio import ID_OFICINA, SENHA, VEICULO_VALIDO  # noqa: E402


def contar_linhas():
    with Session(engine) as s:
        return {
            t.__tablename__: s.scalar(select(func.count()).select_from(t))
            for t in (Usuario, Veiculo, Orcamento, ItemOrcamento)
        }


@pytest.fixture(scope="session", autouse=True)
def banco_sem_lixo():
    antes = contar_linhas()
    yield
    depois = contar_linhas()
    assert depois == antes, f"Os testes deixaram lixo no banco: {antes} -> {depois}"


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def id_categoria():
    with Session(engine) as s:
        return s.scalars(select(CategoriaItem.id).order_by(CategoriaItem.id)).first()


class Fabrica:
    def __init__(self, client, id_categoria):
        self.client = client
        self.id_categoria = id_categoria
        self.emails = []

    def usuario(self):
        email = f"pytest_{uuid.uuid4().hex[:10]}@teste.com"
        self.emails.append(email)
        r = self.client.post(
            "/usuarios", json={"nome": "Teste", "email": email, "senha": SENHA}
        )
        assert r.status_code == 201, r.text
        r = self.client.post("/login", json={"email": email, "senha": SENHA})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def veiculo(self, headers, **mudancas):
        r = self.client.post(
            "/veiculos", json={**VEICULO_VALIDO, **mudancas}, headers=headers
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def orcamento(self, headers, id_veiculo, com_item=True):
        corpo = {
            "id_oficina": ID_OFICINA,
            "data_emissao": date.today().isoformat(),
            "km": 31000,
        }
        r = self.client.post(
            f"/veiculos/{id_veiculo}/orcamentos", json=corpo, headers=headers
        )
        assert r.status_code == 201, r.text
        id_orcamento = r.json()["id"]
        if com_item:
            r = self.item(headers, id_veiculo, id_orcamento)
            assert r.status_code == 201, r.text
        return id_orcamento

    def corpo_item(self, **mudancas):
        return {
            "id_categoria": self.id_categoria,
            "descricao": "Pastilha de freio",
            "tipo": "PECA",
            "quantidade": "2.00",
            "valor_unitario": "10.50",
            **mudancas,
        }

    def item(self, headers, id_veiculo, id_orcamento, corpo=None):
        return self.client.post(
            f"/veiculos/{id_veiculo}/orcamentos/{id_orcamento}/itens",
            json=corpo or self.corpo_item(),
            headers=headers,
        )

    def limpar(self):
        with Session(engine) as s:
            usuarios = select(Usuario.id).where(Usuario.email.in_(self.emails))
            veiculos = select(Veiculo.id).where(Veiculo.id_usuario.in_(usuarios))
            orcamentos = select(Orcamento.id).where(Orcamento.id_veiculo.in_(veiculos))
            s.execute(
                delete(ItemOrcamento).where(ItemOrcamento.id_orcamento.in_(orcamentos))
            )
            s.execute(delete(Orcamento).where(Orcamento.id.in_(orcamentos)))
            s.execute(delete(Veiculo).where(Veiculo.id.in_(veiculos)))
            s.execute(delete(Usuario).where(Usuario.email.in_(self.emails)))
            s.commit()


@pytest.fixture
def fabrica(client, id_categoria):
    f = Fabrica(client, id_categoria)
    yield f
    f.limpar()


@pytest.fixture
def login_seed(client):
    originais = {}

    def logar(email):
        senha = secrets.token_urlsafe(24)
        with Session(engine) as s:
            usuario = s.scalars(select(Usuario).where(Usuario.email == email)).one()
            originais.setdefault(usuario.id, usuario.senha_hash)
            usuario.senha_hash = gerar_hash(senha)
            s.commit()
        r = client.post("/login", json={"email": email, "senha": senha})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    yield logar

    with Session(engine) as s:
        for id_usuario, senha_hash in originais.items():
            s.execute(
                update(Usuario)
                .where(Usuario.id == id_usuario)
                .values(senha_hash=senha_hash)
            )
        s.commit()
