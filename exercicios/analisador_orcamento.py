from decimal import Decimal, InvalidOperation

def calcular_orcamento(itens):

    orcamento_total = Decimal('0.00')
    valor_mao = Decimal('0.00')
    valor_peca = Decimal('0.00')
    
    for item in itens:

        subtotal = item['valor_unitario'] * item['quantidade']

        orcamento_total += subtotal

        if item['tipo'] == 'MAO_OBRA':
            valor_mao += subtotal
        elif item['tipo'] == 'PECA':
            valor_peca += subtotal

    return orcamento_total,valor_mao,valor_peca

def calcular_perc(valor_mao,valor_peca,total):
    if total == 0:
        return Decimal('0.00'), Decimal('0.00')
    
    perc_mao = (valor_mao/total)
    perc_peca = (valor_peca/total)
    return perc_mao, perc_peca

def gerar_alertas(perc_mao, limite_mao_obra,itens):
    alertas = []
    desc_vistas = []

    for item in itens:
        descricao_entrada = item['descricao']
        descricao = descricao_entrada.strip().lower()
        if descricao in desc_vistas:
            alertas.append(f'ALERTA! Item duplicado: {descricao_entrada}')
        else:
            desc_vistas.append(descricao)
        
        if item['valor_unitario'] == 0:
            alertas.append(f'ALERTA! Item com valor zerado: {descricao_entrada}')

    if perc_mao > limite_mao_obra/100:
        alertas.append(f'ALERTA! Mão de obra de {perc_mao*100:.2f}% do total! Limite de {limite_mao_obra}%')

    return alertas

def ler_decimal(mensagem):
    while True:
        try:
            entrada_mensagem = input(mensagem).replace(',','.')
            entrada_mensagem = Decimal(entrada_mensagem)
            if entrada_mensagem.is_finite():
                if entrada_mensagem < 0:
                    print('Erro! Digite apenas números positivos.')
                else:
                    return entrada_mensagem
            else:
                print('Erro! Digite um número finito.')
        except InvalidOperation:
            print('Erro! Digite apenas números válidos.')

def ler_tipo(mensagem):
    tipos = {'1': 'MAO_OBRA',
            '2': 'PECA'}
    while True:

        entrada_mensagem = input(mensagem).strip()
        if entrada_mensagem in tipos:
            return tipos[entrada_mensagem]
        else:
            print('Erro! Digite um tipo de item válido.')



def cadastrar_itens():
    print('--- CADASTRO DE ITENS DO ORÇAMENTO ---')
    itens = []
    while True:
    
        descricao =  input('\nDigite a descrição do item: ')
        tipo = ler_tipo('\nDigite o tipo do item (1. Mão de obra / 2. Peça): ')
        quantidade = ler_decimal('Digite a quantidade do item: ')
        valor_unitario = ler_decimal('Digite o valor do item: R$')


        novo_item = {
            'descricao': descricao,
            'tipo': tipo,
            'quantidade': quantidade,
            'valor_unitario': valor_unitario
        }

        itens.append(novo_item)

        continuar = input('Deseja adicionar mais um item? (s/n): ').strip().lower()
        if continuar == 'n':
            break
    return itens

itens = cadastrar_itens()
limite_mao_obra = ler_decimal("Porcentagem para o alerta: ")
orcamento_total,valor_mao,valor_peca = calcular_orcamento(itens)
perc_mao, perc_peca = calcular_perc(valor_mao, valor_peca, orcamento_total)

print(f'\nOrçamento total de: R${orcamento_total:.2f}')
print(f'Valor Peça: R${valor_peca:.2f} ({perc_peca:.2%})')
print(f'Valor Mão de obra: R${valor_mao:.2f} ({perc_mao:.2%})')



alertas = gerar_alertas(perc_mao, limite_mao_obra,itens)
print()
if not alertas:
    print('Nenhum alerta encontrado!')
else:
    for alerta in alertas:
        print(alerta)