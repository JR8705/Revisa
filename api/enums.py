import enum


class TipoCombustivelEnum(str, enum.Enum):
    FLEX = "FLEX"
    GASOLINA = "GASOLINA"
    ETANOL = "ETANOL"
    DIESEL = "DIESEL"
    ELETRICO = "ELETRICO"
    HIBRIDO = "HIBRIDO"


class GrupoItemEnum(str, enum.Enum):
    FLUIDOS = "FLUIDOS"
    FILTROS = "FILTROS"
    FREIOS = "FREIOS"
    MOTOR = "MOTOR"
    INJECAO = "INJECAO"
    SUSPENSAO = "SUSPENSAO"
    ELETRICA = "ELETRICA"
    TRANSMISSAO = "TRANSMISSAO"
    SERVICOS = "SERVICOS"


class StatusOrcamentoEnum(str, enum.Enum):
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"


class TipoItemEnum(str, enum.Enum):
    PECA = "PECA"
    MAO_OBRA = "MAO_OBRA"


class TipoAlertaEnum(str, enum.Enum):
    TROCA_RECENTE = "TROCA_RECENTE"
    PRECO_ACIMA_MEDIA = "PRECO_ACIMA_MEDIA"
    MAO_OBRA_ALTA = "MAO_OBRA_ALTA"
    ITEM_DUPLICADO = "ITEM_DUPLICADO"
    ITEM_GENERICO = "ITEM_GENERICO"
    CONSUMIVEL_CARO = "CONSUMIVEL_CARO"
    VALOR_ZERADO = "VALOR_ZERADO"


class SeveridadeAlertaEnum(str, enum.Enum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"
