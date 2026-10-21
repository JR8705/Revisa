import enum

class TipoCombustivelEnum(str, enum.Enum):
    FLEX = 'FLEX'
    GASOLINA = 'GASOLINA'
    ETANOL = 'ETANOL'
    DIESEL = 'DIESEL'
    ELETRICO = 'ELETRICO'
    HIBRIDO = 'HIBRIDO'


class GrupoItemEnum(str, enum.Enum):
    FLUIDOS = 'FLUIDOS'
    FILTROS = 'FILTROS'
    FREIOS = 'FREIOS'
    MOTOR = 'MOTOR'
    INJECAO = 'INJECAO'
    SUSPENSAO = 'SUSPENSAO'
    ELETRICA = 'ELETRICA'
    TRANSMISSAO = 'TRANSMISSAO'
    SERVICOS = 'SERVICOS'


class StatusOrcamentoEnum(str, enum.Enum):
    PENDENTE = 'PENDENTE'
    APROVADO = 'APROVADO'
    RECUSADO = 'RECUSADO'


class TipoItemEnum(str, enum.Enum):
    PECA = 'PECA'
    MAO_OBRA = 'MAO_OBRA'