-- Revisa — Consultas principais
-- Base: base-teste-v7.sql (resultados esperados calculados sobre ela)
-- Os valores fixos marcados com "parâmetro" viram variáveis na API.

-- 1) Histórico de manutenções de um veículo (mais recente primeiro)

SELECT m.data,
       m.km,
       m.tipo,
       m.status,
       f.nome AS oficina
FROM manutencoes m
JOIN orcamentos o ON o.id = m.id_orcamento
JOIN oficinas   f ON f.id = o.id_oficina
WHERE o.id_veiculo = 3                -- parâmetro: HB20
ORDER BY m.data DESC, m.km DESC

-- Resultado esperado:
--  data       |  km   | tipo      | status       | oficina
--  2026-08-22 | 67500 | CORRETIVA | EM_ANDAMENTO | Mecânica Boa Viagem
--  2026-02-10 | 62000 | CORRETIVA | CONCLUIDA    | Auto Center Primavera

-- 2) Total de peças x total de mão de obra de um orçamento

SELECT i.tipo,
       SUM(i.quantidade * i.valor_unitario)::numeric(12,2) AS total,
       ROUND(100 * SUM(i.quantidade * i.valor_unitario)
                 / SUM(SUM(i.quantidade * i.valor_unitario)) OVER (), 1) AS percentual
FROM itens_orcamento i
WHERE i.id_orcamento = 8              -- parâmetro: embreagem da Strada
GROUP BY i.tipo
ORDER BY i.tipo

-- Resultado esperado:
--  tipo     |  total  | percentual
--  PECA     | 1230.00 |       69.1
--  MAO_OBRA |  550.00 |       30.9
-- Obs.: a ordem segue a declaração do enum (PECA antes de MAO_OBRA).

-- 3) Última troca de uma categoria em um veículo
--    Só considera orçamentos que viraram manutenção (aprovados).

SELECT m.data,
       m.km,
       i.descricao,
       c.nome AS categoria
FROM manutencoes     m
JOIN orcamentos      o ON o.id = m.id_orcamento
JOIN itens_orcamento i ON i.id_orcamento = o.id
JOIN categorias_item c ON c.id = i.id_categoria
WHERE o.id_veiculo = 3                -- parâmetro: HB20
  AND c.id = 10                       -- parâmetro: Pastilha de freio
ORDER BY m.data DESC, m.km DESC
LIMIT 1

-- Resultado esperado:
--  data       |  km   | descricao                          | categoria
--  2026-02-10 | 62000 | Pastilha de freio dianteira (jogo) | Pastilha de freio

-- 4) Preço médio de uma categoria em todos os orçamentos
--    Considera todos os status (pendente, aprovado e recusado).

SELECT c.nome                     AS categoria,
       COUNT(*)                   AS amostras,
       ROUND(AVG(i.valor_unitario), 2) AS preco_medio,
       MIN(i.valor_unitario)      AS menor,
       MAX(i.valor_unitario)      AS maior
FROM itens_orcamento i
JOIN categorias_item c ON c.id = i.id_categoria
WHERE c.id = 2                        -- parâmetro: Óleo do motor sintético
GROUP BY c.nome

-- Resultado esperado:
--  categoria               | amostras | preco_medio | menor | maior
--  Óleo do motor sintético |        4 |       68.00 | 62.00 | 75.00
-- Obs.: média do valor unitário (preço por litro), sem ponderar pela quantidade.

-- 5) Comparar dois orçamentos item a item pela categoria

SELECT c.nome AS categoria,
       COALESCE(SUM(i.quantidade * i.valor_unitario) FILTER (WHERE o.id = 2), 0)::numeric(12,2) AS orc_2,
       COALESCE(SUM(i.quantidade * i.valor_unitario) FILTER (WHERE o.id = 3), 0)::numeric(12,2) AS orc_3,
       (COALESCE(SUM(i.quantidade * i.valor_unitario) FILTER (WHERE o.id = 3), 0)
      - COALESCE(SUM(i.quantidade * i.valor_unitario) FILTER (WHERE o.id = 2), 0))::numeric(12,2) AS diferenca
FROM orcamentos      o
JOIN itens_orcamento i ON i.id_orcamento = o.id
JOIN categorias_item c ON c.id = i.id_categoria
WHERE o.id IN (2, 3)                  -- parâmetro: correia do Gol em 2 oficinas
GROUP BY c.nome
ORDER BY diferenca DESC

-- Resultado esperado:
--  categoria                    | orc_2  | orc_3  | diferenca
--  Bomba d'água                 | 260.00 | 760.00 |    500.00
--  Kit correia dentada          | 420.00 | 690.00 |    270.00
--  Material de consumo/diversos |   0.00 | 150.00 |    150.00
--  Mão de obra                  | 350.00 | 450.00 |    100.00
--  Líquido de arrefecimento     |  84.00 |  96.00 |     12.00
-- Obs.: soma das diferenças = 1032.00 (2146.00 - 1114.00).
--       A bomba d'água aparece com 760.00 porque foi lançada duas vezes no #3.