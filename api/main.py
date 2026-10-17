from fastapi import Depends, FastAPI, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from api.database import engine
from api.schemas import VeiculoResposta, VeiculoCriar, VeiculoAtualizar
from api.models import Veiculo

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

        veiculo_novo = Veiculo(
            **veiculo_tratado,
            id_usuario = ID_USUARIO_CONSTANTE # TODO S2: vem do login
        ) 

        session.add(veiculo_novo)
        try: 
            session.commit()

        except IntegrityError as e:
            session.rollback()
            print(e) # TODO S6: usar logging
            raise HTTPException(status_code = 422, detail = 'Dados recusados pelo banco.')

        session.refresh(veiculo_novo)
        return veiculo_novo


@app.patch('/veiculos/{veiculo_id}', response_model = VeiculoResposta)
def veiculo_alterar(veiculo_id: int, dados_veiculo: VeiculoAtualizar):

    with Session(engine) as session:

        veiculo_existente = session.get(Veiculo, veiculo_id)

        if not veiculo_existente:
            raise HTTPException(status_code = 404, detail = 'Veículo não encontrado.')

        campos_enviados = dados_veiculo.model_dump(exclude_unset = True)

        if 'placa' in campos_enviados and campos_enviados['placa'] is not None:
            campos_enviados['placa'] = campos_enviados['placa'].strip().upper()

        for campo, valor in campos_enviados.items():
            setattr(veiculo_existente, campo, valor)

        if veiculo_existente.ano_modelo < veiculo_existente.ano_fabricacao or veiculo_existente.ano_modelo > veiculo_existente.ano_fabricacao + 1:
            session.rollback()
            raise HTTPException(status_code = 422, detail = 'O ano do modelo deve ser igual ao de fabricação ou no máximo 1 ano maior')

        try: 
            session.commit()

        except IntegrityError as e:
            session.rollback()
            print(e) # TODO S6: usar logging
            raise HTTPException(status_code = 422, detail = 'Dados recusados pelo banco.')
        
        session.refresh(veiculo_existente)
        return veiculo_existente


@app.delete('/veiculos/{veiculo_id}', status_code = 204)
def veiculo_delete(veiculo_id: int):

    with Session(engine) as session:

        veiculo = session.get(Veiculo, veiculo_id)

        if not veiculo:
            raise HTTPException(status_code = 404, detail = 'Veículo não encontrado.')

        session.delete(veiculo)

        try: 
            session.commit()
            return
        
        except IntegrityError as e:
            session.rollback()
            print(e) # TODO S6: usar logging
            raise HTTPException(status_code = 409, detail = 'Veículo possui orçamentos vinculados. Não é possível apagar o veículo.')

     