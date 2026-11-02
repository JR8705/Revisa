from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import engine
from api.enums import StatusOrcamentoEnum, TipoItemEnum
from api.models import ItemOrcamento, Orcamento
from apoio import ID_OFICINA, contar_itens

INEXISTENTE = 2147483647


def corpo_orcamento(**mudancas):
    return {
        "id_oficina": ID_OFICINA,
        "data_emissao": date.today().isoformat(),
        "km": 31000,
        **mudancas,
    }


def contar_orcamentos(id_veiculo):
    with Session(engine) as s:
        return s.scalar(
            select(func.count())
            .select_from(Orcamento)
            .where(Orcamento.id_veiculo == id_veiculo)
        )


def inserir_itens(id_orcamento, id_categoria):
    with Session(engine) as s:
        for descricao, tipo, quantidade, valor in [
            ("Peça A", TipoItemEnum.PECA, "2.50", "10.10"),
            ("Mão de obra", TipoItemEnum.MAO_OBRA, "1.00", "100.00"),
            ("Fluido", TipoItemEnum.PECA, "3.00", "33.33"),
        ]:
            s.add(
                ItemOrcamento(
                    id_orcamento=id_orcamento,
                    id_categoria=id_categoria,
                    descricao=descricao,
                    tipo=tipo,
                    quantidade=Decimal(quantidade),
                    valor_unitario=Decimal(valor),
                )
            )
        s.commit()


def recusar_no_banco(id_orcamento):
    with Session(engine) as s:
        s.get(Orcamento, id_orcamento).status = StatusOrcamentoEnum.RECUSADO
        s.commit()


@pytest.fixture
def cenario(fabrica):
    dono = fabrica.usuario()
    intruso = fabrica.usuario()
    veic_a = fabrica.veiculo(dono)
    veic_b = fabrica.veiculo(dono)
    veic_c = fabrica.veiculo(intruso)
    return {
        "dono": dono,
        "intruso": intruso,
        "veic_a": veic_a,
        "veic_b": veic_b,
        "veic_c": veic_c,
        "orc_a": fabrica.orcamento(dono, veic_a, com_item=False),
    }


class TestCriarOrcamento:
    def test_dono_cria(self, client, cenario):
        c = cenario
        r = client.post(
            f"/veiculos/{c['veic_a']}/orcamentos",
            json=corpo_orcamento(),
            headers=c["dono"],
        )
        assert r.status_code == 201
        dados = r.json()
        assert dados["status"] == "PENDENTE"
        assert dados["id_veiculo"] == c["veic_a"]
        assert "criado_em" not in dados

    def test_sem_token(self, client, cenario):
        r = client.post(
            f"/veiculos/{cenario['veic_a']}/orcamentos", json=corpo_orcamento()
        )
        assert r.status_code == 401

    def test_intruso_no_veiculo_alheio(self, client, cenario):
        c = cenario
        antes = contar_orcamentos(c["veic_a"])
        alheio = client.post(
            f"/veiculos/{c['veic_a']}/orcamentos",
            json=corpo_orcamento(),
            headers=c["intruso"],
        )
        inexistente = client.post(
            f"/veiculos/{INEXISTENTE}/orcamentos",
            json=corpo_orcamento(),
            headers=c["intruso"],
        )
        assert alheio.status_code == inexistente.status_code == 404
        assert alheio.json() == inexistente.json()
        assert contar_orcamentos(c["veic_a"]) == antes

    @pytest.mark.parametrize(
        "mudancas",
        [
            {"id": 999},
            {"id_veiculo": 1},
            {"status": "APROVADO"},
            {"criado_em": "2020-01-01T00:00:00"},
            {"id_oficina": INEXISTENTE},
            {"id_oficina": 2**31},
            {"km": -1},
            {"km": 99999999999},
            {"data_emissao": (date.today() + timedelta(days=1)).isoformat()},
            {"data_emissao": "abc"},
        ],
        ids=lambda m: ",".join(f"{k}={v}" for k, v in m.items()),
    )
    def test_corpo_invalido_422(self, client, cenario, mudancas):
        c = cenario
        antes = contar_orcamentos(c["veic_a"])
        r = client.post(
            f"/veiculos/{c['veic_a']}/orcamentos",
            json=corpo_orcamento(**mudancas),
            headers=c["dono"],
        )
        assert r.status_code == 422
        assert contar_orcamentos(c["veic_a"]) == antes

    def test_km_menor_que_km_atual_e_aceito(self, client, cenario):
        r = client.post(
            f"/veiculos/{cenario['veic_a']}/orcamentos",
            json=corpo_orcamento(km=100),
            headers=cenario["dono"],
        )
        assert r.status_code == 201


class TestConsultarOrcamento:
    def test_dono_le_com_subtotais_e_total(self, client, cenario, id_categoria):
        c = cenario
        inserir_itens(c["orc_a"], id_categoria)
        r = client.get(
            f"/veiculos/{c['veic_a']}/orcamentos/{c['orc_a']}", headers=c["dono"]
        )
        assert r.status_code == 200
        dados = r.json()
        assert [i["subtotal"] for i in dados["itens"]] == ["25.25", "100.00", "99.99"]
        assert dados["total"] == "225.24"
        for campo in ("criado_em", "arquivo_url", "texto_extraido"):
            assert campo not in dados

    def test_sem_token(self, client, cenario):
        r = client.get(f"/veiculos/{cenario['veic_a']}/orcamentos/{cenario['orc_a']}")
        assert r.status_code == 401

    def test_404_identicos(self, client, cenario):
        c = cenario
        respostas = [
            client.get(
                f"/veiculos/{c['veic_a']}/orcamentos/{c['orc_a']}", headers=c["intruso"]
            ),
            client.get(
                f"/veiculos/{c['veic_c']}/orcamentos/{c['orc_a']}", headers=c["intruso"]
            ),
            client.get(
                f"/veiculos/{c['veic_b']}/orcamentos/{c['orc_a']}", headers=c["dono"]
            ),
            client.get(
                f"/veiculos/{INEXISTENTE}/orcamentos/{INEXISTENTE}", headers=c["dono"]
            ),
        ]
        assert {r.status_code for r in respostas} == {404}
        assert len({r.text for r in respostas}) == 1

    def test_id_invalido_422(self, client, cenario):
        r = client.get(
            f"/veiculos/{cenario['veic_a']}/orcamentos/abc", headers=cenario["dono"]
        )
        assert r.status_code == 422


class TestAdicionarItem:
    def url(self, id_veiculo, id_orcamento):
        return f"/veiculos/{id_veiculo}/orcamentos/{id_orcamento}/itens"

    def test_dono_adiciona(self, fabrica, cenario):
        c = cenario
        r = fabrica.item(c["dono"], c["veic_a"], c["orc_a"])
        assert r.status_code == 201
        assert r.json()["subtotal"] == "21.00"
        assert "id_orcamento" not in r.json()

    def test_sem_token(self, client, fabrica, cenario):
        r = client.post(
            self.url(cenario["veic_a"], cenario["orc_a"]), json=fabrica.corpo_item()
        )
        assert r.status_code == 401

    def test_404_identicos_e_nada_gravado(self, fabrica, cenario):
        c = cenario
        antes = contar_itens(c["orc_a"])
        respostas = [
            fabrica.item(c["intruso"], c["veic_a"], c["orc_a"]),
            fabrica.item(c["intruso"], c["veic_c"], c["orc_a"]),
            fabrica.item(c["dono"], c["veic_b"], c["orc_a"]),
        ]
        assert {r.status_code for r in respostas} == {404}
        assert len({r.text for r in respostas}) == 1
        assert contar_itens(c["orc_a"]) == antes

    @pytest.mark.parametrize(
        "mudancas",
        [
            {"id": 999},
            {"id_orcamento": 1},
            {"subtotal": "1.00"},
            {"id_categoria": INEXISTENTE},
            {"id_categoria": 2**31},
            {"descricao": ""},
            {"descricao": "   "},
            {"descricao": "a" * 256},
            {"quantidade": "0"},
            {"quantidade": "-1"},
            {"quantidade": "inf"},
            {"quantidade": "NaN"},
            {"valor_unitario": "-1"},
            {"valor_unitario": "99999999999"},
        ],
        ids=lambda m: ",".join(f"{k}={str(v)[:10]}" for k, v in m.items()),
    )
    def test_corpo_invalido_422(self, fabrica, cenario, mudancas):
        c = cenario
        antes = contar_itens(c["orc_a"])
        corpo = fabrica.corpo_item(**mudancas)
        r = fabrica.item(c["dono"], c["veic_a"], c["orc_a"], corpo)
        assert r.status_code == 422
        assert contar_itens(c["orc_a"]) == antes

    def test_valor_zero_e_total_recalculado(self, client, fabrica, cenario):
        c = cenario
        assert fabrica.item(c["dono"], c["veic_a"], c["orc_a"]).status_code == 201
        corpo = fabrica.corpo_item(valor_unitario="0.00")
        r = fabrica.item(c["dono"], c["veic_a"], c["orc_a"], corpo)
        assert r.status_code == 201
        r = client.get(
            f"/veiculos/{c['veic_a']}/orcamentos/{c['orc_a']}", headers=c["dono"]
        )
        assert len(r.json()["itens"]) == 2
        assert r.json()["total"] == "21.00"

    def test_orcamento_recusado_409(self, fabrica, cenario):
        c = cenario
        recusar_no_banco(c["orc_a"])
        r = fabrica.item(c["dono"], c["veic_a"], c["orc_a"])
        assert r.status_code == 409
        assert contar_itens(c["orc_a"]) == 0
