from fastapi import FastAPI, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from api.database import engine
from api.schemas import VeiculoResposta
from api.models import Veiculo


app = FastAPI()

@app.get('/')
async def root():
    return {"message": "Hello World"}

@app.get('/veiculos/{veiculo_id}', response_model = VeiculoResposta)
def get_veiculo_id(veiculo_id: int):
    
    with Session(engine) as session:
        veiculo = session.scalars(
            select(Veiculo).where(Veiculo.id == veiculo_id)
        ).first()

        if veiculo:
            return veiculo
        
        else:
            raise HTTPException(status_code=404, detail='Veículo não encontrado.')

@app.get('/veiculos/placa/{veiculo_placa}', response_model = list[VeiculoResposta])
def get_veiculo_placa(veiculo_placa: str = Path(max_length = 10)):

    placa_tratada = veiculo_placa.strip().upper()
    
    with Session(engine) as session:
        veiculos = session.scalars(
            select(Veiculo).where(Veiculo.placa == placa_tratada)
            ).all()
        if veiculos:
            return veiculos
        
        else:
            raise HTTPException(status_code=404, detail='Veículo não encontrado.')
    