from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from api.database import engine

app = FastAPI()


@app.get('/')
async def root():
    return {"message": "Hello World"}

@app.get('/veiculos/{veiculo_id}')
def get_veiculo(veiculo_id: int):
    with engine.connect() as connection:
        veiculo = connection.execute(text("SELECT marca,modelo,motor,ano_modelo,km_atual FROM veiculos WHERE id = :veiculo_id"), {'veiculo_id': veiculo_id}).first()

        if veiculo:
            dados_veiculo = dict(veiculo._mapping)
            
            return{
                'veiculo_id': veiculo_id, 
                'dados': dados_veiculo
                }
        else:
            raise HTTPException(status_code=404, detail='Veículo não encontrado.')
