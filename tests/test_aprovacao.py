import threading

import pytest

from apoio import (
    APROVAR,
    RECUSAR,
    TOKENS_FORJADOS,
    apagar_usuario,
    cabecalho,
    status_no_banco,
    tokens_forjados,
)

MSG_409 = "Não é possível alterar este orçamento."
CAMPOS_RESPOSTA = {"id", "id_veiculo", "id_oficina", "data_emissao", "km", "status"}


def url(id_veiculo, id_orcamento):
    return f"/veiculos/{id_veiculo}/orcamentos/{id_orcamento}"


@pytest.fixture
def cenario(fabrica):
    dono = fabrica.usuario()
    intruso = fabrica.usuario()
    veic_dono = fabrica.veiculo(dono)
    return {
        "dono": dono,
        "intruso": intruso,
        "veic_dono": veic_dono,
        "veic_dono_2": fabrica.veiculo(dono),
        "veic_intruso": fabrica.veiculo(intruso),
        "alvo": fabrica.orcamento(dono, veic_dono),
    }


@pytest.fixture
def alterar(client, cenario):
    def patch(corpo, id_orcamento=None, headers=None, id_veiculo=None):
        return client.patch(
            url(id_veiculo or cenario["veic_dono"], id_orcamento or cenario["alvo"]),
            json=corpo,
            headers=cenario["dono"] if headers is None else headers,
        )

    return patch


class TestFluxo:
    def test_dono_aprova(self, client, cenario, alterar):
        r = alterar(APROVAR)
        assert r.status_code == 200
        assert r.json()["status"] == "APROVADO"
        assert set(r.json()) == CAMPOS_RESPOSTA
        assert status_no_banco(cenario["alvo"]) == "APROVADO"
        r = client.get(
            url(cenario["veic_dono"], cenario["alvo"]), headers=cenario["dono"]
        )
        assert r.json()["status"] == "APROVADO"

    def test_dono_recusa_sem_itens(self, fabrica, cenario, alterar):
        c = cenario
        vazio = fabrica.orcamento(c["dono"], c["veic_dono"], com_item=False)
        assert alterar(RECUSAR, vazio).status_code == 200
        assert status_no_banco(vazio) == "RECUSADO"

    def test_aprovar_sem_itens_409(self, fabrica, cenario, alterar):
        c = cenario
        vazio = fabrica.orcamento(c["dono"], c["veic_dono"], com_item=False)
        r = alterar(APROVAR, vazio)
        assert (r.status_code, r.json()["detail"]) == (409, MSG_409)
        assert status_no_banco(vazio) == "PENDENTE"

    @pytest.mark.parametrize(
        ("primeira", "segunda"),
        [
            (APROVAR, APROVAR),
            (APROVAR, RECUSAR),
            (RECUSAR, APROVAR),
            (RECUSAR, RECUSAR),
        ],
        ids=[
            "aprovado-aprovar",
            "aprovado-recusar",
            "recusado-aprovar",
            "recusado-recusar",
        ],
    )
    def test_estado_final_nao_muda(self, cenario, alterar, primeira, segunda):
        assert alterar(primeira).status_code == 200
        r = alterar(segunda)
        assert (r.status_code, r.json()["detail"]) == (409, MSG_409)
        assert status_no_banco(cenario["alvo"]) == primeira["status"]

    def test_item_em_orcamento_aprovado_409(self, fabrica, cenario, alterar):
        assert alterar(APROVAR).status_code == 200
        r = fabrica.item(cenario["dono"], cenario["veic_dono"], cenario["alvo"])
        assert r.status_code == 409


class TestCorpo:
    @pytest.mark.parametrize(
        "corpo",
        [
            {"status": "PENDENTE"},
            {"status": "PAGO"},
            {"status": "aprovado"},
            {},
            {"status": "APROVADO", "id": 999},
            {"status": "APROVADO", "total": "0.00"},
            {"status": "APROVADO", "id_veiculo": 1},
            {"status": None},
            {"status": 1},
            {"status": True},
            {"status": ["APROVADO"]},
            {"status": {"valor": "APROVADO"}},
            {"status": "APROVADO "},
            {"status": " APROVADO"},
            {"status": "Aprovado"},
            {"status": "АPROVADO"},
            {"status": "APROVADO\u0000"},
            {"status": "StatusOrcamentoEnum.APROVADO"},
            {"status": "A" * 100_000},
            "APROVADO",
            [APROVAR],
        ],
        ids=lambda c: repr(c)[:40],
    )
    def test_corpo_invalido_422(self, cenario, alterar, corpo):
        assert alterar(corpo).status_code == 422
        assert status_no_banco(cenario["alvo"]) == "PENDENTE"

    @pytest.mark.parametrize("valor", ["Infinity", "NaN", "-Infinity"])
    def test_json_com_infinity_cru_422(self, client, cenario, valor):
        c = cenario
        r = client.patch(
            url(c["veic_dono"], c["alvo"]),
            content=f'{{"status": {valor}}}',
            headers={**c["dono"], "Content-Type": "application/json"},
        )
        assert r.status_code == 422
        assert status_no_banco(c["alvo"]) == "PENDENTE"

    def test_formulario_e_query_422(self, client, cenario):
        c = cenario
        caminho = url(c["veic_dono"], c["alvo"])
        assert client.patch(caminho, data=APROVAR, headers=c["dono"]).status_code == 422
        assert (
            client.patch(caminho + "?status=APROVADO", headers=c["dono"]).status_code
            == 422
        )
        assert status_no_banco(c["alvo"]) == "PENDENTE"

    @pytest.mark.parametrize("metodo", ["PUT", "POST", "DELETE"])
    def test_outros_metodos_405(self, client, cenario, metodo):
        c = cenario
        r = client.request(
            metodo, url(c["veic_dono"], c["alvo"]), json=APROVAR, headers=c["dono"]
        )
        assert r.status_code == 405
        assert status_no_banco(c["alvo"]) == "PENDENTE"


class TestIds:
    @pytest.mark.parametrize(
        ("valor", "esperado"),
        [
            ("0", 422),
            ("-1", 422),
            ("1.0", 404),
            ("1e3", 422),
            ("0x1", 422),
            ("1 OR 1=1", 422),
            ("abc", 422),
            (str(2**31), 422),
            (str(2**63), 422),
            ("9" * 30, 422),
        ],
    )
    def test_id_adulterado_no_caminho(self, client, cenario, valor, esperado):
        c = cenario
        no_orcamento = client.patch(
            f"/veiculos/{c['veic_dono']}/orcamentos/{valor}",
            json=APROVAR,
            headers=c["dono"],
        )
        no_veiculo = client.patch(
            f"/veiculos/{valor}/orcamentos/{c['alvo']}", json=APROVAR, headers=c["dono"]
        )
        assert no_orcamento.status_code == esperado
        assert no_veiculo.status_code == esperado
        assert status_no_banco(c["alvo"]) == "PENDENTE"


class TestPosse:
    def test_sem_token_401(self, client, cenario):
        r = client.patch(url(cenario["veic_dono"], cenario["alvo"]), json=APROVAR)
        assert r.status_code == 401

    def test_404_identicos(self, fabrica, cenario, alterar):
        c = cenario
        aprovado = fabrica.orcamento(c["dono"], c["veic_dono"])
        recusado = fabrica.orcamento(c["dono"], c["veic_dono"])
        vazio = fabrica.orcamento(c["dono"], c["veic_dono"], com_item=False)
        assert alterar(APROVAR, aprovado).status_code == 200
        assert alterar(RECUSAR, recusado).status_code == 200

        intruso = c["intruso"]
        respostas = [alterar(APROVAR, 2147483647, intruso, c["veic_intruso"])]
        for id_orcamento in (c["alvo"], aprovado, recusado, vazio):
            respostas.append(alterar(APROVAR, id_orcamento, intruso))
            respostas.append(alterar(APROVAR, id_orcamento, intruso, c["veic_intruso"]))
        respostas.append(alterar(APROVAR, c["alvo"], c["dono"], c["veic_dono_2"]))
        respostas.append(alterar(APROVAR, 2147483647, c["dono"], 2147483647))

        assert {r.status_code for r in respostas} == {404}
        assert len({r.text for r in respostas}) == 1
        assert status_no_banco(c["alvo"]) == "PENDENTE"

    @pytest.mark.parametrize("nome", TOKENS_FORJADOS)
    def test_token_forjado_401(self, cenario, alterar, nome):
        valor = tokens_forjados(cenario["dono"])[nome]
        assert alterar(APROVAR, headers=cabecalho(valor)).status_code == 401
        assert status_no_banco(cenario["alvo"]) == "PENDENTE"

    def test_token_de_usuario_apagado_401(self, fabrica, cenario, alterar):
        apagado = fabrica.usuario()
        apagar_usuario(apagado)
        assert alterar(APROVAR, headers=apagado).status_code == 401


@pytest.mark.lento
def test_corrida_aprovar_e_recusar(fabrica, cenario, alterar):
    c = cenario
    duplas = 0
    rodadas = 15
    for _ in range(rodadas):
        id_orcamento = fabrica.orcamento(c["dono"], c["veic_dono"])
        largada = threading.Barrier(2)
        resultados = []

        def disparar(
            corpo, id_orcamento=id_orcamento, largada=largada, resultados=resultados
        ):
            largada.wait()
            resultados.append(alterar(corpo, id_orcamento).status_code)

        fios = [
            threading.Thread(target=disparar, args=(corpo,))
            for corpo in (APROVAR, RECUSAR)
        ]
        for fio in fios:
            fio.start()
        for fio in fios:
            fio.join()
        assert sorted(resultados) == [200, 409], resultados
        duplas += resultados.count(200) == 2
    assert duplas == 0, f"{duplas} de {rodadas} rodadas aceitaram duas decisões"
