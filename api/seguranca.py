import datetime
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from api.config import JWT_SECRET, JWT_ALGORITMO, JWT_EXPIRA_EM_MINUTOS


ph = PasswordHasher()

def gerar_hash(senha):

    return ph.hash(senha)

def verificar_senha(senha, senha_hash):

    try:
        ph.verify(senha_hash, senha)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False

def criar_token(id_usuario):
    payload = {
        'sub': str(id_usuario),
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes = JWT_EXPIRA_EM_MINUTOS)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm = JWT_ALGORITMO)
    return token

def ler_token(token: str) -> int | None:

    try:
        token_decodificado = jwt.decode(
            token, 
            JWT_SECRET, 
            algorithms = [JWT_ALGORITMO],
            options={'require': ['exp']}
            )
        id_usuario = int(token_decodificado['sub'])
        return id_usuario
    except (jwt.InvalidTokenError, ValueError, KeyError):
        return None
