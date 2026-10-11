import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError('ERRO! Está faltando a variável DATABASE_URL. Configure no .env')

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

if __name__ == "__main__":
    with engine.connect() as connection:
    
        result = connection.execute(text('SELECT 1'))
    
        valor = result.scalar()
    
        print(f'Conexão bem-sucedida! O banco respondeu: {valor}')