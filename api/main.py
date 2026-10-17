from fastapi import Depends, FastAPI, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from api.database import engine
from api.schemas import VeiculoResposta, VeiculoCriar
from api.models import Veiculo
from api.database import engine

ID_USUARIO_CONSTANTE = 1

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

@app.post('/veiculos', response_model = VeiculoResposta, status_code = 201)
def veiculo_criar(dados_veiculo: VeiculoCriar):

    with Session(engine) as session:
        veiculo_tratado = dados_veiculo.model_dump()

        if veiculo_tratado['placa'] is not None:
           veiculo_tratado['placa'] = veiculo_tratado['placa'].strip().upper()

        novo_veiculo = Veiculo(
            **veiculo_tratado,
            id_usuario = ID_USUARIO_CONSTANTE # TODO S2: vem do login
        ) 

        session.add(novo_veiculo)
        try: 
            session.commit()

        except IntegrityError as e:
            session.rollback()
            print(e) # TODO S6: usar logging
            raise HTTPException(status_code = 422, detail = 'Dados recusados pelo banco.')

        session.refresh(novo_veiculo)
        return novo_veiculo