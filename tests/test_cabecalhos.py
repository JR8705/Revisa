from api.main import CABECALHOS_SEGURANCA


def test_cabecalhos_presentes_em_rota_publica(client):
    resposta = client.get("/")
    for nome, valor in CABECALHOS_SEGURANCA.items():
        assert resposta.headers[nome] == valor


def test_cabecalhos_presentes_em_resposta_de_erro(client):
    resposta = client.get("/veiculos/999999")
    assert resposta.status_code == 401
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
