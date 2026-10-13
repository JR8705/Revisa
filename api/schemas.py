from pydantic import BaseModel, ConfigDict

class VeiculoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    marca: str
    modelo: str
    motor: str | None
    ano_fabricacao: int
    ano_modelo: int | None
    km_atual: int