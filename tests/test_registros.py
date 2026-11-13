from apoio import VEICULO_VALIDO


def test_erro_do_banco_vai_para_o_log_sem_os_dados(client, fabrica, caplog):
    headers = fabrica.usuario()
    id_veiculo = fabrica.veiculo(headers)
    fabrica.orcamento(headers, id_veiculo)
    with caplog.at_level("WARNING", logger="revisa"):
        r = client.delete(f"/veiculos/{id_veiculo}", headers=headers)
    assert r.status_code == 409
    assert "DELETE /veiculos" in caplog.text
    assert "ForeignKeyViolation" in caplog.text
    assert "orcamentos_id_veiculo_fkey" in caplog.text
    assert VEICULO_VALIDO["placa"] not in caplog.text
    assert "DELETE FROM" not in caplog.text


def test_cadastro_repetido_vai_para_o_log_sem_o_email(client, fabrica, caplog):
    fabrica.usuario()
    email = fabrica.emails[-1]
    corpo = {"nome": "Teste", "email": email, "senha": "senhaSegura123"}
    with caplog.at_level("WARNING", logger="revisa"):
        r = client.post("/usuarios", json=corpo)
    assert r.status_code == 409
    assert "POST /usuarios" in caplog.text
    assert "UniqueViolation" in caplog.text
    assert email not in caplog.text
    assert "senhaSegura123" not in caplog.text
