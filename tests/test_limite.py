import threading
import time
import types

import pytest

from api import config
from api.limite import (
    HASHES_SIMULTANEOS,
    VARRER_A_CADA,
    RegistroTentativas,
    tentativas,
)
from api.regras import espera_em_segundos, tentativas_recentes
from apoio import SENHA

MENSAGEM = "Muitas tentativas. Tente novamente mais tarde."
SENHA_ERRADA = "senhaErrada123"


@pytest.mark.parametrize(
    "momentos, agora, limite, janela, esperado",
    [
        ([], 100, 5, 900, 0),
        ([10, 20, 30, 40], 100, 5, 900, 0),
        ([10, 20, 30, 40, 50], 100, 5, 900, 810),
        ([10, 20, 30, 40, 50], 910, 5, 900, 0),
        ([10, 20, 30, 40, 50], 909.5, 5, 900, 1),
        ([10, 20, 30, 40, 50], 909.99, 5, 900, 1),
        ([50, 10, 40, 20, 30], 100, 5, 900, 810),
        ([10, 20, 30, 40, 50, 60], 100, 5, 900, 810),
        ([99.9], 100, 1, 900, 900),
        ([1, 2, 3, 950], 1000, 2, 900, 0),
    ],
)
def test_espera_em_segundos(momentos, agora, limite, janela, esperado):
    obtido = espera_em_segundos(momentos, agora, limite, janela)
    assert obtido == esperado
    assert type(obtido) is int


@pytest.mark.parametrize(
    "momentos, esperado",
    [
        ([10, 500, 950], [500, 950]),
        ([100], []),
        ([100.1], [100.1]),
        ([], []),
        ([1, 2, 3], []),
    ],
)
def test_tentativas_recentes(momentos, esperado):
    assert tentativas_recentes(momentos, 1000, 900) == esperado


def test_tentativas_recentes_nao_altera_a_lista_recebida():
    momentos = [10, 500, 950]
    tentativas_recentes(momentos, 1000, 900)
    assert momentos == [10, 500, 950]


@pytest.fixture
def relogio(monkeypatch):
    agora = [1000.0]
    monkeypatch.setattr(
        "api.limite.time", types.SimpleNamespace(monotonic=lambda: agora[0])
    )
    return agora


def test_registro_bloqueia_libera_e_limpa(relogio):
    registro = RegistroTentativas()
    for _ in range(5):
        registro.registrar("a")
    assert registro.espera("a", 5, 900) == 900
    assert registro.espera("b", 5, 900) == 0
    relogio[0] += 900
    assert registro.espera("a", 5, 900) == 0
    relogio[0] -= 900
    registro.limpar_chave("a")
    registro.limpar_chave("nao-existe")
    assert registro.espera("a", 5, 900) == 0


def test_tentar_checa_e_registra_de_uma_vez(relogio):
    registro = RegistroTentativas()
    regras = [("a", 2, 900), ("b", 3, 900)]
    assert [registro.tentar(regras) for _ in range(3)] == [0, 0, 900]
    assert (len(registro._momentos["a"]), len(registro._momentos["b"])) == (2, 2)
    registro.devolver("b")
    registro.devolver("nao-existe")
    assert len(registro._momentos["b"]) == 1
    assert registro.tentar([("b", 3, 900)]) == 0


def test_registro_varre_chaves_vencidas(relogio):
    registro = RegistroTentativas()
    registro.registrar("antiga")
    relogio[0] += max(config.JANELA_LOGIN, config.JANELA_CADASTRO)
    for _ in range(VARRER_A_CADA):
        registro.registrar("nova")
    assert "antiga" not in registro._momentos
    assert len(registro._momentos["nova"]) == VARRER_A_CADA


@pytest.fixture
def limite_real(monkeypatch):
    for nome in ("LIMITE_LOGIN_EMAIL", "LIMITE_LOGIN_IP", "LIMITE_CADASTRO_IP"):
        monkeypatch.setattr(f"api.main.{nome}", getattr(config, nome))


@pytest.fixture
def conta(fabrica):
    fabrica.usuario()
    tentativas.limpar()
    return fabrica.emails[-1]


def login(client, email, senha=SENHA_ERRADA, **extras):
    return client.post("/login", json={"email": email, "senha": senha}, **extras)


def cadastro(client, fabrica, email=None):
    if email is None:
        email = f"pytest_limite_{len(fabrica.emails)}_{id(fabrica)}@teste.com"
        fabrica.emails.append(email)
    corpo = {"nome": "Teste", "email": email, "senha": SENHA}
    return client.post("/usuarios", json=corpo)


def conferir_429(r, espera_maxima):
    assert r.status_code == 429, r.text
    assert r.json() == {"detail": MENSAGEM}
    assert 0 < int(r.headers["retry-after"]) <= espera_maxima


def test_valores_dos_limites():
    assert (config.LIMITE_LOGIN_EMAIL, config.LIMITE_LOGIN_IP) == (5, 20)
    assert (config.JANELA_LOGIN, config.LIMITE_CADASTRO_IP) == (900, 5)
    assert config.JANELA_CADASTRO == 3600


def test_login_bloqueia_na_sexta_falha(client, conta, limite_real):
    codigos = [login(client, conta).status_code for _ in range(5)]
    assert codigos == [401] * 5
    conferir_429(login(client, conta), 900)


def test_login_bloqueado_recusa_ate_a_senha_certa(client, conta, limite_real):
    for _ in range(5):
        login(client, conta)
    conferir_429(login(client, conta, SENHA), 900)


def test_login_bloqueia_igual_para_email_que_nao_existe(client, conta, limite_real):
    def sequencia(email):
        respostas = [login(client, email) for _ in range(6)]
        return [(r.status_code, r.json()) for r in respostas]

    existe = sequencia(conta)
    tentativas.limpar()
    assert sequencia("pytest_nao_existe@teste.com") == existe
    assert existe[-1][0] == 429


def test_login_conta_o_email_normalizado(client, conta, limite_real):
    for _ in range(5):
        login(client, conta.upper())
    conferir_429(login(client, conta), 900)


def test_login_bloqueado_nao_confere_a_senha(client, conta, limite_real, monkeypatch):
    for _ in range(5):
        login(client, conta)
    chamadas = []
    monkeypatch.setattr(
        "api.main.verificar_senha", lambda *a: chamadas.append(a) or False
    )
    assert login(client, conta).status_code == 429
    assert chamadas == []


def test_tentativa_bloqueada_nao_renova_o_bloqueio(client, conta, limite_real, relogio):
    for _ in range(5):
        login(client, conta)
    relogio[0] += 899
    codigos = [login(client, conta).status_code for _ in range(5)]
    assert codigos == [429] * 5
    relogio[0] += 1
    assert login(client, conta).status_code == 401


def test_sucesso_zera_as_falhas_do_email(client, conta, limite_real):
    for _ in range(4):
        login(client, conta)
    assert login(client, conta, SENHA).status_code == 200
    codigos = [login(client, conta).status_code for _ in range(5)]
    assert codigos == [401] * 5
    assert login(client, conta).status_code == 429


def test_ip_bloqueia_senha_espalhada_em_varios_emails(client, limite_real):
    codigos = [
        login(client, f"pytest_spray_{i}@teste.com").status_code for i in range(20)
    ]
    assert codigos == [401] * 20
    conferir_429(login(client, "pytest_spray_novo@teste.com"), 900)


def test_sucesso_nao_zera_as_falhas_do_ip(client, conta, limite_real, monkeypatch):
    monkeypatch.setattr("api.main.LIMITE_LOGIN_IP", 6)
    for i in range(5):
        login(client, f"pytest_spray_{i}@teste.com")
    assert login(client, conta, SENHA).status_code == 200
    assert login(client, "pytest_spray_5@teste.com").status_code == 401
    assert login(client, "pytest_spray_6@teste.com").status_code == 429


def test_cabecalho_forjado_nao_troca_o_ip(client, conta, limite_real):
    def forjado(i):
        ip = f"10.0.0.{i}"
        return {"X-Forwarded-For": ip, "X-Real-IP": ip, "Forwarded": f"for={ip}"}

    for i in range(5):
        login(client, conta, headers=forjado(i))
    assert login(client, conta, headers=forjado(99)).status_code == 429
    tentativas.limpar()
    for i in range(20):
        login(client, f"pytest_spray_{i}@teste.com", headers=forjado(i))
    resposta = login(client, "pytest_spray_novo@teste.com", headers=forjado(99))
    assert resposta.status_code == 429


def test_cadastro_bloqueia_no_sexto(client, fabrica, limite_real):
    codigos = [cadastro(client, fabrica).status_code for _ in range(5)]
    assert codigos == [201] * 5
    quantos = len(fabrica.emails)
    conferir_429(cadastro(client, fabrica), 3600)
    assert login(client, fabrica.emails[quantos], SENHA).status_code == 401


def test_cadastro_repetido_tambem_conta(client, fabrica, conta, limite_real):
    codigos = [cadastro(client, fabrica, conta).status_code for _ in range(5)]
    assert codigos == [409] * 5
    conferir_429(cadastro(client, fabrica, conta), 3600)


def test_cadastro_e_login_tem_contadores_separados(
    client, fabrica, limite_real, monkeypatch
):
    monkeypatch.setattr("api.main.LIMITE_LOGIN_IP", 5)
    for _ in range(5):
        cadastro(client, fabrica)
    assert cadastro(client, fabrica).status_code == 429
    assert login(client, "pytest_spray_0@teste.com").status_code == 401
    tentativas.limpar()
    for i in range(5):
        login(client, f"pytest_spray_{i}@teste.com")
    assert login(client, "pytest_spray_5@teste.com").status_code == 429
    assert cadastro(client, fabrica).status_code == 201


def disparar_juntos(quantos, acao):
    largada = threading.Barrier(quantos)
    resultados = []

    def disparar(i):
        largada.wait()
        resultados.append(acao(i))

    fios = [threading.Thread(target=disparar, args=(i,)) for i in range(quantos)]
    for fio in fios:
        fio.start()
    for fio in fios:
        fio.join()
    return resultados


@pytest.mark.lento
def test_rajada_de_logins_respeita_o_limite(client, conta, limite_real):
    for _ in range(3):
        tentativas.limpar()
        codigos = disparar_juntos(30, lambda i: login(client, conta).status_code)
        assert (codigos.count(401), codigos.count(429)) == (5, 25), codigos


@pytest.mark.lento
def test_rajada_de_cadastros_respeita_o_limite(client, fabrica, conta, limite_real):
    codigos = disparar_juntos(
        20, lambda i: cadastro(client, fabrica, conta).status_code
    )
    assert (codigos.count(409), codigos.count(429)) == (5, 15), codigos


def test_no_maximo_dois_hashes_ao_mesmo_tempo(client, limite_real, monkeypatch):
    trava = threading.Lock()
    em_curso = []
    picos = []

    def verificar_lento(senha_hash, senha):
        with trava:
            em_curso.append(1)
            picos.append(len(em_curso))
        time.sleep(0.05)
        with trava:
            em_curso.pop()
        return True

    monkeypatch.setattr(
        "api.seguranca.ph", types.SimpleNamespace(verify=verificar_lento)
    )
    codigos = disparar_juntos(
        15, lambda i: login(client, f"pytest_spray_{i}@teste.com").status_code
    )
    assert codigos == [401] * 15
    assert HASHES_SIMULTANEOS == 2
    assert max(picos) == 2


def test_limite_atingido_vai_para_o_log_sem_o_email(client, conta, limite_real, caplog):
    for _ in range(5):
        login(client, conta)
    with caplog.at_level("WARNING", logger="revisa"):
        login(client, conta)
    assert "login-email" in caplog.text
    assert conta not in caplog.text
    assert SENHA_ERRADA not in caplog.text


def test_limite_folgado_e_o_padrao_dos_outros_testes(client, conta):
    codigos = [login(client, conta).status_code for _ in range(6)]
    assert codigos == [401] * 6
