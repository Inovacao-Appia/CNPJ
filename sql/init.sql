CREATE TABLE IF NOT EXISTS logs_nf (
    id SERIAL PRIMARY KEY,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now(),
    arquivo TEXT,
    num_nota TEXT,
    data_emissao TEXT,
    prestador TEXT,
    valor_bruto TEXT,
    valor_liquido TEXT,
    status TEXT,
    erro TEXT
);

CREATE TABLE IF NOT EXISTS logs_contratos (
    id SERIAL PRIMARY KEY,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now(),
    categoria_contrato TEXT,
    tipo_documento TEXT,
    numero_contrato TEXT,
    numero_contrato_sap TEXT,
    numero_pedido_sap TEXT,
    razao_social_contratante TEXT,
    cnpj_contratante TEXT,
    razao_social_contratada TEXT,
    cnpj_contratada TEXT,
    objeto_contrato TEXT,
    data_assinatura TEXT,
    data_inicio_vigencia TEXT,
    data_final_vigencia TEXT,
    prazo_vigencia TEXT,
    valor_total TEXT,
    detalhes_valor TEXT,
    valores_extras TEXT,
    condicao_pagamento TEXT,
    havera_reajuste TEXT,
    indice_reajuste TEXT,
    garantia_financeira TEXT,
    retencao_caucao TEXT,
    periodo_medicao TEXT,
    local_servico TEXT,
    subcontratacao_faturamento_direto TEXT,
    gestor_contratante TEXT,
    gestor_contratada TEXT,
    arquivo_origem TEXT,
    arquivo TEXT,
    arquivos_origem TEXT,
    status TEXT,
    erro TEXT
);

CREATE TABLE IF NOT EXISTS usuarios (
    email TEXT PRIMARY KEY,
    nome TEXT,
    role TEXT NOT NULL DEFAULT 'usuario' CHECK (role IN ('admin', 'usuario')),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Bootstrap: sem isso, ninguém consegue entrar pra cadastrar os demais pela tela de administração.
INSERT INTO usuarios (email, nome, role) VALUES
    ('leonardo.silva@viaappia.com.br', 'Leonardo Silva', 'admin'),
    ('joao.guimaraes@viaappia.com.br', 'João Guimarães', 'admin')
ON CONFLICT (email) DO NOTHING;
