from pydantic import BaseModel, ConfigDict
from api.enums import TipoCombustivelEnum
from decimal import Decimal
class VeiculoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    marca: str
    modelo: str
    motor: str | None
    combustivel: TipoCombustivelEnum
    cilindrada: Decimal | None
    turbo: bool
    ano_fabricacao: int
    ano_modelo: int
    km_atual: int