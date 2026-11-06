import pytest

from apoio import (
    APROVAR,
    RECUSAR,
    TOKENS_FORJADOS,
    cabecalho,
    contar_itens,
    status_no_banco,
    tokens_forjados,
)

INEXISTENTE = 2147483647
CAMPOS = {"tipo", "severidade", "id_item", "mensagem"}


def url(id_veiculo, id_orcamento):
    return f"/veiculos/{id_veiculo}/orcamentos/{id_orcamento}/alertas"


@pytest.fixture
def cenario(fabrica):
    dono = fabrica.usuario()
    intruso = fabrica.usuario()
    veic_dono = fabrica.veiculo(dono)
    alvo = fabrica.orcamento(dono, veic_dono)
    r = fabrica.item(
        dono, veic_dono, alvo, fabrica.corpo_item(descricao="PASTILHA DE FREIO")
    )
    assert r.status_code == 201, r.text
    return {
        "dono": dono,
        "intruso": intruso,
        "veic_dono": veic_dono,
        "veic_dono_2": fabrica.veiculo(dono),
        "veic_intruso": fabrica.veiculo(intruso),
        "alvo": alvo,
        "id_duplicado": r.json()["id"],
    }


class TestAlertas:
    def test_dono_ve_o_duplicado(self, client, cenario):
        c = cenario
        r = client.get(url(c["veic_dono"], c["alvo"]), headers=c["dono"])
        assert r.status_code == 200
        assert r.json() == [
            {
                "tipo": "ITEM_DUPLICADO",
                "severidade": "ALTA",
                "id_item": c["id_duplicado"],
                "mensagem": r.json()[0]["mensagem"],
            }
        ]

    def test_resposta_so_com_os_quatro_campos(self, client, cenario):
        c = cenario
        for alerta in client.get(
            url(c["veic_dono"], c["alvo"]), headers=c["dono"]
        ).json():
            assert set(alerta) == CAMPOS

    def test_orcamento_vazio_lista_vazia(self, client, fabrica, cenario):
        c = cenario
        vazio = fabrica.orcamento(c["dono"], c["veic_dono"], com_item=False)
        r = client.get(url(c["veic_dono"], vazio), headers=c["dono"])
        assert r.status_code == 200
        assert r.json() == []

    def test_sem_alerta_lista_vazia(self, client, fabrica, cenario):
        c = cenario
        limpo = fabrica.orcamento(c["dono"], c["veic_dono"])
        r = client.get(url(c["veic_dono"], limpo), headers=c["dono"])
        assert r.status_code == 200
        assert r.json() == []

    def test_todos_zerados_sem_500(self, client, fabrica, cenario):
        c = cenario
        orcamento = fabrica.orcamento(c["dono"], c["veic_dono"], com_item=False)
        corpo = fabrica.corpo_item(valor_unitario="0")
        assert (
            fabrica.item(c["dono"], c["veic_dono"], orcamento, corpo).status_code == 201
        )
        r = client.get(url(c["veic_dono"], orcamento), headers=c["dono"])
        assert r.status_code == 200
        assert [a["tipo"] for a in r.json()] == ["VALOR_ZERADO"]

    @pytest.mark.parametrize(
        "decisao", [APROVAR, RECUSAR], ids=["aprovado", "recusado"]
    )
    def test_alertas_em_orcamento_decidido(self, client, cenario, decisao):
        c = cenario
        caminho = f"/veiculos/{c['veic_dono']}/orcamentos/{c['alvo']}"
        assert client.patch(caminho, json=decisao, headers=c["dono"]).status_code == 200
        r = client.get(url(c["veic_dono"], c["alvo"]), headers=c["dono"])
        assert r.status_code == 200
        assert [a["tipo"] for a in r.json()] == ["ITEM_DUPLICADO"]

    def test_get_nao_muda_nada(self, client, cenario):
        c = cenario
        antes = (status_no_banco(c["alvo"]), contar_itens(c["alvo"]))
        for _ in range(3):
            client.get(url(c["veic_dono"], c["alvo"]), headers=c["dono"])
        assert (status_no_banco(c["alvo"]), contar_itens(c["alvo"])) == antes

    @pytest.mark.parametrize("metodo", ["PUT", "POST", "PATCH", "DELETE"])
    def test_outros_metodos_405(self, client, cenario, metodo):
        c = cenario
        r = client.request(metodo, url(c["veic_dono"], c["alvo"]), headers=c["dono"])
        assert r.status_code == 405
        assert contar_itens(c["alvo"]) == 2


class TestSeed:
    def test_seed_5_mao_de_obra(self, client, login_seed):
        r = client.get(url(2, 5), headers=login_seed("carlos.mendes@email.com"))
        assert r.status_code == 200
        alertas = r.json()
        assert [(a["tipo"], a["severidade"], a["id_item"]) for a in alertas] == [
            ("MAO_OBRA_ALTA", "MEDIA", None)
        ]
        assert "51.09" in alertas[0]["mensagem"]

    def test_seed_3_duplicado(self, client, login_seed):
        r = client.get(url(1, 3), headers=login_seed("carlos.mendes@email.com"))
        assert r.status_code == 200
        assert [(a["tipo"], a["id_item"]) for a in r.json()] == [("ITEM_DUPLICADO", 12)]

    def test_seed_1_sem_alertas(self, client, login_seed):
        r = client.get(url(1, 1), headers=login_seed("carlos.mendes@email.com"))
        assert r.status_code == 200
        assert r.json() == []


class TestIds:
    @pytest.mark.parametrize(
        ("valor", "esperado"),
        [
            ("0", 422),
            ("-1", 422),
            ("1.0", 404),
            ("1e3", 422),
            ("1 OR 1=1", 422),
            ("abc", 422),
            (str(2**31), 422),
            ("9" * 30, 422),
        ],
    )
    def test_id_adulterado_no_caminho(self, client, cenario, valor, esperado):
        c = cenario
        no_orcamento = client.get(url(c["veic_dono"], valor), headers=c["dono"])
        no_veiculo = client.get(url(valor, c["alvo"]), headers=c["dono"])
        assert no_orcamento.status_code == esperado
        assert no_veiculo.status_code == esperado


class TestPosse:
    def test_sem_token_401(self, client, cenario):
        assert client.get(url(cenario["veic_dono"], cenario["alvo"])).status_code == 401

    def test_404_identicos(self, client, cenario):
        c = cenario
        respostas = [
            client.get(url(c["veic_intruso"], INEXISTENTE), headers=c["intruso"]),
            client.get(url(c["veic_dono"], c["alvo"]), headers=c["intruso"]),
            client.get(url(c["veic_intruso"], c["alvo"]), headers=c["intruso"]),
            client.get(url(c["veic_dono_2"], c["alvo"]), headers=c["dono"]),
            client.get(url(INEXISTENTE, INEXISTENTE), headers=c["dono"]),
        ]
        assert {r.status_code for r in respostas} == {404}
        assert len({r.text for r in respostas}) == 1

    def test_intruso_nao_ve_alerta_do_seed(self, client, cenario):
        r = client.get(url(2, 5), headers=cenario["intruso"])
        assert r.status_code == 404
        assert "MAO_OBRA" not in r.text

    @pytest.mark.parametrize("nome", TOKENS_FORJADOS)
    def test_token_forjado_401(self, client, cenario, nome):
        c = cenario
        valor = tokens_forjados(c["dono"])[nome]
        r = client.get(url(c["veic_dono"], c["alvo"]), headers=cabecalho(valor))
        assert r.status_code == 401
