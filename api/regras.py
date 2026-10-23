
from api.enums import TipoCombustivelEnum
from datetime import date

def emissao_valida(data: date) -> bool:
    return data <= date.today()
            
def ano_valido(ano_fabricacao, ano_modelo):

    return ano_fabricacao <= ano_modelo <= ano_fabricacao + 1

def combustivel_valido(combustivel,cilindrada):
        
    return not (combustivel == TipoCombustivelEnum.ELETRICO and cilindrada is not None)
