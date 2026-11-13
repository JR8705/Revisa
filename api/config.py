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

LIMITE_LOGIN_EMAIL = 5
LIMITE_LOGIN_IP = 20
JANELA_LOGIN = 15 * 60
LIMITE_CADASTRO_IP = 5
JANELA_CADASTRO = 60 * 60
