import pytest
import schemathesis
from conftest import Fabrica
from hypothesis import HealthCheck, settings
from schemathesis.checks import not_a_server_error
from schemathesis.specs.openapi.checks import response_schema_conformance
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from api.database import engine
from api.main import app
from api.models import ItemOrcamento, Orcamento, Usuario, Veiculo
from apoio import SENHA, VEICULO_VALIDO, contar_itens

pytestmark = pytest.mark.fuzz

schema = schemathesis.openapi.from_asgi("/openapi.json", app)

CHECAGENS = [not_a_server_error, response_schema_conformance]
CONFIG = settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)


def apagar_usuarios_novos(ultimo_id):
    with Session(engine) as s:
        usuarios = select(Usuario.id).where(Usuario.id > ultimo_id)
        veiculos = select(Veiculo.id).where(Veiculo.id_usuario.in_(usuarios))
        orcamentos = select(Orcamento.id).where(Orcamento.id_veiculo.in_(veiculos))
        s.execute(
            delete(ItemOrcamento).where(ItemOrcamento.id_orcamento.in_(orcamentos))
        )
        s.execute(delete(Orcamento).where(Orcamento.id.in_(orcamentos)))
        s.execute(delete(Veiculo).where(Veiculo.id.in_(veiculos)))
        s.execute(delete(Usuario).where(Usuario.id > ultimo_id))
        s.commit()


@pytest.fixture(scope="module")
def dono(client, id_categoria):
    with Session(engine) as s:
        ultimo_id = s.scalar(select(func.max(Usuario.id))) or 0
    f = Fabrica(client, id_categoria)
    headers = f.usuario()
    id_veiculo = f.veiculo(headers)
    id_orcamento = f.orcamento(headers, id_veiculo)
    yield {
        "headers": headers,
        "ids": {
            "veiculo_id": id_veiculo,
            "id_veiculo": id_veiculo,
            "orcamento_id": id_orcamento,
            "id_orcamento": id_orcamento,
        },
    }
    apagar_usuarios_novos(ultimo_id)


@schema.parametrize()
@CONFIG
def test_fuzz_ids_quaisquer(case, dono):
    case.call_and_validate(headers=dono["headers"], checks=CHECAGENS)


@schema.parametrize()
@CONFIG
def test_fuzz_recursos_do_dono(case, dono):
    if case.path_parameters:
        for nome in case.path_parameters:
            if nome in dono["ids"]:
                case.path_parameters[nome] = dono["ids"][nome]
    case.call_and_validate(headers=dono["headers"], checks=CHECAGENS)


NULO = "A\x00B"


@pytest.mark.parametrize("campo", ["marca", "modelo", "motor", "placa"])
def test_byte_nulo_no_cadastro_de_veiculo(client, fabrica, campo):
    headers = fabrica.usuario()
    r = client.post("/veiculos", json={**VEICULO_VALIDO, campo: NULO}, headers=headers)
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("campo", ["marca", "modelo", "motor", "placa"])
def test_byte_nulo_na_alteracao_de_veiculo(client, fabrica, campo):
    headers = fabrica.usuario()
    id_veiculo = fabrica.veiculo(headers)
    antes = client.get(f"/veiculos/{id_veiculo}", headers=headers).json()
    r = client.patch(f"/veiculos/{id_veiculo}", json={campo: NULO}, headers=headers)
    assert r.status_code == 422, r.text
    assert client.get(f"/veiculos/{id_veiculo}", headers=headers).json() == antes


def test_byte_nulo_na_busca_por_placa(client, fabrica):
    headers = fabrica.usuario()
    r = client.get("/veiculos/placa/A%00B", headers=headers)
    assert r.status_code == 422, r.text


def test_byte_nulo_no_item(client, fabrica):
    headers = fabrica.usuario()
    id_veiculo = fabrica.veiculo(headers)
    id_orcamento = fabrica.orcamento(headers, id_veiculo, com_item=False)
    r = fabrica.item(
        headers, id_veiculo, id_orcamento, fabrica.corpo_item(descricao=NULO)
    )
    assert r.status_code == 422, r.text
    assert contar_itens(id_orcamento) == 0


def test_byte_nulo_no_cadastro_de_usuario(client):
    corpo = {"nome": NULO, "email": "nulo@teste.com", "senha": SENHA}
    assert client.post("/usuarios", json=corpo).status_code == 422
