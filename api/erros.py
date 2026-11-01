from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def validacao_sem_input(request: Request, exc: RequestValidationError):

    erros = [
        {campo: valor for campo, valor in erro.items() if campo != "input"}
        for erro in exc.errors()
    ]

    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(erros)})
