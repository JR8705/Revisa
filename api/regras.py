
from api.enums import TipoCombustivelEnum
from datetime import date
from decimal import Decimal

def emissao_valida(data: date) -> bool:
    return data <= date.today()
            
def ano_valido(ano_fabricacao, ano_modelo):

    return ano_fabricacao <= ano_modelo <= ano_fabricacao + 1

def combustivel_valido(combustivel,cilindrada):
        
    return not (combustivel == TipoCombustivelEnum.ELETRICO and cilindrada is not None)

def calcular_subtotal(quantidade, valor_unitario):

    subtotal_orcamento = quantidade * valor_unitario

    return subtotal_orcamento.quantize(Decimal('0.01'))

def calcular_total(subtotais):

    total_orcamento = Decimal('0.00')

    for item in subtotais:
        total_orcamento += item

    return total_orcamento