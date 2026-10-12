from pydantic import BaseModel

class VeiculoResposta(BaseModel):
    id: int
    marca: str
    modelo: str
    motor: str | None
    ano_fabricacao: int
    ano_modelo: int | None
    km_atual: int