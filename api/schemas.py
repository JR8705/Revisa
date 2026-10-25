from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator, field_validator
from api.enums import TipoCombustivelEnum, StatusOrcamentoEnum, TipoItemEnum
from datetime import date
from decimal import Decimal
from api.regras import ano_valido, combustivel_valido, emissao_valida
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
    cilindrada: Decimal | None = Field(default = None, gt = 0, max_digits = 3, decimal_places = 1, allow_inf_nan = False)
    turbo: bool = Field(default = False)
    placa: str | None = Field(default = None, max_length = 10)
    ano_fabricacao: int = Field(ge = 1886, le = 2027)
    ano_modelo: int = Field(ge = 1886, le = 2027)
    km_atual: int = Field(default = 0, ge = 0, le = 6000000)
    
    @model_validator(mode = 'after')
    def verificar_anos(self) -> 'VeiculoCriar':

        if not ano_valido(self.ano_fabricacao, self.ano_modelo):
            raise ValueError(
                'O ano do modelo deve ser igual ao de fabricação ou no máximo 1 ano maior'
            )
        return self
    
    @model_validator(mode = 'after')
    def verificar_cilindrada(self) -> 'VeiculoCriar':
        
        if not combustivel_valido(self.combustivel, self.cilindrada):
            raise ValueError(
                'Veículo elétrico não tem cilindrada.'
            )
        return self

class VeiculoAtualizar(BaseModel):
    model_config = ConfigDict(extra = 'forbid')
    
    marca: str = Field(default = None,min_length = 2, max_length = 50)
    modelo: str = Field(default = None,min_length = 2,max_length = 80)
    motor: str | None = Field(default = None, max_length = 30)
    combustivel: TipoCombustivelEnum = Field(default = None)
    cilindrada: Decimal | None  = Field(default = None, gt = 0, max_digits = 3, decimal_places = 1, allow_inf_nan = False)
    turbo: bool = Field(default = None)
    placa: str | None = Field(default = None, max_length = 10)
    ano_fabricacao: int = Field(default = None,ge = 1886, le = 2027)
    ano_modelo: int = Field(default = None,ge = 1886, le = 2027)
    km_atual: int = Field(default = None, ge = 0, le = 6000000)

class OrcamentoResposta(BaseModel):
    model_config = ConfigDict(from_attributes = True)

    id: int
    id_veiculo: int
    id_oficina: int
    data_emissao: date
    km: int
    status: StatusOrcamentoEnum

class OrcamentoCriar(BaseModel):
    model_config = ConfigDict(extra = 'forbid')

    id_oficina: int = Field(gt = 0)
    data_emissao: date
    km: int = Field(ge = 0, le = 6000000)

    @field_validator('data_emissao')
    @classmethod
    def verificar_emissao(cls, data_emissao: date) -> date:

        if not emissao_valida(data_emissao):
            raise ValueError(
                'A data de emissão não pode ser maior que a data atual.'
                )
        return data_emissao

class ItemOrcamentoResposta(BaseModel):
    model_config = ConfigDict(from_attributes = True)

    id: int
    id_categoria: int
    descricao: str
    tipo: TipoItemEnum
    quantidade: Decimal
    valor_unitario: Decimal
    subtotal: Decimal

class OrcamentoDetalheResposta(OrcamentoResposta):

    itens: list[ItemOrcamentoResposta]
    total: Decimal


class ItemOrcamentoCriar(BaseModel):
    model_config = ConfigDict(extra = 'forbid', str_strip_whitespace = True)

    id_categoria: int = Field(gt = 0)
    descricao: str = Field(min_length = 1, max_length = 255)
    tipo: TipoItemEnum
    quantidade: Decimal = Field(gt = 0, max_digits = 10, decimal_places = 2, allow_inf_nan = False)
    valor_unitario: Decimal = Field(ge = 0, max_digits = 10, decimal_places = 2,allow_inf_nan = False)
    
class UsuarioResposta(BaseModel):
    model_config = ConfigDict(from_attributes = True)

    id: int
    nome: str
    email: str

class UsuarioCriar(BaseModel):
    model_config = ConfigDict(extra = 'forbid')

    nome: str = Field(min_length = 2, max_length = 100)
    email: EmailStr = Field(min_length = 6, max_length = 150)
    senha: str = Field(min_length = 8, max_length = 128)

class LoginEntrada(BaseModel):
    model_config = ConfigDict(extra = 'forbid')

    email: EmailStr = Field(max_length = 150)
    senha: str = Field(max_length = 128)

class TokenResposta(BaseModel):

    access_token: str
    token_type: str = Field(default = 'bearer')