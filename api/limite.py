import threading
import time

from api.config import JANELA_CADASTRO, JANELA_LOGIN
from api.registros import avisar_limite
from api.regras import espera_em_segundos, tentativas_recentes

JANELA_MAXIMA = max(JANELA_LOGIN, JANELA_CADASTRO)
VARRER_A_CADA = 1000
HASHES_SIMULTANEOS = 2


class RegistroTentativas:
    def __init__(self):
        self._momentos = {}
        self._trava = threading.Lock()
        self._registros = 0

    def espera(self, chave, limite, janela):
        with self._trava:
            momentos = self._momentos.get(chave, [])
            return espera_em_segundos(momentos, time.monotonic(), limite, janela)

    def registrar(self, chave):
        with self._trava:
            agora = time.monotonic()
            self._momentos.setdefault(chave, []).append(agora)
            self._registros += 1
            if self._registros % VARRER_A_CADA == 0:
                self._varrer(agora)

    def tentar(self, regras):
        with self._trava:
            agora = time.monotonic()
            esperas = [
                espera_em_segundos(self._momentos.get(chave, []), agora, limite, janela)
                for chave, limite, janela in regras
            ]
            espera = max(esperas)
            if espera > 0:
                avisar_limite(
                    regra[0][0] for regra, e in zip(regras, esperas, strict=True) if e
                )
                return espera
            for chave, _, _ in regras:
                self._momentos.setdefault(chave, []).append(agora)
            self._registros += 1
            if self._registros % VARRER_A_CADA == 0:
                self._varrer(agora)
            return 0

    def devolver(self, chave):
        with self._trava:
            momentos = self._momentos.get(chave)
            if momentos:
                momentos.pop()

    def limpar_chave(self, chave):
        with self._trava:
            self._momentos.pop(chave, None)

    def limpar(self):
        with self._trava:
            self._momentos.clear()

    def _varrer(self, agora):
        for chave in list(self._momentos):
            recentes = tentativas_recentes(self._momentos[chave], agora, JANELA_MAXIMA)
            if recentes:
                self._momentos[chave] = recentes
            else:
                del self._momentos[chave]


tentativas = RegistroTentativas()
vagas_hash = threading.BoundedSemaphore(HASHES_SIMULTANEOS)


def ip_do_cliente(request):
    if request.client is None:
        return "desconhecido"
    return request.client.host
