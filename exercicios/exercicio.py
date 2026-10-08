from decimal import Decimal, InvalidOperation

itens = []

def calcular_orcamento(itens):

    orcamento_total = Decimal('0.00')
    valor_mao = Decimal('0.00')
    valor_peca = Decimal('0.00')
    
    for item in itens:

        subtotal = item['valor'] * item['quantidade']

        orcamento_total += subtotal

        if item['tipo'] == 'MAO_OBRA':
            valor_mao += subtotal
        elif item['tipo'] == 'PECA':
            valor_peca += subtotal

    return orcamento_total,valor_mao,valor_peca

def calcular_perc(valor_mao,valor_peca,total):
    if total == 0:
        return Decimal('0.00'), Decimal('0.00')
    
    p1 = (valor_mao/total)
    p2 = (valor_peca/total)
    return p1, p2

def gerar_alertas(perc2, perc_aviso):

    if perc2 > perc_aviso/100:
        print(f"ALERTA: Mão de obra de {perc2*100:.2f}% do total! Limite de {perc_aviso}%")

def ler_decimal(mensagem):
    while True:
        try:
            entrada_mensagem = input(mensagem).replace(',','.')
            entrada_mensagem = Decimal(entrada_mensagem)
            if entrada_mensagem < 0:
                print('Erro! Digite apenas números positivos.')
            else:
                return entrada_mensagem

        except InvalidOperation:
            print('Erro! Digite apenas números válidos.')

def ler_tipo(mensagem):
    while True:

        entrada_mensagem = input(mensagem).strip().lower()
        if entrada_mensagem not in ['1','2']:
            print('Erro! Digite um tipo de item válido.')
        else:
            if entrada_mensagem == '1':
                entrada_mensagem = 'MAO_OBRA'
            else:
                entrada_mensagem = 'PECA'
            return entrada_mensagem

print('--- CADASTRO DE ITENS DO ORÇAMENTO ---')

while True:
    
    descricao =  input('\nDigite a descrição do item: ')
    tipo = ler_tipo('\nDigite o tipo do item (1. Mão de obra / 2. Peça): ')
    quantidade = ler_decimal('Digite a quantidade do item: ')
    valor_unitario = ler_decimal('Digite o valor do item: R$')


    novo_item = {
        'descricao': descricao,
        'tipo': tipo,
        'quantidade': quantidade,
        'valor': valor_unitario
    }

    itens.append(novo_item)

    continuar = input('Deseja adicionar mais um item? (s/n): ').strip().lower()
    if continuar == 'n':
        break

aviso = ler_decimal("Porcentagem para o aviso: ")

orcamento_total,valor_mao,valor_peca = calcular_orcamento(itens)
perc_mao, perc_peca = calcular_perc(valor_mao, valor_peca, orcamento_total)

print(f'Orçamento total de: R${orcamento_total:.2f}')
print(f'Valor Peça: R${valor_peca:.2f} ({perc_peca:.2%})')
print(f'Valor Mão de obra: R${valor_mao:.2f} ({perc_mao:.2%})')

gerar_alertas(perc_mao, aviso)