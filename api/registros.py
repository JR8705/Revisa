import logging

logger = logging.getLogger("revisa")


def avisar_erro_banco(rota, erro):
    diag = getattr(erro.orig, "diag", None)
    restricao = getattr(diag, "constraint_name", None)
    logger.warning(
        "Erro do banco em %s: %s (restrição: %s)",
        rota,
        type(erro.orig).__name__,
        restricao,
    )


def avisar_limite(tipos):
    logger.warning("Limite de tentativas atingido: %s", ", ".join(tipos))
