-- Revisa — catálogo do banco de produção: oficinas, categorias e preços de referência.
-- Rodar uma vez, depois do schema.sql, em um banco vazio. Não apaga nada e não cria
-- usuários, veículos nem orçamentos (esses são dados de teste e ficam só no seed.sql).
-- As linhas abaixo são cópia das do seed.sql; o tests/test_catalogo.py confere que continuam iguais.
-- As oficinas são fictícias (demonstração) e as faixas de preço 1 a 10 são de teste.

BEGIN;

INSERT INTO oficinas (id, nome, cidade, telefone) VALUES
(1, 'Auto Center Primavera',     'Campinas',  '(19) 3201-1001'),
(2, 'Mecânica Boa Viagem',       'Campinas',  '(19) 99811-2002'),
(3, 'Oficina Express Car',       'Campinas',  '(19) 3302-3003'),
(4, 'Concessionária Rede Norte', 'Campinas',  '(19) 3403-4004'),
(5, 'Garagem do Paulo',          'Sumaré',    '(19) 99722-5005');

INSERT INTO categorias_item (id, nome, grupo, intervalo_km, intervalo_meses) VALUES
(1,  'Óleo do motor semissintético', 'FLUIDOS',     10000, 12),
(2,  'Óleo do motor sintético',      'FLUIDOS',     10000, 12),
(3,  'Fluido de freio',              'FLUIDOS',     NULL,  24),
(4,  'Líquido de arrefecimento',     'FLUIDOS',     40000, 24),
(5,  'Óleo de câmbio',               'TRANSMISSAO', 60000, NULL),
(6,  'Filtro de óleo',               'FILTROS',     10000, 12),
(7,  'Filtro de ar do motor',        'FILTROS',     15000, 12),
(8,  'Filtro de combustível',        'FILTROS',     20000, 12),
(9,  'Filtro de cabine',             'FILTROS',     15000, 12),
(10, 'Pastilha de freio',            'FREIOS',      30000, NULL),
(11, 'Disco de freio',               'FREIOS',      60000, NULL),
(12, 'Lona de freio traseira',       'FREIOS',      50000, NULL),
(13, 'Kit correia dentada',          'MOTOR',       50000, 48),
(14, 'Correia auxiliar',             'MOTOR',       40000, NULL),
(15, 'Velas de ignição',             'MOTOR',       30000, NULL),
(16, 'Bobina de ignição',            'MOTOR',       NULL,  NULL),
(17, 'Bomba d''água',                'MOTOR',       50000, NULL),
(18, 'Bico injetor flex',            'INJECAO',     NULL,  NULL),
(19, 'Bico injetor diesel',          'INJECAO',     NULL,  NULL),
(20, 'Sonda lambda',                 'INJECAO',     80000, NULL),
(21, 'Amortecedor',                  'SUSPENSAO',   60000, NULL),
(22, 'Bieleta',                      'SUSPENSAO',   40000, NULL),
(23, 'Pivô de suspensão',            'SUSPENSAO',   60000, NULL),
(24, 'Alinhamento e balanceamento',  'SUSPENSAO',   10000, 12),
(25, 'Bateria',                      'ELETRICA',    NULL,  36),
(26, 'Lâmpada',                      'ELETRICA',    NULL,  NULL),
(27, 'Kit embreagem',                'TRANSMISSAO', NULL,  NULL),
(28, 'Mão de obra',                  'SERVICOS',    NULL,  NULL),
(29, 'Material de consumo/diversos', 'SERVICOS',    NULL,  NULL),
(30, 'Diagnóstico com scanner',      'SERVICOS',    NULL,  NULL);

INSERT INTO precos_referencia (id, id_categoria, descricao, valor_min, valor_max, fonte) VALUES
(1,  1,  'Óleo semissintético (litro)',       30.00,   45.00, 'MANUAL'),
(2,  2,  'Óleo sintético (litro)',            50.00,   80.00, 'MANUAL'),
(3,  6,  'Filtro de óleo (leve e diesel)',    25.00,   90.00, 'MANUAL'),
(4,  10, 'Pastilha de freio dianteira (jogo)',120.00, 200.00, 'MANUAL'),
(5,  13, 'Kit correia dentada + tensor',      350.00, 500.00, 'MANUAL'),
(6,  17, 'Bomba d''água',                     200.00, 320.00, 'MANUAL'),
(7,  19, 'Bico injetor diesel (unidade)',     900.00,1200.00, 'MANUAL'),
(8,  21, 'Amortecedor dianteiro (unidade)',   250.00, 400.00, 'MANUAL'),
(9,  25, 'Bateria 50-60Ah',                   420.00, 520.00, 'MANUAL'),
(10, 27, 'Kit embreagem (platô, disco, rolamento)', 750.00, 950.00, 'MANUAL'),
(11, 3,  'Fluido de freio DOT4 (frasco 500 ml)',          15.00,   70.00, 'MANUAL'), -- Radnaq R$ 15,90 LdM; Varga R$ 46,65 Magalu
(12, 4,  'Aditivo de radiador pronto para uso (litro)',   15.00,   60.00, 'MANUAL'), -- Paraflu R$ 16,90 LdM; Paraflu Bio R$ 39,21 Magalu
(13, 5,  'Óleo de câmbio (litro)',                        60.00,  210.00, 'MANUAL'), -- Lubrax ATF R$ 64,71 Magalu; Motul 75W90 R$ 137,90 Buscapé
(14, 7,  'Filtro de ar do motor (leve e diesel)',         10.00,  180.00, 'MANUAL'), -- Tecfil Gol R$ 13,11 Magalu; Frontier diesel R$ 116,00 Magalu
(15, 8,  'Filtro de combustível (leve e diesel)',         20.00,  240.00, 'MANUAL'), -- Tecfil GI04/7 R$ 23,75 Magalu; Wega Compass diesel R$ 154,71 Magalu
(16, 9,  'Filtro de cabine',                              10.00,   90.00, 'MANUAL'), -- Tecfil HB20 R$ 12,23 Magalu; Tecfil Hilux R$ 55,90 LdM
(17, 11, 'Disco de freio (unidade)',                     125.00,  530.00, 'MANUAL'), -- Fremax Onix R$ 125,90 Magalu; Fremax Corolla R$ 347,82 Magalu
(18, 12, 'Lonas ou sapatas traseiras (jogo)',             35.00,  230.00, 'MANUAL'), -- lona Gol R$ 38,25 Magalu; sapatas 207 R$ 150,00 ML
(19, 14, 'Correia auxiliar (unidade)',                    20.00,  220.00, 'MANUAL'), -- Gates Corsa R$ 24,27 Magalu; Gates Cruze R$ 140,41 ML
(20, 15, 'Vela de ignição (unidade)',                     10.00,  220.00, 'MANUAL'), -- NGK Celta R$ 13,78 Magalu; NGK irídio Corolla R$ 145,00 Magalu
(21, 16, 'Bobina de ignição (unidade)',                   90.00,  390.00, 'MANUAL'), -- Marelli Strada R$ 93,24 Magalu; NGK Corolla R$ 258,54 Magalu
(22, 18, 'Bico injetor flex (unidade)',                   50.00,  500.00, 'MANUAL'), -- Bosch Gol R$ 54,40 Magalu; Bosch Mobi R$ 329,00 Magalu
(23, 20, 'Sonda lambda (unidade)',                       105.00,  950.00, 'MANUAL'), -- NTK Strada R$ 107,89 Magalu; Bosch Toro R$ 629,00 Magalu
(24, 22, 'Bieleta (unidade)',                             35.00,  170.00, 'MANUAL'), -- Nakata Onix R$ 37,92 Magalu; Cofap Corolla R$ 107,86 Magalu
(25, 23, 'Pivô de suspensão (unidade)',                   40.00,  240.00, 'MANUAL'), -- Nakata Strada R$ 42,30 Magalu; Nakata Gol R$ 158,90 Magalu
(26, 26, 'Lâmpada halógena de farol (unidade)',           15.00,   70.00, 'MANUAL'); -- Philips H4 R$ 18,88 Magalu; Philips H4 Premium R$ 45,60 Magalu

SELECT setval(pg_get_serial_sequence('oficinas',          'id'), (SELECT MAX(id) FROM oficinas));

SELECT setval(pg_get_serial_sequence('categorias_item',   'id'), (SELECT MAX(id) FROM categorias_item));

SELECT setval(pg_get_serial_sequence('precos_referencia', 'id'), (SELECT MAX(id) FROM precos_referencia));

COMMIT;
