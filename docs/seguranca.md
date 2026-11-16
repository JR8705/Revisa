# Segurança do Revisa

Este documento reúne o trabalho de segurança feito na API do Revisa: o que foi atacado, o que apareceu, o que foi corrigido e qual teste garante que a correção continua no lugar.

## Introdução

O Revisa é uma API (FastAPI + PostgreSQL) para registrar veículos e orçamentos de oficina. Ela gera alertas sobre cobranças suspeitas, como preço acima da referência, item duplicado ou troca recente da mesma peça. A regra central de segurança é simples: **cada usuário só vê e altera os próprios dados**.

**Para quem é este documento:** alguém técnico que não acompanhou o projeto. Não é preciso ler o código; os nomes de arquivos e funções aparecem para quem quiser conferir.

**Como cada seção está organizada:**

1. **Cenário:** o que um atacante tentaria.
2. **O que foi feito:** o teste, a ferramenta ou a medição, com o resultado.
3. **Defesa:** o que barra o ataque e por quê.
4. **Garantia:** o teste automatizado que falha se a defesa for removida.

**Ambientes:**

| Ambiente | O que é | Usado para |
|---|---|---|
| Testes | PostgreSQL recriado do `schema.sql` + `seed.sql`, igual ao CI | pytest (455 testes), fuzzing, mutações |
| Contêiner local | Docker Compose (API + PostgreSQL) na máquina do autor | varredura pesada (ZAP ativo, sqlmap no nível máximo) |
| Produção | Render (contêiner) + Neon (PostgreSQL gerenciado), planos gratuitos | medição dos proxies, varredura leve |

**Mutação**, termo que aparece em várias seções: quebrar a defesa de propósito no código, rodar os testes e confirmar que algum falha; depois desfazer. Se nenhum teste cai, o teste não estava protegendo nada.

## Resumo dos achados

**Defeitos reais encontrados e corrigidos.** A gravidade é avaliação do projeto, considerando uma API pública com dados de usuários.

| Achado | Gravidade | Como foi achado | Correção | Quando |
|---|---|---|---|---|
| Rajada de 30 logins passava pelo limite de 5 (TOCTOU) e levava o processo a ~2 GB | 🔴 Alta | teste de rajada | checar e registrar na mesma trava + semáforo do argon2 | PR #8 |
| Corrida aprovar × recusar: os dois pedidos venciam, e um item podia entrar num orçamento já aprovado | 🔴 Alta | red team da aprovação | trava da linha (`FOR UPDATE`) | 01/11/2026 |
| Byte nulo em campo de texto → 500 | 🟠 Média | fuzzing (Schemathesis) | tipo `Texto` | PR #4 |
| `Infinity`/`NaN` cru no JSON → 500 | 🟠 Média | red team da aprovação | erro de validação sem ecoar a entrada | 01/11/2026 |
| Id acima do limite do `INTEGER` → 500 | 🟠 Média | red team da aprovação | `IdCaminho` com teto | 01/11/2026 |
| As regras padrão do gitleaks não pegavam URL de banco com senha | 🟠 Média | commit de teste | regra própria `url-com-senha` | PR #4 |
| 2 bibliotecas com CVE publicada | 🟠 Média | pip-audit | versões atualizadas | PR #9 |
| 7 vulnerabilidades HIGH no `pip` embutido na imagem | 🟠 Média | trivy | `pip` fora da imagem final | PR #9 |
| Erro 422 das regras fora do formato prometido no contrato | 🟡 Baixa | fuzzing | `erro_422` no formato padrão | PR #4 |
| Cabeçalhos de segurança ausentes | 🟡 Baixa | ZAP passivo | middleware de cabeçalhos | PR #14 |

**Defesas verificadas, sem defeito encontrado:**

| Defesa | Como foi verificada |
|---|---|
| Dono no `WHERE` (IDOR aninhado) | testes de posse; a mutação que remove a defesa derruba 6 testes |
| Consulta interna pelo objeto validado (IDOR lateral) | teste do vazamento; a mutação derruba 17 testes |
| `PROXIES_CONFIAVEIS=3` | medido em produção com e sem `X-Forwarded-For` forjado |
| Consulta parametrizada | sqlmap no nível máximo: não injetável |
| Limite de tentativas sob tráfego real | o ZAP ativo foi bloqueado com ~330 respostas 429 |

**Nenhuma ferramenta nem teste encontrou injeção de SQL, XSS ou IDOR explorável na versão atual.** O que isso não garante está em "O que a varredura não prova" e em "Limites conhecidos".

O red team da aprovação (01/11/2026) não tem seção própria neste documento: os dois achados de entrada aparecem em "Entrada inválida", e a corrida está descrita no README ("Red team da aprovação").

## Controle de acesso (IDOR)

IDOR (*Insecure Direct Object Reference*) é quando a API recebe o id de um recurso e o entrega sem conferir se ele pertence a quem pediu. É a falha mais comum em APIs: trocar `/orcamentos/10` por `/orcamentos/11` e ler o orçamento de outra pessoa.

**Regras usadas em todas as rotas:**

- **O id do usuário vem do token** (JWT assinado pelo servidor), nunca da URL nem do corpo.
- **O dono fica dentro do `WHERE`** da mesma consulta que busca o dado, e não numa checagem separada depois.
- **"Não existe" e "é de outro" devolvem o mesmo 404, com o mesmo corpo.** Assim o atacante não descobre nem que o id existe.

### IDOR aninhado

**Cenário.** As rotas de orçamento ficam dentro do veículo: `/veiculos/{id_veiculo}/orcamentos/{id_orcamento}`. O orçamento não tem dono direto; o dono vem do veículo. A implementação ingênua confere só a primeira parte do caminho:

1. O veículo da URL é do usuário? **Sim**: o intruso põe o próprio veículo.
2. Busca o orçamento pelo id. **Devolve o orçamento alheio.**

Com `/veiculos/{veiculo_do_intruso}/orcamentos/{orcamento_da_vitima}`, o intruso lê, aprova e adiciona itens no orçamento de outra pessoa. Cada parte do caminho, isolada, parece válida; o defeito está na relação entre elas.

**Defesa.** `buscar_orcamento_do_usuario` (`api/main.py`) amarra as três condições numa consulta só:

```python
select(Orcamento)
.join(Veiculo)
.where(
    Orcamento.id == id_orcamento,
    Orcamento.id_veiculo == id_veiculo,
    Veiculo.id_usuario == id_usuario,
)
```

O `JOIN` confere o dono do veículo **ao qual o orçamento pertence de fato**, e não o veículo que veio na URL. Todas as rotas de orçamento passam por essa função: ler, adicionar item, aprovar/recusar e alertas.

A segunda condição também fecha uma variação: o dono que põe no caminho **outro veículo dele mesmo**. Não é vazamento, mas deixaria a URL mentir sobre o veículo do orçamento, e as regras que dependem do veículo (o histórico de trocas, abaixo) leriam o veículo errado.

**Garantia.** Os testes `test_404_identicos` (em `test_orcamentos.py`, `test_aprovacao.py` e `test_alertas_api.py`) fazem quatro pedidos e exigem **quatro 404 com o mesmo texto**:

| Pedido | Quem pede |
|---|---|
| veículo da vítima + orçamento da vítima | intruso |
| **veículo do intruso + orçamento da vítima** (aninhado) | intruso |
| outro veículo do dono + orçamento do dono | dono |
| ids inexistentes | dono |

Nos testes de escrita (item, aprovação), o teste também confere no banco que nada mudou.

**Mutação conferida em 16/11/2026:** trocar a função pela versão ingênua (checa o veículo e depois busca o orçamento só pelo id) derruba **6 testes**. Nos testes de posse, o intruso passa a receber **200**.

### IDOR por caminho lateral

**Cenário.** A rota de alertas já confere o dono do orçamento (seção anterior). Só que, para gerar o alerta `TROCA_RECENTE`, ela faz uma **segunda consulta, interna**: "orçamentos aprovados anteriores com a mesma peça". Essa consulta não vem de nenhuma URL e por isso é fácil esquecer de filtrá-la.

Se ela buscar todos os orçamentos aprovados, a troca de óleo de **outro usuário** vira "troca anterior", e a mensagem do alerta conta ao dono a quilometragem e a época da manutenção de terceiros. Nenhum id foi adulterado e o atacante nem precisa agir: o dado vaza por um caminho que não é a porta da frente.

**O que foi feito.** Com o filtro retirado (mutação), o dono recebeu este alerta sobre uma troca feita no veículo de outra pessoa:

```json
{"tipo": "TROCA_RECENTE", "mensagem": "O item 'Óleo sintético (litro)' foi trocado há -68000 km e 0 meses."}
```

O km negativo é a diferença para o hodômetro de **outro veículo**: dado alheio dentro de uma resposta legítima.

**Defesa.** A consulta interna filtra pelo **veículo do orçamento já validado** (`orcamento.id_veiculo`, o objeto devolvido por `buscar_orcamento_do_usuario`), nunca pelo id que veio na URL. Isso virou regra do projeto: **toda consulta interna sobre dados do usuário filtra pelo objeto validado**.

**Garantia.** `test_troca_de_outro_usuario_nao_vaza` (`test_alertas_api.py`): o intruso aprova uma troca de óleo no próprio veículo, o dono abre um orçamento com óleo, e o teste exige **lista vazia** e nenhuma ocorrência de "trocado" na resposta. **Mutação conferida em 16/11/2026:** tirar o filtro do veículo derruba **17 testes** (suíte sem os testes lentos e sem o fuzzing).

### O que não é IDOR

Oficinas, categorias e faixas de preço de referência são **catálogo compartilhado**: não têm dono, e a consulta não filtra por usuário, de propósito. O risco ali é outro. Quando as faixas vierem dos preços lançados pelos usuários, alguém pode lançar valores falsos para mexer na referência (**envenenamento de dados**). Por isso, hoje só contam as faixas de fonte `MANUAL`, pesquisadas e gravadas pelo projeto.

## Entrada inválida (fuzzing e byte nulo)

Esta seção trata de **entrada que ninguém previu**. Não é o ataque esperto, é o valor estranho: um caractere invisível, um número fora do comum, um tipo errado. Se a API devolve **500 (erro interno)** em vez de **422 (entrada recusada)**, isso já é um achado. Significa que o dado passou da validação e quebrou algo lá dentro. Nesse caso, o atacante tem um jeito barato de derrubar pedidos e muitas vezes recebe pistas do que existe por trás.

### Fuzzing com Schemathesis

**O que é.** Fuzzing é bombardear a API com entradas geradas automaticamente e observar o que quebra. O Schemathesis lê o contrato da API (`/openapi.json`, que o FastAPI gera a partir dos schemas) e monta pedidos para todas as rotas: válidos, quase válidos e absurdos. A ferramenta não sabe o que a rota deveria fazer; ela só confere duas coisas:

- **nenhuma resposta 500;**
- **toda resposta dentro do contrato**, ou seja, a API devolve o formato que ela mesma promete.

**Como roda** (`tests/test_fuzz.py`, dentro do pytest e no CI a cada push): com o token de um usuário criado para o teste, em duas rodadas por rota.

| Rodada | Ids no caminho | O que exercita |
|---|---|---|
| `test_fuzz_ids_quaisquer` | sorteados | quase sempre 404: o caminho de quem tenta o recurso alheio |
| `test_fuzz_recursos_do_dono` | os do próprio usuário | os corpos de verdade: criar, alterar, aprovar |

Tudo o que o fuzzing cria é apagado no fim do módulo.

**Achados (08/11/2026):**

| Achado | Antes | Depois |
|---|---|---|
| Byte nulo em campo de texto (detalhes abaixo) | **500** | 422 |
| Regras checadas dentro da rota (ano, oficina inválida etc.) devolviam o erro como texto, mas o contrato promete uma lista | resposta fora do contrato | o mesmo formato de lista da validação automática (`erro_422` em `api/erros.py`) |

O segundo achado não é uma falha explorável, mas pesa: um cliente que confia no contrato quebra ao receber um formato diferente.

### O byte nulo

**Cenário.** O caractere `\x00` (byte nulo) é texto válido para o Python e para o JSON, mas o **PostgreSQL não aceita esse caractere em campo de texto**. Um cadastro com `"marca": "A\u0000B"` passava por toda a validação (tamanho certo, tipo certo) e só explodia no banco:

```text
psycopg.DataError: PostgreSQL text fields cannot contain NUL (0x00) bytes
```

Resultado: **500** em toda rota que grava ou busca texto (`nome`, `marca`, `modelo`, `motor`, `placa`, `descricao` e a busca por placa).

**Defesa.** Um tipo próprio, `Texto` (`api/schemas.py`), que é `str` com uma validação a mais: recusa o byte nulo **antes** de qualquer consulta. Todo campo de texto de entrada usa esse tipo, e isso virou regra do projeto para as rotas novas. A checagem em si é uma função pura em `api/regras.py`:

```python
def texto_sem_nulo(texto):
    return "\x00" not in texto
```

**Garantia.** O fuzzing achou o byte nulo, mas **não serve para garantir que ele continue barrado**, e isso foi medido. Com a defesa desligada (mutação, 16/11/2026), o fuzzing rodou 5 vezes e **só pegou o defeito em 1**. A explicação é que o Schemathesis sorteia as entradas, e o byte nulo é só uma das possibilidades. Por isso, depois do achado, cada campo ganhou um **teste fixo** com `"A\x00B"`: 11 testes em `test_fuzz.py`, que cobrem o cadastro e a alteração de veículo, a busca por placa, o item do orçamento e o cadastro de usuário. Nos testes de escrita, o teste também confere no banco que nada foi gravado. Com a mesma mutação, **os 11 caem**.

> **Lição de método:** o fuzzing é bom para **descobrir**; o teste fixo é o que **trava** o defeito descoberto. Cada achado de fuzzing vira um teste determinístico.

### A mesma classe de erro: `Infinity` e o limite do `INTEGER`

Dois achados do red team da rota de aprovação (01/11/2026) seguem o mesmo padrão "entrada estranha → 500":

| Entrada | Por que dava 500 | Defesa | Garantia |
|---|---|---|---|
| `{"status": Infinity}` (e `NaN`, `-Infinity`) cru no JSON | o 422 da validação ecoava o valor recebido, e `Infinity` não pode ser escrito em JSON válido: a resposta de erro quebrava ao ser montada | o tratador de erro de validação (`validacao_sem_input`, `api/erros.py`) tira o valor recebido da resposta; o erro diz o campo e o motivo, não repete a entrada | `test_json_com_infinity_cru_422`; com o tratador desligado, os 3 casos caem (conferido em 16/11/2026) |
| id no caminho acima de 2.147.483.647 | a coluna é `INTEGER`; o valor passava na validação e estourava no banco | o tipo `IdCaminho` exige um id entre 1 e 2.147.483.647 | testes de ids adulterados (`0`, `-1`, `1e3`, `2**31`, 30 dígitos…) nas rotas de aprovação e alertas |

O último caso fecha o ciclo do fuzzing: em 08/11/2026, com o limite do `IdCaminho` retirado de propósito, **o fuzzing derrubou 7 rotas com 500 sem ajuda**. Foi o mesmo achado do red team, agora encontrado pela ferramenta (registrado no README; não refeito em 16/11).

**O que o fuzzing não cobre:** ele não entende regra de negócio. Um IDOR devolve um 200 bem formado, dentro do contrato, e por isso **passa no fuzzing**. Quem cobre esses casos são os testes de posse da seção anterior.

## Limite de tentativas (rajada e semáforo do argon2)

**Cenário.** Sem limite, o login é uma porta que aceita palpites infinitos. Três ataques usam isso:

- **Força bruta:** muitas senhas contra um e-mail.
- **Password spraying:** uma senha comum (`123456`) contra muitos e-mails. Fica abaixo de qualquer limite por e-mail.
- **Esgotar o servidor:** cada login confere a senha com **argon2**, um hash feito de propósito para ser caro (cerca de 64 MiB de memória por conferência). Uma rajada de logins errados derruba o servidor sem acertar senha nenhuma. Em produção o contêiner tem **512 MB**.

**Defesa: os limites.**

| Rota | Limite | Por quê |
|---|---|---|
| Login, por e-mail | 5 falhas em 15 min | força bruta numa conta |
| Login, por IP | 20 falhas em 15 min | *password spraying* (muitos e-mails, um IP) |
| Cadastro, por IP | 5 tentativas por hora | criação de contas em massa |

As decisões que importam para a segurança:

- **O 429 vem antes do argon2.** O pedido bloqueado não gasta hash, e nem a senha certa passa durante o bloqueio; se passasse, o atacante saberia que acertou.
- **E-mail que não existe bloqueia igual.** Se o limite só contasse contas reais, o 429 revelaria quais e-mails estão cadastrados.
- **O sucesso zera o e-mail, mas não o IP.** Se zerasse o IP, quem tem uma conta válida intercalaria o próprio login entre os palpites em contas alheias e nunca seria bloqueado.

### A rajada: o limite que não limitava (TOCTOU)

**Cenário.** A primeira versão fazia o óbvio, em três passos:

1. **checa:** este e-mail já tem 5 falhas?
2. confere a senha (argon2, centenas de milissegundos);
3. **registra** a falha.

Com pedidos um de cada vez, funciona. Com **30 pedidos ao mesmo tempo**, todos passam pelo passo 1 antes que qualquer um chegue ao passo 3, e todos veem "0 falhas". É uma corrida do tipo **TOCTOU** (*time of check to time of use*): entre checar e agir, o estado muda.

**O que foi medido.** A versão antiga foi reconstruída em 16/11/2026 (mutação) e recebeu 30 logins errados simultâneos com argon2 real, na nuvem do Claude:

| Versão | 401 | 429 | Pico de memória do processo |
|---|---|---|---|
| Checa → confere → registra, sem semáforo (a original) | **30** | **0** | **2.014 MB** |
| Checa e registra juntos, sem semáforo | 5 | 25 | 411 MB |
| Checa e registra juntos, com semáforo (a atual) | 5 | 25 | **219 MB** |

O processo parte de cerca de 150 MB. A primeira linha mostra **dois defeitos somados**: o limite não barrou nada (30 senhas testadas contra um limite de 5) e o pico passou de 2 GB, **quatro vezes a memória do contêiner de produção**. Os números batem com a medição original de 12/11/2026.

**Defesa 1: checar e registrar no mesmo passo.** `tentar` (`api/limite.py`) faz as duas coisas **dentro da mesma trava** (`threading.Lock`): ou a tentativa é registrada na entrada, ou o pedido recebe 429. Não existe mais intervalo entre checar e registrar. Em caso de sucesso, a tentativa do IP é **devolvida** e as falhas do e-mail são zeradas.

```text
pedido → tentar (checa e registra na mesma trava) → bloqueado: 429, sem conferir a senha
                                                  → liberado: confere a senha
```

**Defesa 2: no máximo 2 hashes ao mesmo tempo.** Mesmo com o limite certo, pedidos legítimos simultâneos ainda somam memória. O semáforo `vagas_hash` (`BoundedSemaphore(2)`) envolve todo uso do argon2 (`gerar_hash` e `verificar_senha` em `api/seguranca.py`): o terceiro pedido espera na fila em vez de alocar mais 64 MiB. A tabela mostra o efeito de cada defesa isolada: o limite sozinho leva o pico a 411 MB; o semáforo leva a 219 MB.

**Garantia.**

| Teste (`tests/test_limite.py`) | O que exige | Com a defesa removida (16/11/2026) |
|---|---|---|
| `test_rajada_de_logins_respeita_o_limite` | 30 logins simultâneos, 3 vezes: exatamente 5 × 401 e 25 × 429 | falha (versão antiga: 30 × 401) |
| `test_no_maximo_dois_hashes_ao_mesmo_tempo` | 15 logins simultâneos com um argon2 falso e lento: nunca mais de 2 conferências juntas | falha: **15** ao mesmo tempo |
| `test_rajada_de_cadastros_respeita_o_limite` | 20 cadastros simultâneos: 5 × 409 e 15 × 429 | — |
| `test_login_bloqueado_nao_confere_a_senha` | o argon2 não é chamado durante o bloqueio | — |
| `test_ip_bloqueia_senha_espalhada_em_varios_emails` | *password spraying* barrado pelo limite do IP | — |

Os testes de rajada têm a marca `lento`: rodam no CI e podem ser pulados localmente.

**Limites desta defesa** (detalhados em "Limites conhecidos"):

- **O contador fica na memória do processo.** Ele zera a cada deploy, a cada reinício e a cada vez que o plano gratuito acorda o serviço, e não é dividido entre processos.
- **5 senhas erradas bloqueiam o e-mail de outra pessoa por 15 minutos.** É o custo aceito do limite por e-mail.
- **A fila do semáforo não tem tempo máximo de espera.**

## IP atrás de proxy (`X-Forwarded-For` forjado)

O limite por IP da seção anterior depende de uma pergunta que parece simples: **qual é o IP de quem fez o pedido?** Em produção a resposta não é óbvia.

**O problema.** No Render, o pedido não chega direto ao contêiner. Ele passa por intermediários:

```text
cliente → Cloudflare → proxy interno do Render → contêiner da API
```

O contêiner só vê a conexão do último intermediário. Para não perder a origem, cada proxy **acrescenta** um endereço no fim do cabeçalho `X-Forwarded-For`. Só que esse cabeçalho também pode ser escrito por quem manda o pedido, e o que o cliente escreve vai para o **começo** da lista. É como um envelope com carimbos dos correios: os carimbos de cada agência são confiáveis, mas o remetente pode desenhar carimbos falsos antes de postar.

**Os dois erros possíveis:**

| Erro | Consequência |
|---|---|
| Ignorar o cabeçalho e usar o IP da conexão | todos os clientes aparecem com o IP do proxy e **dividem um contador**: 20 falhas de qualquer pessoa bloqueiam o login de todo mundo |
| Confiar no primeiro endereço da lista | o atacante escreve um IP falso diferente a cada pedido e **cada palpite ganha um contador novo**: o limite por IP deixa de existir |

### A defesa: contar do fim

`ip_do_pedido` (`api/regras.py`) recebe quantos proxies são confiáveis (`PROXIES_CONFIAVEIS`) e pega o endereço **nessa posição, contando do fim da lista**. O fim é escrito pelos proxies; o começo, pelo cliente. Se o cabeçalho estiver ausente ou mais curto que o esperado, vale o IP da conexão. O valor padrão é `0` (ignorar o cabeçalho), que é o seguro para rodar sem proxy, como no contêiner local.

### A medição em produção

O número de proxies não está na documentação de forma confiável e pode mudar com a hospedagem, por isso **foi medido**. Uma rota temporária, `GET /diagnostico-ip`, devolvia o IP da conexão, o `X-Forwarded-For` recebido e o IP que o limite usaria. Ela entrou num PR e saiu no seguinte. A rota não exigia login, mas só mostrava a quem perguntava os próprios dados de rede, e ficou no ar apenas durante a medição.

Resultado (endereços trocados por exemplos):

| Pedido | `X-Forwarded-For` que chegou | Cliente na posição |
|---|---|---|
| normal | `203.0.113.7, <Cloudflare>, <proxy interno>` | 3ª a partir do fim |
| com cabeçalho forjado `X-Forwarded-For: 9.9.9.9` | `9.9.9.9, 203.0.113.7, <Cloudflare>, <proxy interno>` | **continua na 3ª** |

O endereço forjado entrou **no começo** e ficou fora da posição lida. Daí `PROXIES_CONFIAVEIS=3`, conferido nos dois casos. O efeito de cada valor possível:

| `PROXIES_CONFIAVEIS` | IP usado pelo limite | Efeito |
|---|---|---|
| 0 ou 1 | proxy interno do Render | todos os clientes dividem um contador |
| 2 | servidor da Cloudflare | clientes do mesmo servidor dividem o contador |
| **3** | **cliente** | **correto** |
| 4 | o que o cliente escrever | o limite por IP deixa de valer |

O erro mais perigoso é o **4** (contar um a mais): nada quebra visivelmente, o login funciona normalmente, e o limite simplesmente para de proteger. Por isso o valor veio de medição, não de suposição.

### Garantia

| Teste (`tests/test_limite.py`) | O que exige |
|---|---|
| `test_ip_do_pedido` (12 casos) | a posição certa contando do fim; cabeçalho ausente, vazio, com espaços, com entradas vazias ou mais curto que o esperado → IP da conexão |
| `test_cabecalho_forjado_nao_troca_o_ip` | com o padrão `0`, trocar `X-Forwarded-For`, `X-Real-IP` e `Forwarded` a cada pedido **não** escapa do limite por e-mail nem do limite por IP |

**Mutação conferida em 16/11/2026:** trocar a leitura do fim pela leitura do primeiro endereço (o erro clássico) derruba **5 dos 12 casos** de `test_ip_do_pedido`.

**🟠 Dependência da hospedagem:** `3` vale para o Render de hoje (Cloudflare + 1 proxy). Mudar de plano, de hospedagem ou pôr um domínio próprio com outro proxy na frente pode mudar a quantidade, e a medição tem de ser refeita.

## Varredura com ZAP e sqlmap

As seções anteriores testam defesas que o projeto já conhecia. A varredura responde à pergunta oposta: **o que uma ferramenta de ataque, sem conhecer o código, encontra?**

**As ferramentas.**

| Ferramenta | O que faz | Analogia |
|---|---|---|
| **OWASP ZAP 2.17.0**, modo passivo | lê as respostas e aponta o que falta (cabeçalhos, cookies, vazamento de informação), sem mandar nada malicioso | vistoriador que só anota |
| **OWASP ZAP**, modo ativo | manda payloads de ataque (injeção, XSS, travessia de caminho…) em toda rota do `/openapi.json`, com o token de uma conta descartável | vistoriador que força as portas |
| **sqlmap 1.10.11** | especialista em injeção de SQL: milhares de variações por campo, inclusive injeção cega por tempo | chaveiro especialista |

**Onde rodou.**

| Rodada | Alvo | Intensidade |
|---|---|---|
| pesada | contêiner local (Docker Compose) | ZAP passivo + ativo; sqlmap `--level=5 --risk=3` (o máximo) |
| leve | produção | ZAP passivo; sqlmap `--level=1 --risk=1 --threads=1 --delay=1` |

A rodada pesada fica no contêiner local por dois motivos. Em produção ela gastaria a cota do plano gratuito e faria o próprio limite de tentativas bloquear o teste. Além disso, o banco local pode ser descartado depois. Em produção, a varredura mirou **só a URL do próprio projeto**, e as contas criadas foram apagadas no fim.

### O laço achar → corrigir → varrer de novo

**Achado.** O ZAP passivo apontou **cabeçalhos de segurança ausentes**. Foi o único achado das duas ferramentas, e ele foi deixado de fora de propósito até a varredura, para testar se ela o encontraria.

| Cabeçalho | O ataque que barra |
|---|---|
| `X-Content-Type-Options: nosniff` | o navegador "adivinhar" que uma resposta é HTML ou script e executá-la (*MIME sniffing*) |
| `Cross-Origin-Resource-Policy: same-origin` | outro site embutir e ler as respostas da API |
| `Strict-Transport-Security` | alguém na mesma rede rebaixar a conexão para HTTP e interceptar o token; o navegador passa a recusar HTTP por um ano |

**Correção.** Um middleware em `api/main.py` acrescenta os três em **toda resposta**, inclusive nas de erro. Ele usa `setdefault`, para não sobrescrever um cabeçalho que alguma rota defina de propósito.

**Re-varredura.** O ZAP passivo rodou de novo, local e em produção: **0 alertas**. O HSTS só tem efeito de verdade em produção, porque o navegador só o respeita em HTTPS.

**Garantia.** `tests/test_cabecalhos.py`: os três cabeçalhos numa rota pública e numa resposta 401. O teste da resposta de erro existe porque é fácil pôr cabeçalho só no caminho feliz.

Ficaram de fora, de propósito: `Content-Security-Policy` e `X-Frame-Options`. Uma política rígida quebraria a documentação interativa (`/docs`), que carrega scripts de fora. Ver "Limites conhecidos".

### O limite de tentativas bloqueou o próprio scanner

Durante o ZAP ativo, as rotas de login e cadastro devolveram **cerca de 330 respostas 429**. O limite da seção "Limite de tentativas" tratou a ferramenta como trataria um ataque de força bruta, e isso é um **achado positivo**: a defesa funciona contra tráfego real, não só nos testes.

A consequência para quem lê o relatório: **nessas duas rotas, o ZAP testou bem menos do que parece**, porque a maior parte dos payloads parou no 429. Elas já estavam cobertas pelos testes da seção do limite e pelo fuzzing (que roda com o limite folgado). As rotas autenticadas de leitura e escrita não têm esse limite e foram varridas por inteiro.

### Injeção de SQL: não injetável

**Resultado.** O sqlmap no nível máximo, contra `/veiculos/{id}` e `/veiculos/placa/{placa}` (as rotas que recebem texto livre do usuário e consultam o banco), concluiu **não injetável**. Na rodada leve em produção, mesmo resultado. A opção `--jwt`, que tenta manipular o token, recebeu **401**: o token é assinado pelo servidor, e alterá-lo invalida a assinatura.

**Por quê: duas camadas, em ordem.**

1. **O schema recusa antes do banco.** O id do caminho é um inteiro entre 1 e 2.147.483.647; a placa tem no máximo 10 caracteres; todo texto passa pelo tipo `Texto`. A maior parte dos payloads morre aí, com **422**: no ZAP ativo foram cerca de 3.300 respostas 422.
2. **A consulta é parametrizada.** O que passa pelo schema chega ao banco **como valor, nunca como código SQL**. O SQLAlchemy envia a consulta e o valor separados, e o PostgreSQL nunca interpreta o valor como comando.

A segunda camada é a que importa de verdade, e foi conferida em 16/11/2026:

| Pedido | Resposta | Camada que barrou |
|---|---|---|
| `/veiculos/1 OR 1=1` | 422 (não é inteiro) | schema |
| `/veiculos/placa/' OR '1'='1' --` | 422 (mais de 10 caracteres) | schema |
| `/veiculos/placa/' OR 1=1--` | **404** (nenhum veículo com essa placa) | consulta parametrizada |

O último payload tem exatamente 10 caracteres, **passa pelo schema e chega ao banco**. Mesmo assim, o banco procura um veículo cuja placa seja literalmente `' OR 1=1--` e não acha nenhum. **O schema reduz a superfície; quem impede a injeção é o parâmetro.** Um schema mais folgado (placa com 50 caracteres) não abriria uma falha. O contrário, montar o SQL com f-string, abriria a falha mesmo com o schema mais rígido. O laboratório de SQL Injection do projeto mostrou isso: numa versão vulnerável, escrita só localmente e nunca commitada, `' OR '1'='1` na placa devolvia **todos os veículos do banco**, de todos os usuários.

### O que a varredura não prova

- **Ausência de achado não é ausência de falha.** ZAP e sqlmap testam padrões conhecidos. Um IDOR, por exemplo, devolve um 200 bem formado e passa pelas duas ferramentas; quem cobre IDOR são os testes de posse.
- As ferramentas e os scripts que as rodam ficam **fora do repositório** (ver "Como reproduzir"). Os números desta seção (330 × 429, 3.300 × 422) vêm dos relatórios de 16/11/2026, gerados na máquina do autor; a tabela das camadas foi reproduzida na nuvem.

## Cadeia de suprimentos

**Cenário.** A maior parte do código que roda no Revisa não foi escrita pelo projeto: bibliotecas Python, a imagem base do Docker, as *actions* do GitHub, as ferramentas de varredura. Se uma delas for adulterada, o ataque não precisa achar falha nenhuma na API. Ele já entra rodando, dentro do pipeline ou do contêiner, com acesso ao que estiver ali (o token do GitHub, os segredos do CI, os dados).

O ponto fraco mais comum é a **referência por nome**. `actions/checkout@v5` ou `python:3.14-slim` parecem fixos, mas **uma tag é um ponteiro que o dono pode mover**. Quem controla o repositório, ou quem roubou a credencial do dono, aponta a mesma tag para outro código, e todo pipeline que usa a tag baixa a versão nova sem perceber.

### O caso da `trivy-action` (março de 2026)

Não é hipótese. Em 19/03/2026, atacantes com uma credencial roubada **reescreveram quase todas as tags de versão** da `aquasecurity/trivy-action`, a *action* oficial do scanner trivy, para apontar a um código que roubava os segredos do pipeline. A varredura legítima rodava depois, e por isso o log parecia normal. Quem usava a *action* por tag rodou o código malicioso; **quem usava por SHA de commit não foi afetado**. No mesmo episódio também foi publicado um binário malicioso do próprio trivy (versão 0.69.4).

O Revisa usa o trivy para varrer a imagem. O incidente decidiu como ele é instalado (abaixo).

### As defesas

| O quê | Como é referenciado | Por quê |
|---|---|---|
| *Actions* do GitHub (`checkout`, `setup-python`) | **SHA do commit**, com a versão num comentário (`@fbc6f39… # v5.1.0`) | um SHA aponta para um conteúdo específico e não pode ser movido |
| gitleaks e trivy no CI | **binário com versão fixa e SHA-256 conferido** antes de rodar (`sha256sum --check`); se o arquivo mudar, o job falha | dispensa *actions* de terceiros, que receberiam o token do pipeline |
| Imagem do ZAP | **digest** (`ghcr.io/zaproxy/zaproxy@sha256:9624…28af`) | o digest é o hash do conteúdo da imagem; a tag `stable` muda a cada versão |
| sqlmap | pacote do PyPI com SHA-256 conferido, num ambiente Python separado, fora do repositório | a ferramenta de ataque não se mistura às dependências da API |
| Token do pipeline | `permissions: contents: read` no workflow | mesmo que um passo seja comprometido, o token não consegue escrever no repositório |

**O limite do checksum.** O SHA-256 garante que o arquivo baixado é **o mesmo que foi escolhido**, mas não que a escolha foi boa: quem tivesse fixado o checksum do trivy 0.69.4 teria fixado o binário malicioso. Por isso a regra do projeto é **escolher uma versão que já tenha semanas de uso público** e só então fixar o checksum. A versão do trivy no CI é a 0.76.1.

### O que as verificações já barraram

Estas ferramentas rodam no CI a cada push, e um achado bloqueia o merge:

| Verificação | Achado | Correção |
|---|---|---|
| **pip-audit** (bibliotecas com vulnerabilidade publicada) | 2 CVEs, em `dnspython` e `opentelemetry-api` | versões atualizadas no `requirements.txt` (PR #9) |
| **trivy** (pacotes dentro da imagem Docker) | 7 vulnerabilidades HIGH, todas no `pip` que vinha embutido na imagem base | o `pip` saiu da imagem final (ele só é usado no estágio de build) e os pacotes do sistema são atualizados no build (PR #9) |
| **gitleaks** (segredos no código e no histórico) | as regras padrão **não pegaram** uma URL de banco com senha num commit de teste | regra própria `url-com-senha` no `.gitleaks.toml`, no pre-commit e no CI (PR #4) |

O segundo achado mostra o princípio por trás da correção: **o que não está na imagem não pode ser explorado**. A API não precisa instalar pacotes em produção, então o instalador de pacotes saiu.

O **Dependabot** abre PRs semanais com atualizações de bibliotecas e *actions*, inclusive trocando os SHAs fixados. Cada PR passa pelo CI inteiro antes de qualquer merge.

### O que ainda está por tag

- As imagens base `python:3.14-slim` e `postgres:16-alpine` ainda são referenciadas por tag, sem digest.
- Como o build atualiza os pacotes do sistema, a imagem depende do dia em que foi construída. A rede de segurança é o trivy, que varre a imagem final a cada build.
- Os ganchos do pre-commit (ruff, gitleaks) não são atualizados pelo Dependabot.

## Limites conhecidos

O que **não** está resolvido, de propósito ou por enquanto. Cada linha é um risco aceito com motivo, não um esquecimento.

| Limite | Risco | Quando resolver |
|---|---|---|
| 🟠 Contador de tentativas na memória do processo | zera a cada deploy, reinício ou vez que o plano gratuito acorda o serviço; não é dividido entre processos (só vale com uma instância) | armazenamento externo, quando houver mais de uma instância |
| 🟠 `PROXIES_CONFIAVEIS` depende da hospedagem | se a cadeia de proxies mudar, o limite por IP passa a dividir contador (a menos) ou a aceitar IP forjado (a mais) | medir de novo a cada mudança de hospedagem, plano ou domínio |
| 🟠 Sem rota para apagar a conta | o usuário não consegue apagar os próprios dados; contas de teste em produção são limpas direto no banco | antes de ter usuários reais |
| 🟡 5 senhas erradas bloqueiam o e-mail de outra pessoa por 15 min | quem sabe o e-mail de alguém consegue atrapalhar o login dessa pessoa | aceito: é o custo do limite por e-mail |
| 🟡 Fila do semáforo do argon2 sem tempo máximo | uma rajada longa deixa pedidos legítimos esperando sem resposta; não foi medido com a CPU de produção | junto com o limite externo |
| 🟡 Token sem revogação | o token vale até expirar (30 min); não há logout. Usuário apagado é barrado na hora | futuro |
| 🟡 Sem `Content-Security-Policy` nem `X-Frame-Options`; `/docs` público | uma política rígida quebraria a documentação interativa; o `/docs` mostra o mapa da API a qualquer pessoa (sem dados) | quando o `/docs` sair de produção ou ganhar política própria |
| 🟡 Sem limite de itens por orçamento | um orçamento com milhares de itens deixa a rota de alertas cara (negação de serviço por um usuário autenticado) | antes de ter usuários reais |
| 🟡 A API conecta ao banco com um usuário de permissão ampla | se houver uma injeção no futuro, o estrago não fica restrito às tabelas da aplicação | papel com permissão mínima, depois do marco |
| 🟡 401, 404, 409 e 429 fora do `/openapi.json` | o fuzzing não confere se o código de status está documentado | documentar as respostas nas rotas |
| 🟡 Mensagem do alerta repete o texto digitado | se uma tela futura mostrar a mensagem sem escapar, um `<script>` gravado na descrição roda no navegador (XSS armazenado). A API devolve JSON e não executa nada | regra para o front-end: nunca inserir a mensagem como HTML |
| 🟡 Imagens base por tag | ver "Cadeia de suprimentos" | depois do marco |

## Como reproduzir

**Testes automatizados** (o mesmo que o CI roda a cada push; o banco de testes é recriado do `schema.sql` + `seed.sql`):

```bash
pytest                   # tudo: 455 testes, inclusive fuzzing e rajadas
pytest -m "not lento"    # pula corridas, rajadas e a medição de tempo do login
pytest -m "not fuzz"     # pula o Schemathesis e os testes de byte nulo
```

| Tema deste documento | Arquivo de teste |
|---|---|
| IDOR aninhado e lateral | `test_orcamentos.py`, `test_aprovacao.py`, `test_alertas_api.py`, `test_veiculos.py` |
| Entrada inválida | `test_fuzz.py`, `test_aprovacao.py` (red team) |
| Limite de tentativas e IP atrás de proxy | `test_limite.py` |
| Cabeçalhos de segurança | `test_cabecalhos.py` |

**Mutações.** Para conferir que um teste protege uma defesa: remova a defesa no código (a seção correspondente diz qual trecho), rode o arquivo de teste, confira que ele falha e desfaça a mudança.

**Varredura (ZAP e sqlmap).** Os scripts que rodam as ferramentas **não estão no repositório**, de propósito:

- **Um kit de ataque pronto num repositório público** serve a qualquer pessoa, inclusive contra a URL de produção do próprio projeto.
- **Os scripts manipulam um token de acesso e o endereço de produção**, que não devem ficar versionados.
- **Ferramenta de ataque só roda contra alvo autorizado.** Quem for reproduzir deve usar o contêiner local, nunca um serviço de terceiros.

Para refazer a rodada pesada: suba o contêiner local (`docker compose up --build -d`); rode o ZAP pela imagem oficial, fixada por digest, contra o `/openapi.json` local; e rode o sqlmap no nível máximo (`--level=5 --risk=3`) contra `/veiculos/{id}` e `/veiculos/placa/{placa}`, usando o token de uma conta descartável. No fim, `docker compose down -v` apaga o banco junto com tudo o que a varredura criou.
