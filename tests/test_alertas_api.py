from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from api.database import engine
from api.enums import FontePrecoEnum
from api.models import PrecoReferencia
from apoio import (
    APROVAR,
    ID_OFICINA,
    RECUSAR,
    TOKENS_FORJADOS,
    cabecalho,
    contar_itens,
    status_no_banco,
    tokens_forjados,
)

INEXISTENTE = 2147483647
CAMPOS = {"tipo", "severidade", "id_item", "mensagem"}
OLEO = {
    "id_categoria": 2,
    "descricao": "Óleo sintético (litro)",
    "tipo": "PECA",
    "quantidade": "4.00",
    "valor_unitario": "60.00",
}


def url(id_veiculo, id_orcamento):
    return f"/veiculos/{id_veiculo}/orcamentos/{id_orcamento}/alertas"


def resumo(resposta):
    return [(a["tipo"], a["severidade"], a["id_item"]) for a in resposta.json()]


def orcamento_em(client, headers, id_veiculo, data, km, itens, decisao=None):
    corpo = {"id_oficina": ID_OFICINA, "data_emissao": data, "km": km}
    r = client.post(f"/veiculos/{id_veiculo}/orcamentos", json=corpo, headers=headers)
    assert r.status_code == 201, r.text
    id_orcamento = r.json()["id"]
    ids_itens = []
    for item in itens:
        r = client.post(
            f"/veiculos/{id_veiculo}/orcamentos/{id_orcamento}/itens",
            json=item,
            headers=headers,
        )
        assert r.status_code == 201, r.text
        ids_itens.append(r.json()["id"])
    if decisao:
        r = client.patch(
            f"/veiculos/{id_veiculo}/orcamentos/{id_orcamento}",
            json=decisao,
            headers=headers,
        )
        assert r.status_code == 200, r.text
    return id_orcamento, ids_itens


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
    def test_seed_5_troca_recente_e_mao_de_obra(self, client, login_seed):
        r = client.get(url(2, 5), headers=login_seed("carlos.mendes@email.com"))
        assert r.status_code == 200
        assert resumo(r) == [
            ("TROCA_RECENTE", "ALTA", 21),
            ("TROCA_RECENTE", "ALTA", 22),
            ("MAO_OBRA_ALTA", "MEDIA", None),
        ]
        mensagens = [a["mensagem"] for a in r.json()]
        assert "2200 km e 1 meses" in mensagens[0]
        assert "51.09" in mensagens[2]

    def test_seed_3_preco_e_duplicado(self, client, login_seed):
        r = client.get(url(1, 3), headers=login_seed("carlos.mendes@email.com"))
        assert r.status_code == 200
        assert resumo(r) == [
            ("PRECO_ACIMA_MEDIA", "ALTA", 10),
            ("ITEM_DUPLICADO", "ALTA", 12),
            ("PRECO_ACIMA_MEDIA", "MEDIA", 11),
            ("PRECO_ACIMA_MEDIA", "MEDIA", 12),
        ]
        assert "38.00%" in r.json()[0]["mensagem"]

    @pytest.mark.parametrize(
        ("email", "id_veiculo", "id_orcamento", "esperado"),
        [
            (
                "ana.ribeiro@email.com",
                4,
                8,
                [("PRECO_ACIMA_MEDIA", "MEDIA", 32)],
            ),
            (
                "marcos.teixeira@email.com",
                5,
                11,
                [("VALOR_ZERADO", "ALTA", 48), ("PRECO_ACIMA_MEDIA", "MEDIA", 47)],
            ),
            (
                "marcos.teixeira@email.com",
                6,
                13,
                [("PRECO_ACIMA_MEDIA", "ALTA", 57)],
            ),
        ],
        ids=["seed-8", "seed-11", "seed-13"],
    )
    def test_seed_preco(
        self, client, login_seed, email, id_veiculo, id_orcamento, esperado
    ):
        r = client.get(url(id_veiculo, id_orcamento), headers=login_seed(email))
        assert r.status_code == 200
        assert resumo(r) == esperado

    @pytest.mark.parametrize(
        ("email", "id_veiculo", "id_orcamento"),
        [
            ("carlos.mendes@email.com", 1, 1),
            ("carlos.mendes@email.com", 1, 2),
            ("carlos.mendes@email.com", 2, 4),
            ("carlos.mendes@email.com", 2, 14),
            ("ana.ribeiro@email.com", 3, 6),
            ("ana.ribeiro@email.com", 3, 7),
            ("ana.ribeiro@email.com", 4, 9),
            ("marcos.teixeira@email.com", 5, 10),
            ("marcos.teixeira@email.com", 6, 12),
        ],
    )
    def test_seed_sem_alertas(
        self, client, login_seed, email, id_veiculo, id_orcamento
    ):
        r = client.get(url(id_veiculo, id_orcamento), headers=login_seed(email))
        assert r.status_code == 200
        assert r.json() == []


@pytest.fixture
def faixas_extras():
    with Session(engine) as s:
        novas = [
            PrecoReferencia(
                id_categoria=10,
                codigo_peca="PYTEST-MANUAL",
                descricao="Pastilha importada",
                valor_min=Decimal("200.00"),
                valor_max=Decimal("300.00"),
                fonte=FontePrecoEnum.MANUAL,
            ),
            PrecoReferencia(
                id_categoria=10,
                descricao="Pastilha (preço dos usuários)",
                valor_min=Decimal("100.00"),
                valor_max=Decimal("1000.00"),
                fonte=FontePrecoEnum.HISTORICO,
            ),
        ]
        s.add_all(novas)
        s.commit()
        ids = [n.id for n in novas]
    yield
    with Session(engine) as s:
        s.execute(delete(PrecoReferencia).where(PrecoReferencia.id.in_(ids)))
        s.commit()


class TestPrecoETroca:
    def test_preco_acima_do_teto(self, client, cenario):
        c = cenario
        pastilha = {
            **OLEO,
            "id_categoria": 10,
            "descricao": "Pastilha",
            "quantidade": "1.00",
        }
        atual, ids = orcamento_em(
            client,
            c["dono"],
            c["veic_dono"],
            "2026-03-10",
            32000,
            [{**pastilha, "valor_unitario": "250.00"}],
        )
        r = client.get(url(c["veic_dono"], atual), headers=c["dono"])
        assert resumo(r) == [("PRECO_ACIMA_MEDIA", "ALTA", ids[0])]

    def test_teto_e_o_maior_valor_max_so_da_fonte_manual(
        self, client, cenario, faixas_extras
    ):
        c = cenario
        pastilha = {
            **OLEO,
            "id_categoria": 10,
            "descricao": "Pastilha",
            "quantidade": "1.00",
            "valor_unitario": "350.00",
        }
        atual, ids = orcamento_em(
            client, c["dono"], c["veic_dono"], "2026-03-10", 32000, [pastilha]
        )
        r = client.get(url(c["veic_dono"], atual), headers=c["dono"])
        assert resumo(r) == [("PRECO_ACIMA_MEDIA", "MEDIA", ids[0])]
        assert "(R$ 300,00)" in r.json()[0]["mensagem"]

    def test_troca_recente_no_mesmo_veiculo(self, client, cenario):
        c = cenario
        orcamento_em(
            client, c["dono"], c["veic_dono"], "2026-01-10", 30000, [OLEO], APROVAR
        )
        atual, ids = orcamento_em(
            client, c["dono"], c["veic_dono"], "2026-03-10", 32000, [OLEO]
        )
        r = client.get(url(c["veic_dono"], atual), headers=c["dono"])
        assert resumo(r) == [("TROCA_RECENTE", "ALTA", ids[0])]
        assert "2000 km e 2 meses" in r.json()[0]["mensagem"]

    @pytest.mark.parametrize(
        "decisao", [None, RECUSAR], ids=["anterior-pendente", "anterior-recusado"]
    )
    def test_anterior_nao_aprovado_nao_conta(self, client, cenario, decisao):
        c = cenario
        orcamento_em(
            client, c["dono"], c["veic_dono"], "2026-01-10", 30000, [OLEO], decisao
        )
        atual, _ = orcamento_em(
            client, c["dono"], c["veic_dono"], "2026-03-10", 32000, [OLEO]
        )
        assert client.get(url(c["veic_dono"], atual), headers=c["dono"]).json() == []

    def test_anterior_com_data_posterior_nao_conta(self, client, cenario):
        c = cenario
        orcamento_em(
            client, c["dono"], c["veic_dono"], "2026-05-10", 30000, [OLEO], APROVAR
        )
        atual, _ = orcamento_em(
            client, c["dono"], c["veic_dono"], "2026-03-10", 32000, [OLEO]
        )
        assert client.get(url(c["veic_dono"], atual), headers=c["dono"]).json() == []

    def test_km_atingido_nao_alerta(self, client, cenario):
        c = cenario
        orcamento_em(
            client, c["dono"], c["veic_dono"], "2026-01-10", 30000, [OLEO], APROVAR
        )
        atual, _ = orcamento_em(
            client, c["dono"], c["veic_dono"], "2026-03-10", 40000, [OLEO]
        )
        assert client.get(url(c["veic_dono"], atual), headers=c["dono"]).json() == []

    def test_aprovado_nao_compara_com_ele_mesmo(self, client, cenario):
        c = cenario
        atual, _ = orcamento_em(
            client, c["dono"], c["veic_dono"], "2026-03-10", 32000, [OLEO], APROVAR
        )
        assert client.get(url(c["veic_dono"], atual), headers=c["dono"]).json() == []

    def test_outro_veiculo_do_mesmo_dono_nao_conta(self, client, cenario):
        c = cenario
        orcamento_em(
            client, c["dono"], c["veic_dono_2"], "2026-01-10", 30000, [OLEO], APROVAR
        )
        atual, _ = orcamento_em(
            client, c["dono"], c["veic_dono"], "2026-03-10", 32000, [OLEO]
        )
        assert client.get(url(c["veic_dono"], atual), headers=c["dono"]).json() == []

    def test_troca_de_outro_usuario_nao_vaza(self, client, cenario):
        c = cenario
        orcamento_em(
            client,
            c["intruso"],
            c["veic_intruso"],
            "2026-01-10",
            30000,
            [OLEO],
            APROVAR,
        )
        atual, _ = orcamento_em(
            client, c["dono"], c["veic_dono"], "2026-03-10", 32000, [OLEO]
        )
        r = client.get(url(c["veic_dono"], atual), headers=c["dono"])
        assert r.json() == []
        assert "trocado" not in r.text


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
