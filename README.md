# Revisa

Aplicativo para registrar manutenções de veículos e **analisar orçamentos de oficina**: extrai os itens do orçamento, compara preços com o histórico e sinaliza cobranças suspeitas antes de você aprovar o serviço.

> **Status:** em desenvolvimento. A modelagem do banco de dados está concluída; a API está em construção.

## O problema

Quem não entende de mecânica não tem como saber se um orçamento está caro, se um item é desnecessário ou se aquela peça já foi trocada há pouco tempo. O Revisa usa o histórico do próprio veículo e uma base de preços de referência para responder a essas perguntas.

## Funcionalidades planejadas

- Cadastro de veículos e histórico de manutenções
- Registro de orçamentos, com itens separados em peça e mão de obra
- Extração automática dos itens a partir de foto ou PDF do orçamento
- Comparação de dois ou mais orçamentos lado a lado
- Orçamento aprovado vira registro de manutenção
- Alertas automáticos na análise do orçamento:

| Alerta | Quando dispara |
|---|---|
| `TROCA_RECENTE` | A mesma categoria foi trocada há poucos km ou meses |
| `PRECO_ACIMA_MEDIA` | Valor acima da faixa de referência ou de um orçamento concorrente |
| `MAO_OBRA_ALTA` | Mão de obra desproporcional ao total |
| `ITEM_DUPLICADO` | Mesmo item lançado mais de uma vez |
| `ITEM_GENERICO` | Descrição vaga, sem discriminação do que será feito |
| `CONSUMIVEL_CARO` | Consumíveis (estopa, graxa, etc.) acima do esperado |
| `VALOR_ZERADO` | Item sem valor, que pode virar cobrança depois |

## Modelo de dados

![Diagrama do banco de dados](database/diagrama.png)

| Tabela | Função |
|---|---|
| `usuarios` | Donos dos veículos |
| `veiculos` | Veículos de cada usuário |
| `oficinas` | Oficinas que emitem os orçamentos |
| `orcamentos` | Orçamento de uma oficina para um veículo |
| `itens_orcamento` | Cada linha do orçamento (peça ou mão de obra) |
| `categorias_item` | Catálogo que padroniza os itens e guarda os intervalos de troca |
| `precos_referencia` | Faixa de preço (mínimo e máximo) esperada por categoria |
| `alertas` | Avisos gerados na análise de um orçamento |
| `manutencoes` | Serviço realizado a partir de um orçamento aprovado |

### Decisões de modelagem

- **Itens categorizados:** oficinas escrevem o mesmo item de formas diferentes. A tabela `categorias_item` padroniza os itens e permite comparar preços e detectar trocas recentes.
- **Total não armazenado:** o valor do orçamento é calculado pela soma dos itens, o que evita divergência entre o total e os itens.
- **Uma manutenção por orçamento:** a chave estrangeira `manutencoes.id_orcamento` é única.
- **Quilometragem no orçamento e na manutenção:** registra o km no momento do serviço, base dos alertas de troca recente.
- **Preço de referência em faixa:** `precos_referencia` guarda mínimo e máximo, com a origem do dado (manual, histórico ou externo).
- **Regras no banco:** restrições `CHECK` impedem quilometragem negativa, quantidade zerada e faixa de preço invertida.

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Banco de dados | PostgreSQL |
| Back-end | Python, FastAPI, SQLAlchemy, Alembic |
| Testes | pytest |
| Infraestrutura | Docker, GitHub Actions |

## Como rodar o banco

Pré-requisito: PostgreSQL 14 ou superior.

```bash
createdb revisa
psql -d revisa -f database/schema.sql
psql -d revisa -f database/seed.sql
psql -d revisa -f database/queries.sql
```

Os arquivos devem ser executados nessa ordem. Também é possível abri-los em um cliente como o DBeaver.

O `queries.sql` traz as consultas usadas para validar o modelo, cada uma com o resultado esperado em comentário.

## Protótipo em terminal

Antes da API, a lógica de cálculo e de alertas está sendo validada em um programa de terminal, sem banco de dados e sem bibliotecas externas.

O `exercicios/analisador_orcamento.py`:

- cadastra os itens de um orçamento (descrição, tipo, quantidade e valor unitário)
- valida a entrada: recusa texto no lugar de número, valores negativos e tipo inexistente, e aceita vírgula como separador decimal
- calcula o total e separa peças de mão de obra, com o percentual de cada um
- alerta quando a mão de obra passa do limite informado

Os valores usam `Decimal`, pelo mesmo motivo do `numeric(10,2)` no banco: evitar erro de arredondamento com dinheiro. Os tipos seguem os códigos do enum `tipo_item` (`PECA` e `MAO_OBRA`).

Para rodar (Python 3.10 ou superior):

```bash
python exercicios/analisador_orcamento.py
```

Exemplo, com os itens do orçamento 5 do `seed.sql`:

```
Orçamento total de: R$685.00
Valor Peça: R$335.00 (48.91%)
Valor Mão de obra: R$350.00 (51.09%)
ALERTA: Mão de obra de 51.09% do total! Limite de 50%
```

## Estrutura do repositório

```
database/
 ├── schema.sql      estrutura: tipos, tabelas, índices e restrições
 ├── seed.sql        dados iniciais e de teste (fictícios)
 ├── queries.sql     consultas de validação com o resultado esperado
 ├── modelo.dbml     código-fonte do diagrama (dbdiagram.io)
 └── diagrama.png    diagrama do banco

exercicios/
 └── analisador_orcamento.py   protótipo em terminal do cálculo e dos alertas
```

## Roadmap

- [x] Modelagem do banco de dados
- [x] Protótipo em terminal do cálculo e do alerta de mão de obra
- [ ] API: autenticação e cadastro de veículos
- [ ] Orçamentos, itens e histórico de manutenções
- [ ] Upload do orçamento e extração automática dos itens
- [ ] Motor de alertas
- [ ] Comparador de orçamentos e aprovação
- [ ] Testes automatizados, CI e deploy

## Autor

Wellington Strehle — projeto pessoal de estudo e portfólio.
