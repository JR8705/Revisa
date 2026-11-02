from urllib.parse import quote

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import engine
from api.models import Veiculo
from apoio import VEICULO_VALIDO, id_do_token

CAMPOS_PROIBIDOS = {"placa", "id_usuario", "criado_em"}
MSG_ELETRICO = "Veículo elétrico não tem cilindrada."


def dono_no_banco(id_veiculo):
    with Session(engine) as s:
        return s.get(Veiculo, id_veiculo).id_usuario


@pytest.fixture
def dois(fabrica):
    return fabrica.usuario(), fabrica.usuario()


def test_criar_grava_o_dono_do_token(client, fabrica, dois):
    a, b = dois
    assert dono_no_banco(fabrica.veiculo(a)) == id_do_token(a)
    assert dono_no_banco(fabrica.veiculo(b)) == id_do_token(b)


@pytest.mark.parametrize(
    "extra",
    [{"id": 99}, {"id_usuario": 1}, {"criado_em": "2001-01-01T00:00:00"}],
    ids=["id", "id_usuario", "criado_em"],
)
def test_criar_recusa_campo_proibido(client, dois, extra):
    r = client.post("/veiculos", json={**VEICULO_VALIDO, **extra}, headers=dois[0])
    assert r.status_code == 422


def test_resposta_sem_campos_internos(client, fabrica, dois):
    a = dois[0]
    r = client.post("/veiculos", json=VEICULO_VALIDO, headers=a)
    assert not set(r.json()) & CAMPOS_PROIBIDOS
    r = client.patch(f"/veiculos/{r.json()['id']}", json={"km_atual": 31000}, headers=a)
    assert not set(r.json()) & CAMPOS_PROIBIDOS


def test_dono_le_por_id_e_placa(client, fabrica, dois):
    a = dois[0]
    id_veiculo = fabrica.veiculo(a, placa=" pat1a23 ")
    assert client.get(f"/veiculos/{id_veiculo}", headers=a).status_code == 200
    r = client.get("/veiculos/placa/PAT1A23", headers=a)
    assert r.status_code == 200
    assert [v["id"] for v in r.json()] == [id_veiculo]


def test_outro_usuario_nao_enxerga(client, fabrica, dois):
    a, b = dois
    id_veiculo = fabrica.veiculo(a, placa="OUT1A23")
    alheio = client.get(f"/veiculos/{id_veiculo}", headers=b)
    inexistente = client.get("/veiculos/2147483647", headers=b)
    assert alheio.status_code == inexistente.status_code == 404
    assert alheio.json() == inexistente.json()
    assert client.get("/veiculos/placa/OUT1A23", headers=b).status_code == 404


def test_outro_usuario_nao_altera_nem_apaga(client, fabrica, dois):
    a, b = dois
    id_veiculo = fabrica.veiculo(a)
    r = client.patch(f"/veiculos/{id_veiculo}", json={"marca": "Alterada"}, headers=b)
    assert r.status_code == 404
    assert client.delete(f"/veiculos/{id_veiculo}", headers=b).status_code == 404
    r = client.get(f"/veiculos/{id_veiculo}", headers=a)
    assert r.status_code == 200
    assert r.json()["marca"] == VEICULO_VALIDO["marca"]


def test_patch_nao_troca_o_dono(client, fabrica, dois):
    a, b = dois
    id_veiculo = fabrica.veiculo(a)
    r = client.patch(
        f"/veiculos/{id_veiculo}", json={"id_usuario": id_do_token(b)}, headers=a
    )
    assert r.status_code == 422
    assert dono_no_banco(id_veiculo) == id_do_token(a)


@pytest.mark.parametrize(
    ("corpo", "esperado"),
    [
        ({"km_atual": 105000}, 200),
        ({}, 200),
        ({"placa": None}, 200),
        ({"marca": None}, 422),
        ({"combustivel": "ELETRICO"}, 422),
        ({"ano_modelo": 2025}, 422),
        ({"modelo": "A" * 10000}, 422),
        ({"placa": "' OR '1'='1"}, 422),
        ({"cilindrada": "inf"}, 422),
        ({"cilindrada": "NaN"}, 422),
        ({"cilindrada": "100"}, 422),
        ({"turbo": "talvez"}, 422),
        ({"km_atual": 99999999999}, 422),
    ],
    ids=lambda v: str(v)[:30] if isinstance(v, dict) else str(v),
)
def test_patch(client, fabrica, dois, corpo, esperado):
    a = dois[0]
    id_veiculo = fabrica.veiculo(a, ano_fabricacao=2018, ano_modelo=2018)
    antes = client.get(f"/veiculos/{id_veiculo}", headers=a).json()
    r = client.patch(f"/veiculos/{id_veiculo}", json=corpo, headers=a)
    assert r.status_code == esperado
    depois = client.get(f"/veiculos/{id_veiculo}", headers=a).json()
    if esperado == 422:
        assert depois == antes
    elif "km_atual" in corpo:
        assert depois["km_atual"] == corpo["km_atual"]


def test_patch_inexistente(client, dois):
    r = client.patch("/veiculos/2147483647", json={"km_atual": 1}, headers=dois[0])
    assert r.status_code == 404


def test_patch_placa_normalizada(client, fabrica, dois):
    a = dois[0]
    id_veiculo = fabrica.veiculo(a, placa="PAT1A23")
    r = client.patch(f"/veiculos/{id_veiculo}", json={"placa": " xyz1k99 "}, headers=a)
    assert r.status_code == 200
    ids = [v["id"] for v in client.get("/veiculos/placa/XYZ1K99", headers=a).json()]
    assert id_veiculo in ids
    assert client.get("/veiculos/placa/PAT1A23", headers=a).status_code == 404


def test_regra_do_eletrico_no_patch(client, fabrica, dois):
    a = dois[0]
    id_veiculo = fabrica.veiculo(a)
    url = f"/veiculos/{id_veiculo}"

    r = client.patch(url, json={"combustivel": "ELETRICO"}, headers=a)
    assert (r.status_code, r.json()["detail"]) == (422, MSG_ELETRICO)

    r = client.patch(
        url, json={"combustivel": "ELETRICO", "cilindrada": None}, headers=a
    )
    assert r.status_code == 200

    r = client.patch(url, json={"cilindrada": "1.5"}, headers=a)
    assert (r.status_code, r.json()["detail"]) == (422, MSG_ELETRICO)


def test_sql_injection_na_marca_vira_texto(client, fabrica, dois):
    a = dois[0]
    ataque = "'; DROP TABLE veiculos;--"
    id_veiculo = fabrica.veiculo(a, marca=ataque)
    assert client.get(f"/veiculos/{id_veiculo}", headers=a).json()["marca"] == ataque
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Veiculo)) > 0


def test_injecao_na_placa_nao_vaza(client, fabrica, dois):
    a = dois[0]
    id_veiculo = fabrica.veiculo(a)
    ataque = "'OR 1=1--"
    assert (
        client.patch(f"/veiculos/{id_veiculo}", json={"placa": ataque}, headers=a)
    ).status_code == 200
    r = client.get(f"/veiculos/placa/{quote(ataque)}", headers=a)
    assert [v["id"] for v in r.json()] == [id_veiculo]


def test_apagar(client, fabrica, dois):
    a = dois[0]
    id_veiculo = fabrica.veiculo(a)
    assert client.delete(f"/veiculos/{id_veiculo}", headers=a).status_code == 204
    assert client.get(f"/veiculos/{id_veiculo}", headers=a).status_code == 404
    assert client.delete(f"/veiculos/{id_veiculo}", headers=a).status_code == 404


def test_apagar_com_orcamento_409(client, fabrica, dois):
    a = dois[0]
    id_veiculo = fabrica.veiculo(a)
    fabrica.orcamento(a, id_veiculo)
    r = client.delete(f"/veiculos/{id_veiculo}", headers=a)
    assert r.status_code == 409
    assert client.get(f"/veiculos/{id_veiculo}", headers=a).status_code == 200


@pytest.mark.parametrize("metodo", ["GET", "PATCH", "DELETE"])
def test_sem_token_401(client, fabrica, dois, metodo):
    id_veiculo = fabrica.veiculo(dois[0])
    r = client.request(metodo, f"/veiculos/{id_veiculo}", json={"marca": "Outra"})
    assert r.status_code == 401


def test_cilindrada_opcional_na_combustao(client, dois):
    corpo = {**VEICULO_VALIDO, "cilindrada": None}
    r = client.post("/veiculos", json=corpo, headers=dois[0])
    assert r.status_code == 201
    assert r.json()["cilindrada"] is None


def test_criar_sem_token_401(client):
    assert client.post("/veiculos", json=VEICULO_VALIDO).status_code == 401
