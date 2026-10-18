
from api.enums import TipoCombustivelEnum

def ano_valido(ano_fabricacao, ano_modelo):

    return ano_fabricacao <= ano_modelo <= ano_fabricacao + 1

def combustivel_valido(combustivel,cilindrada):
        
    return not (combustivel == TipoCombustivelEnum.ELETRICO and cilindrada is not None)
