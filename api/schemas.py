from pydantic import BaseModel, ConfigDict, Field, model_validator
from api.enums import TipoCombustivelEnum
from decimal import Decimal
class VeiculoResposta(BaseModel):
    model_config = ConfigDict(from_attributes = True)

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

class VeiculoCriar(BaseModel):
    model_config = ConfigDict(extra = 'forbid')

    marca: str = Field(min_length = 2, max_length = 50)
    modelo: str = Field(min_length = 2,max_length = 80)
    motor: str | None = Field(default = None, max_length = 30)
    combustivel: TipoCombustivelEnum
    cilindrada: Decimal | None = Field(default = None, gt = 0)
    turbo: bool = Field(default = False)
    placa: str | None = Field(default = None, max_length = 10)
    ano_fabricacao: int = Field(ge = 1886, le = 2027)
    ano_modelo: int = Field(ge = 1886, le = 2027)
    km_atual: int = Field(default = 0, ge = 0)
    
    @model_validator(mode = 'after')
    def verificar_anos(self) -> 'VeiculoCriar':

        if self.ano_modelo < self.ano_fabricacao or self.ano_modelo > self.ano_fabricacao + 1:
            raise ValueError(
                'O ano do modelo deve ser igual ao de fabricação ou no máximo 1 ano maior'
            )
        return self
    
    @model_validator(mode = 'after')
    def verificar_cilindrada(self) -> 'VeiculoCriar':
        
        if self.combustivel == TipoCombustivelEnum.ELETRICO and self.cilindrada is not None:
            raise ValueError(
                'Veículo elétrico não tem cilindrada.'
            )
        return self

class VeiculoAtualizar(BaseModel):
    model_config = ConfigDict(extra = 'forbid')
    
    marca: str = Field(default = None,min_length = 2, max_length = 50)
    modelo: str = Field(default = None,min_length = 2,max_length = 80)
    motor: str | None = Field(default = None, max_length = 30)
    combustivel: TipoCombustivelEnum | None = Field(default = None)
    cilindrada: Decimal = Field(default = None, gt = 0)
    turbo: bool = Field(default = None)
    placa: str | None = Field(default = None, max_length = 10)
    ano_fabricacao: int = Field(default = None,ge = 1886, le = 2027)
    ano_modelo: int = Field(default = None,ge = 1886, le = 2027)
    km_atual: int = Field(default = None, ge = 0)