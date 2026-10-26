import os

from dotenv import load_dotenv

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITMO = "HS256"
JWT_EXPIRA_EM_MINUTOS = 30
if not JWT_SECRET:
    raise RuntimeError("ERRO! Está faltando a variável JWT_SECRET. Configure no .env.")

if len(JWT_SECRET) < 32:
    raise RuntimeError(
        "ERRO! O segredo deve ter pelo menos 32 caracteres. Configure no .env."
    )
