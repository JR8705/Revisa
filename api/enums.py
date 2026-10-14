import enum

class TipoCombustivelEnum(str, enum.Enum):
    FLEX = 'FLEX'
    GASOLINA = 'GASOLINA'
    ETANOL = 'ETANOL'
    DIESEL = 'DIESEL'
    ELETRICO = 'ELETRICO'
    HIBRIDO = 'HIBRIDO'
