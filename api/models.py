from sqlalchemy import String, Integer, SmallInteger, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Veiculo(Base):
    __tablename__ = 'veiculos'

    id: Mapped[int] =  mapped_column(primary_key=True)
    id_usuario: Mapped[int]
    marca: Mapped[str] = mapped_column(String(50))
    modelo: Mapped[str] = mapped_column(String(80))
    motor: Mapped[str | None] = mapped_column(String(30))
    placa: Mapped[str | None] = mapped_column(String(10))
    ano_fabricacao: Mapped[int] = mapped_column(SmallInteger)
    ano_modelo: Mapped[int | None] = mapped_column(SmallInteger)
    km_atual: Mapped[int] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone = True), server_default = func.now())