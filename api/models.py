from datetime import datetime
from decimal import Decimal
from datetime import date
from sqlalchemy import String, SmallInteger, Integer, Boolean, Numeric, DateTime, Date, Enum, func, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from api.enums import TipoCombustivelEnum, GrupoItemEnum, StatusOrcamentoEnum, TipoItemEnum
class Base(DeclarativeBase):
    pass
class Veiculo(Base):
    __tablename__ = 'veiculos'

    id: Mapped[int] =  mapped_column(primary_key = True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))
    marca: Mapped[str] = mapped_column(String(50))
    modelo: Mapped[str] = mapped_column(String(80))
    motor: Mapped[str | None] = mapped_column(String(30))
    combustivel: Mapped[TipoCombustivelEnum] = mapped_column(
        Enum(TipoCombustivelEnum, name = 'tipo_combustivel')
    )
    cilindrada: Mapped[Decimal | None] = mapped_column(Numeric(precision = 3, scale = 1))
    turbo: Mapped[bool] = mapped_column(Boolean, default = False, server_default = "false", nullable = False)
    placa: Mapped[str | None] = mapped_column(String(10))
    ano_fabricacao: Mapped[int] = mapped_column(SmallInteger)
    ano_modelo: Mapped[int] = mapped_column(SmallInteger)
    km_atual: Mapped[int] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now())

class Usuario(Base):
    __tablename__ = 'usuarios'

    id: Mapped[int] = mapped_column(primary_key = True)
    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique = True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now())


class Oficina(Base):
    __tablename__ = 'oficinas'
    
    id: Mapped[int] = mapped_column(primary_key = True)
    nome: Mapped[str] = mapped_column(String(120))
    cidade: Mapped[str | None] = mapped_column(String(80))
    telefone: Mapped[str | None] = mapped_column(String(20))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now())


class CategoriaItem(Base):
    __tablename__ = 'categorias_item'

    id: Mapped[int] = mapped_column(primary_key = True)
    nome: Mapped[str] = mapped_column(String(100), unique = True)
    grupo: Mapped[GrupoItemEnum] = mapped_column(
        Enum(GrupoItemEnum, name = 'grupo_item')
    )
    intervalo_km: Mapped[int | None] = mapped_column(Integer)
    intervalo_meses: Mapped[int | None] = mapped_column(Integer)


class Orcamento(Base):
    __tablename__ = 'orcamentos'

    id: Mapped[int] = mapped_column(primary_key = True)
    id_veiculo: Mapped[int] = mapped_column(ForeignKey('veiculos.id'))
    id_oficina: Mapped[int] = mapped_column(ForeignKey('oficinas.id'))
    data_emissao: Mapped[date] = mapped_column(Date)
    km: Mapped[int] 
    status: Mapped[StatusOrcamentoEnum] = mapped_column(
        Enum(StatusOrcamentoEnum, name = 'status_orcamento'),
        default = StatusOrcamentoEnum.PENDENTE,
        server_default = 'PENDENTE'
    )
    arquivo_url: Mapped[str | None] = mapped_column(String(255))
    texto_extraido: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now())


class ItemOrcamento(Base):
    __tablename__ = 'itens_orcamento'

    id: Mapped[int] = mapped_column(primary_key = True)
    id_orcamento: Mapped[int] = mapped_column(ForeignKey('orcamentos.id'))
    id_categoria: Mapped[int] = mapped_column(ForeignKey('categorias_item.id'))
    descricao: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[TipoItemEnum] = mapped_column(
        Enum(TipoItemEnum, name = 'tipo_item')
    )
    quantidade: Mapped[Decimal] = mapped_column(Numeric(precision = 10, scale = 2), server_default = '1')
    valor_unitario: Mapped[Decimal] = mapped_column(Numeric(precision = 10, scale = 2))
