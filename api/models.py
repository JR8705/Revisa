from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, SmallInteger, Integer, Boolean, Numeric, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from api.enums import TipoCombustivelEnum
class Base(DeclarativeBase):
    pass
class Veiculo(Base):
    __tablename__ = 'veiculos'

    id: Mapped[int] =  mapped_column(primary_key=True)
    id_usuario: Mapped[int]
    marca: Mapped[str] = mapped_column(String(50))
    modelo: Mapped[str] = mapped_column(String(80))
    motor: Mapped[str | None] = mapped_column(String(30))
    combustivel: Mapped[TipoCombustivelEnum] = mapped_column(
        Enum(TipoCombustivelEnum, name='tipo_combustivel')
    )
    cilindrada: Mapped[Decimal | None] = mapped_column(Numeric(precision=3, scale=1))
    turbo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    placa: Mapped[str | None] = mapped_column(String(10))
    ano_fabricacao: Mapped[int] = mapped_column(SmallInteger)
    ano_modelo: Mapped[int | None] = mapped_column(SmallInteger)
    km_atual: Mapped[int] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now())