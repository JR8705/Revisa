from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

ph = PasswordHasher()

def gerar_hash(senha):

    return ph.hash(senha)

def verificar_senha(senha, senha_hash):

    try:
        ph.verify(senha_hash, senha)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False