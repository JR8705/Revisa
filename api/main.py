from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.database import engine
from api.enums import StatusOrcamentoEnum
from api.models import (
    CategoriaItem,
    ItemOrcamento,
    Oficina,
    Orcamento,
    Usuario,
    Veiculo,
)
from api.regras import ano_valido, calcular_subtotal, calcular_total, combustivel_valido
from api.schemas import (
    ItemOrcamentoCriar,
    ItemOrcamentoResposta,
    LoginEntrada,
    OrcamentoCriar,
    OrcamentoDetalheResposta,
    OrcamentoResposta,
    TokenResposta,
    UsuarioCriar,
    UsuarioResposta,
    VeiculoAtualizar,
    VeiculoCriar,
    VeiculoResposta,
)
from api.seguranca import criar_token, gerar_hash, ler_token, verificar_senha

HASH_FALSO = gerar_hash("qualquer-coisa")

app = FastAPI()
esquema_oauth = OAuth2PasswordBearer(tokenUrl="/login")


@app.get("/")
async def root():
    return {"message": "Hello World"}


def usuario_atual(token: str = Depends(esquema_oauth)):
    id_usuario = ler_token(token)

    if id_usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Token inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        id_usuario = int(id_usuario)
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=401,
            detail="Token inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with Session(engine) as session:
        usuario = session.get(Usuario, id_usuario)
        if usuario is None:
            raise HTTPException(
                status_code=401,
                detail="Token inválido.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return id_usuario


IdUsuario = Annotated[int, Depends(usuario_atual)]


@app.get("/veiculos/{id_veiculo}", response_model=VeiculoResposta)
def get_id_veiculo(id_veiculo: int, id_usuario_validado: IdUsuario):

    with Session(engine) as session:
        veiculo = session.scalars(
            select(Veiculo).where(
                Veiculo.id == id_veiculo, Veiculo.id_usuario == id_usuario_validado
            )
        ).first()

        if veiculo:
            return veiculo

        else:
            raise HTTPException(status_code=404, detail="Veículo não encontrado.")


@app.get("/veiculos/placa/{veiculo_placa}", response_model=list[VeiculoResposta])
def get_veiculo_placa(
    veiculo_placa: Annotated[str, Path(max_length=10)], id_usuario_validado: IdUsuario
):

    placa_tratada = veiculo_placa.strip().upper()

    with Session(engine) as session:
        veiculos = session.scalars(
            select(Veiculo).where(
                Veiculo.placa == placa_tratada,
                Veiculo.id_usuario == id_usuario_validado,
            )
        ).all()
        if veiculos:
            return veiculos

        else:
            raise HTTPException(status_code=404, detail="Veículo não encontrado.")


@app.post("/veiculos", response_model=VeiculoResposta, status_code=201)
def veiculo_criar(dados_veiculo: VeiculoCriar, id_usuario_validado: IdUsuario):

    with Session(engine) as session:
        veiculo_tratado = dados_veiculo.model_dump()

        if veiculo_tratado["placa"] is not None:
            veiculo_tratado["placa"] = veiculo_tratado["placa"].strip().upper()

        veiculo_novo = Veiculo(**veiculo_tratado, id_usuario=id_usuario_validado)

        session.add(veiculo_novo)
        try:
            session.commit()

        except IntegrityError:
            session.rollback()
            # print(e)  TODO S6: usar logging
            raise HTTPException(status_code=422, detail="Dados recusados pelo banco.")

        session.refresh(veiculo_novo)
        return veiculo_novo


@app.patch("/veiculos/{id_veiculo}", response_model=VeiculoResposta)
def veiculo_alterar(
    id_veiculo: int, dados_veiculo: VeiculoAtualizar, id_usuario_validado: IdUsuario
):

    with Session(engine) as session:
        veiculo_existente = session.scalars(
            select(Veiculo).where(
                Veiculo.id == id_veiculo, Veiculo.id_usuario == id_usuario_validado
            )
        ).first()

        if not veiculo_existente:
            raise HTTPException(status_code=404, detail="Veículo não encontrado.")

        campos_enviados = dados_veiculo.model_dump(exclude_unset=True)

        if "placa" in campos_enviados and campos_enviados["placa"] is not None:
            campos_enviados["placa"] = campos_enviados["placa"].strip().upper()

        for campo, valor in campos_enviados.items():
            setattr(veiculo_existente, campo, valor)

        if not ano_valido(
            veiculo_existente.ano_fabricacao, veiculo_existente.ano_modelo
        ):
            session.rollback()
            raise HTTPException(
                status_code=422,
                detail="O ano do modelo deve ser igual ao de fabricação ou no máximo 1 ano maior",
            )

        if not combustivel_valido(
            veiculo_existente.combustivel, veiculo_existente.cilindrada
        ):
            session.rollback()
            raise HTTPException(
                status_code=422, detail="Veículo elétrico não tem cilindrada."
            )

        try:
            session.commit()

        except IntegrityError:
            session.rollback()
            # print(e) TODO S6: usar logging
            raise HTTPException(status_code=422, detail="Dados recusados pelo banco.")

        session.refresh(veiculo_existente)
        return veiculo_existente


@app.delete("/veiculos/{id_veiculo}", status_code=204)
def veiculo_delete(id_veiculo: int, id_usuario_validado: IdUsuario):

    with Session(engine) as session:
        veiculo = session.scalars(
            select(Veiculo).where(
                Veiculo.id == id_veiculo, Veiculo.id_usuario == id_usuario_validado
            )
        ).first()

        if not veiculo:
            raise HTTPException(status_code=404, detail="Veículo não encontrado.")

        session.delete(veiculo)

        try:
            session.commit()

        except IntegrityError:
            session.rollback()
            # print(e)  TODO S6: usar logging
            raise HTTPException(
                status_code=409,
                detail="Veículo possui orçamentos vinculados. Não é possível apagar o veículo.",
            )


@app.post("/usuarios", response_model=UsuarioResposta, status_code=201)
def usuario_criar(dados_usuario: UsuarioCriar):

    with Session(engine) as session:
        usuario_tratado = dados_usuario.model_dump()

        senha = usuario_tratado.pop("senha")
        usuario_tratado["senha_hash"] = gerar_hash(senha)
        usuario_tratado["email"] = usuario_tratado["email"].strip().lower()

        usuario_novo = Usuario(**usuario_tratado)

        session.add(usuario_novo)
        try:
            session.commit()

        except IntegrityError:
            session.rollback()
            # print(e) TODO S6: usar logging
            raise HTTPException(status_code=409, detail="E-mail já cadastrado.")

        session.refresh(usuario_novo)
        return usuario_novo


@app.post("/login", response_model=TokenResposta, status_code=200)
def usuario_login(dados_usuario: LoginEntrada):

    email = dados_usuario.email.strip().lower()

    with Session(engine) as session:
        usuario = session.scalars(select(Usuario).where(Usuario.email == email)).first()

    hash_conferir = usuario.senha_hash if usuario else HASH_FALSO
    senha_ok = verificar_senha(dados_usuario.senha, hash_conferir)

    if not usuario or not senha_ok:
        raise HTTPException(
            status_code=401,
            detail="E-mail ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"access_token": criar_token(usuario.id), "token_type": "bearer"}


@app.post(
    "/veiculos/{id_veiculo}/orcamentos",
    response_model=OrcamentoResposta,
    status_code=201,
)
def orcamento_criar(
    dados_orcamento: OrcamentoCriar, id_veiculo: int, id_usuario: IdUsuario
):

    dados = dados_orcamento.model_dump()

    with Session(engine) as session:
        veiculo = session.scalars(
            select(Veiculo).where(
                Veiculo.id == id_veiculo, Veiculo.id_usuario == id_usuario
            )
        ).first()

        if not veiculo:
            raise HTTPException(status_code=404, detail="Veículo não encontrado.")

        check_oficina = session.get(Oficina, dados["id_oficina"])
        if check_oficina is None:
            raise HTTPException(status_code=422, detail="Oficina inválida.")

        orcamento = Orcamento(id_veiculo=veiculo.id, **dados)

        session.add(orcamento)

        try:
            session.commit()

        except IntegrityError:
            session.rollback()
            # print(e) TODO S6: usar logging
            raise HTTPException(status_code=422, detail="Oficina inválida.")

        session.refresh(orcamento)
        return orcamento


@app.get(
    "/veiculos/{id_veiculo}/orcamentos/{id_orcamento}",
    response_model=OrcamentoDetalheResposta,
)
def get_orcamento_id(id_veiculo: int, id_orcamento: int, id_usuario: IdUsuario):

    with Session(engine) as session:
        itens = []
        subtotais = []

        orcamento = session.scalars(
            select(Orcamento)
            .join(Veiculo)
            .where(
                Orcamento.id == id_orcamento,
                Orcamento.id_veiculo == id_veiculo,
                Veiculo.id_usuario == id_usuario,
            )
        ).first()

        if not orcamento:
            raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

        itens_orcamento = session.scalars(
            select(ItemOrcamento)
            .where(ItemOrcamento.id_orcamento == orcamento.id)
            .order_by(ItemOrcamento.id)
        ).all()

        for item in itens_orcamento:
            subtotal = calcular_subtotal(item.quantidade, item.valor_unitario)
            subtotais.append(subtotal)
            itens.append(
                {
                    "id": item.id,
                    "id_categoria": item.id_categoria,
                    "descricao": item.descricao,
                    "tipo": item.tipo,
                    "quantidade": item.quantidade,
                    "valor_unitario": item.valor_unitario,
                    "subtotal": subtotal,
                }
            )

        return {
            **OrcamentoResposta.model_validate(orcamento).model_dump(),
            "itens": itens,
            "total": calcular_total(subtotais),
        }


@app.post(
    "/veiculos/{id_veiculo}/orcamentos/{id_orcamento}/itens",
    response_model=ItemOrcamentoResposta,
    status_code=201,
)
def item_criar(
    id_veiculo: int,
    id_orcamento: int,
    item_dados: ItemOrcamentoCriar,
    id_usuario: IdUsuario,
):

    with Session(engine) as session:
        orcamento = session.scalars(
            select(Orcamento)
            .join(Veiculo)
            .where(
                Orcamento.id == id_orcamento,
                Orcamento.id_veiculo == id_veiculo,
                Veiculo.id_usuario == id_usuario,
            )
        ).first()

        if not orcamento:
            raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

        if orcamento.status != StatusOrcamentoEnum.PENDENTE:
            raise HTTPException(
                status_code=409, detail="Não é possível alterar este orçamento."
            )

        categoria = session.get(CategoriaItem, item_dados.id_categoria)
        if not categoria:
            raise HTTPException(status_code=422, detail="Categoria inválida.")

        dados = item_dados.model_dump()
        novo_item = ItemOrcamento(id_orcamento=orcamento.id, **dados)

        try:
            session.add(novo_item)
            session.commit()
            session.refresh(novo_item)
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=422, detail="Dados do item inválidos.")

        subtotal = calcular_subtotal(novo_item.quantidade, novo_item.valor_unitario)

        return {
            "id": novo_item.id,
            "id_categoria": novo_item.id_categoria,
            "descricao": novo_item.descricao,
            "tipo": novo_item.tipo,
            "quantidade": novo_item.quantidade,
            "valor_unitario": novo_item.valor_unitario,
            "subtotal": subtotal,
        }
