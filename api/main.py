from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.alertas import gerar_alertas
from api.config import (
    JANELA_CADASTRO,
    JANELA_LOGIN,
    LIMITE_CADASTRO_IP,
    LIMITE_LOGIN_EMAIL,
    LIMITE_LOGIN_IP,
)
from api.database import engine
from api.enums import FontePrecoEnum, StatusOrcamentoEnum
from api.erros import erro_422, erro_429, validacao_sem_input
from api.limite import ip_do_cliente, tentativas
from api.models import (
    CategoriaItem,
    ItemOrcamento,
    Oficina,
    Orcamento,
    PrecoReferencia,
    Usuario,
    Veiculo,
)
from api.regras import (
    ano_valido,
    calcular_subtotal,
    calcular_total,
    combustivel_valido,
    transicao_valida,
)
from api.schemas import (
    AlertaResposta,
    ItemOrcamentoCriar,
    ItemOrcamentoResposta,
    LoginEntrada,
    OrcamentoCriar,
    OrcamentoDetalheResposta,
    OrcamentoResposta,
    OrcamentoStatusAtualizar,
    Texto,
    TokenResposta,
    UsuarioCriar,
    UsuarioResposta,
    VeiculoAtualizar,
    VeiculoCriar,
    VeiculoResposta,
)
from api.seguranca import criar_token, gerar_hash, ler_token, verificar_senha

HASH_FALSO = gerar_hash("qualquer-coisa")
IdCaminho = Annotated[int, Path(gt=0, le=2147483647)]

app = FastAPI()
app.add_exception_handler(RequestValidationError, validacao_sem_input)
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
        ) from None

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
def get_id_veiculo(id_veiculo: IdCaminho, id_usuario_validado: IdUsuario):

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
    veiculo_placa: Annotated[Texto, Path(max_length=10)], id_usuario_validado: IdUsuario
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
            raise erro_422("Dados recusados pelo banco.") from None

        session.refresh(veiculo_novo)
        return veiculo_novo


@app.patch("/veiculos/{id_veiculo}", response_model=VeiculoResposta)
def veiculo_alterar(
    id_veiculo: IdCaminho,
    dados_veiculo: VeiculoAtualizar,
    id_usuario_validado: IdUsuario,
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
            raise erro_422(
                "O ano do modelo deve ser igual ao de fabricação ou no máximo 1 ano maior",
                "ano_modelo",
            )

        if not combustivel_valido(
            veiculo_existente.combustivel, veiculo_existente.cilindrada
        ):
            session.rollback()
            raise erro_422("Veículo elétrico não tem cilindrada.", "cilindrada")

        try:
            session.commit()

        except IntegrityError:
            session.rollback()
            # print(e) TODO S6: usar logging
            raise erro_422("Dados recusados pelo banco.") from None

        session.refresh(veiculo_existente)
        return veiculo_existente


@app.delete("/veiculos/{id_veiculo}", status_code=204)
def veiculo_delete(id_veiculo: IdCaminho, id_usuario_validado: IdUsuario):

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
            ) from None


@app.post("/usuarios", response_model=UsuarioResposta, status_code=201)
def usuario_criar(dados_usuario: UsuarioCriar, request: Request):

    chave_ip = ("cadastro-ip", ip_do_cliente(request))

    espera = tentativas.espera(chave_ip, LIMITE_CADASTRO_IP, JANELA_CADASTRO)
    if espera > 0:
        raise erro_429(espera)
    tentativas.registrar(chave_ip)

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
            raise HTTPException(
                status_code=409, detail="E-mail já cadastrado."
            ) from None

        session.refresh(usuario_novo)
    return usuario_novo


@app.post("/login", response_model=TokenResposta, status_code=200)
def usuario_login(dados_usuario: LoginEntrada, request: Request):

    email = dados_usuario.email.strip().lower()
    chave_email = ("login-email", email)
    chave_ip = ("login-ip", ip_do_cliente(request))

    espera = max(
        tentativas.espera(chave_email, LIMITE_LOGIN_EMAIL, JANELA_LOGIN),
        tentativas.espera(chave_ip, LIMITE_LOGIN_IP, JANELA_LOGIN),
    )
    if espera > 0:
        raise erro_429(espera)

    with Session(engine) as session:
        usuario = session.scalars(select(Usuario).where(Usuario.email == email)).first()

    hash_conferir = usuario.senha_hash if usuario else HASH_FALSO
    senha_ok = verificar_senha(dados_usuario.senha, hash_conferir)

    if not usuario or not senha_ok:
        tentativas.registrar(chave_email)
        tentativas.registrar(chave_ip)
        raise HTTPException(
            status_code=401,
            detail="E-mail ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tentativas.limpar_chave(chave_email)
    return {"access_token": criar_token(usuario.id), "token_type": "bearer"}


@app.post(
    "/veiculos/{id_veiculo}/orcamentos",
    response_model=OrcamentoResposta,
    status_code=201,
)
def orcamento_criar(
    dados_orcamento: OrcamentoCriar, id_veiculo: IdCaminho, id_usuario: IdUsuario
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
            raise erro_422("Oficina inválida.", "id_oficina")

        orcamento = Orcamento(id_veiculo=veiculo.id, **dados)

        session.add(orcamento)

        try:
            session.commit()

        except IntegrityError:
            session.rollback()
            # print(e) TODO S6: usar logging
            raise erro_422("Oficina inválida.", "id_oficina") from None

        session.refresh(orcamento)
        return orcamento


def buscar_orcamento_do_usuario(
    session: Session,
    id_veiculo: int,
    id_orcamento: int,
    id_usuario: int,
    travar: bool = False,
) -> Orcamento | None:

    consulta = (
        select(Orcamento)
        .join(Veiculo)
        .where(
            Orcamento.id == id_orcamento,
            Orcamento.id_veiculo == id_veiculo,
            Veiculo.id_usuario == id_usuario,
        )
    )

    if travar:
        consulta = consulta.with_for_update(of=Orcamento)

    return session.scalars(consulta).first()


def item_resposta(item: ItemOrcamento) -> dict:

    return {
        "id": item.id,
        "id_categoria": item.id_categoria,
        "descricao": item.descricao,
        "tipo": item.tipo,
        "quantidade": item.quantidade,
        "valor_unitario": item.valor_unitario,
        "subtotal": calcular_subtotal(item.quantidade, item.valor_unitario),
    }


def montar_itens(session: Session, orcamento: Orcamento) -> list[dict]:

    itens_orcamento = session.scalars(
        select(ItemOrcamento)
        .where(ItemOrcamento.id_orcamento == orcamento.id)
        .order_by(ItemOrcamento.id)
    ).all()

    itens = []
    for item in itens_orcamento:
        itens.append(item_resposta(item))

    return itens


@app.get(
    "/veiculos/{id_veiculo}/orcamentos/{id_orcamento}",
    response_model=OrcamentoDetalheResposta,
)
def get_orcamento_id(
    id_veiculo: IdCaminho, id_orcamento: IdCaminho, id_usuario: IdUsuario
):

    with Session(engine) as session:
        orcamento = buscar_orcamento_do_usuario(
            session, id_veiculo, id_orcamento, id_usuario
        )

        if not orcamento:
            raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

        itens = montar_itens(session, orcamento)

        subtotais = []
        for item in itens:
            subtotais.append(item["subtotal"])

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
    id_veiculo: IdCaminho,
    id_orcamento: IdCaminho,
    item_dados: ItemOrcamentoCriar,
    id_usuario: IdUsuario,
):

    with Session(engine) as session:
        orcamento = buscar_orcamento_do_usuario(
            session, id_veiculo, id_orcamento, id_usuario, travar=True
        )

        if not orcamento:
            raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

        if orcamento.status != StatusOrcamentoEnum.PENDENTE:
            raise HTTPException(
                status_code=409, detail="Não é possível alterar este orçamento."
            )

        categoria = session.get(CategoriaItem, item_dados.id_categoria)
        if not categoria:
            raise erro_422("Categoria inválida.", "id_categoria")

        dados = item_dados.model_dump()
        novo_item = ItemOrcamento(id_orcamento=orcamento.id, **dados)

        try:
            session.add(novo_item)
            session.commit()
            session.refresh(novo_item)
        except IntegrityError:
            session.rollback()
            raise erro_422("Dados do item inválidos.") from None

        return item_resposta(novo_item)


@app.patch(
    "/veiculos/{id_veiculo}/orcamentos/{id_orcamento}", response_model=OrcamentoResposta
)
def status_alterar(
    id_veiculo: IdCaminho,
    id_orcamento: IdCaminho,
    dados_orcamento: OrcamentoStatusAtualizar,
    id_usuario_validado: IdUsuario,
):

    with Session(engine) as session:
        orcamento = buscar_orcamento_do_usuario(
            session, id_veiculo, id_orcamento, id_usuario_validado, travar=True
        )

        if not orcamento:
            raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

        if not transicao_valida(orcamento.status, dados_orcamento.status):
            raise HTTPException(
                status_code=409,
                detail="Não é possível alterar este orçamento.",
            )
        if dados_orcamento.status == StatusOrcamentoEnum.APROVADO:
            tem_item = session.scalars(
                select(ItemOrcamento)
                .where(ItemOrcamento.id_orcamento == orcamento.id)
                .limit(1)
            ).first()

            if not tem_item:
                raise HTTPException(
                    status_code=409, detail="Não é possível alterar este orçamento."
                )

        orcamento.status = dados_orcamento.status

        session.commit()
        session.refresh(orcamento)
        return orcamento


@app.get(
    "/veiculos/{id_veiculo}/orcamentos/{id_orcamento}/alertas",
    response_model=list[AlertaResposta],
)
def get_alertas(
    id_veiculo: IdCaminho,
    id_orcamento: IdCaminho,
    id_usuario_validado: IdUsuario,
):

    with Session(engine) as session:
        orcamento = buscar_orcamento_do_usuario(
            session, id_veiculo, id_orcamento, id_usuario_validado
        )

        if not orcamento:
            raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

        itens = montar_itens(session, orcamento)

        tetos = {}
        linhas_teto = session.execute(
            select(PrecoReferencia.id_categoria, func.max(PrecoReferencia.valor_max))
            .where(PrecoReferencia.fonte == FontePrecoEnum.MANUAL)
            .group_by(PrecoReferencia.id_categoria)
        ).all()
        for id_categoria, teto in linhas_teto:
            tetos[id_categoria] = teto

        intervalos = {}
        for categoria in session.scalars(select(CategoriaItem)).all():
            intervalos[categoria.id] = (
                categoria.intervalo_km,
                categoria.intervalo_meses,
            )

        historico = []
        linhas_historico = session.execute(
            select(ItemOrcamento.id_categoria, Orcamento.data_emissao, Orcamento.km)
            .join(Orcamento)
            .where(
                Orcamento.id_veiculo == orcamento.id_veiculo,
                Orcamento.status == StatusOrcamentoEnum.APROVADO,
                Orcamento.id != orcamento.id,
                Orcamento.data_emissao <= orcamento.data_emissao,
            )
        ).all()
        for id_categoria, data_emissao, km in linhas_historico:
            historico.append(
                {"id_categoria": id_categoria, "data_emissao": data_emissao, "km": km}
            )

        return gerar_alertas(
            itens, tetos, historico, intervalos, orcamento.km, orcamento.data_emissao
        )
