from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def validacao_sem_input(request: Request, exc: RequestValidationError):

    erros = [
        {campo: valor for campo, valor in erro.items() if campo != "input"}
        for erro in exc.errors()
    ]

    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(erros)})


def erro_422(mensagem, campo=None):
    local = ["body", campo] if campo else ["body"]
    return HTTPException(
        status_code=422,
        detail=[{"type": "value_error", "loc": local, "msg": mensagem}],
    )


def erro_429(espera):
    return HTTPException(
        status_code=429,
        detail="Muitas tentativas. Tente novamente mais tarde.",
        headers={"Retry-After": str(espera)},
    )
