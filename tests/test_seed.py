import pytest

EMAILS_SEED = [
    "carlos.mendes@email.com",
    "ana.ribeiro@email.com",
    "marcos.teixeira@email.com",
]
DONO_DO_VEICULO_1 = "carlos.mendes@email.com"


def test_so_o_dono_enxerga_o_veiculo_1(client, login_seed):
    donos = [
        email
        for email in EMAILS_SEED
        if client.get("/veiculos/1", headers=login_seed(email)).status_code == 200
    ]
    assert donos == [DONO_DO_VEICULO_1]


def test_orcamento_3_do_seed(client, login_seed):
    r = client.get("/veiculos/1/orcamentos/3", headers=login_seed(DONO_DO_VEICULO_1))
    assert r.status_code == 200
    dados = r.json()
    assert dados["status"] == "RECUSADO"
    assert len(dados["itens"]) == 6
    assert dados["total"] == "2146.00"


def test_dono_nao_apaga_veiculo_com_orcamentos(client, login_seed):
    headers = login_seed(DONO_DO_VEICULO_1)
    assert client.delete("/veiculos/1", headers=headers).status_code == 409
    assert client.get("/veiculos/1", headers=headers).status_code == 200


@pytest.mark.parametrize("email", [e for e in EMAILS_SEED if e != DONO_DO_VEICULO_1])
def test_outros_nao_apagam_veiculo_1(client, login_seed, email):
    assert client.delete("/veiculos/1", headers=login_seed(email)).status_code == 404
    dono = login_seed(DONO_DO_VEICULO_1)
    assert client.get("/veiculos/1", headers=dono).status_code == 200
