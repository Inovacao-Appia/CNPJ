import json
import os

import pdfplumber
import streamlit as st
from openai import OpenAI

from utils.config import cfg

# Cada prompt extrai um subconjunto de campos (pedir todos os campos de uma vez numa
# só chamada fazia o modelo confundir/misturar informações). Os prompts abaixo
# espelham os documentos "PROMPT 1", "PROMPT 2.1/2.2" e "PROMPT 3":
#   1   - Dados gerais (qualquer tipo de contrato)
#   2.1 - Vigências (Contrato de Obra e Ordem de Serviço — OS)
#   2.2 - Vigências (Contrato de Prestação de Serviço)
#   3   - Pagamentos: condição de pagamento, garantias/retenção e faturamento direto
# O prompt de vigências (2.1 ou 2.2) é escolhido conforme a CATEGORIA do lote
# informada pelo usuário na tela (todos os documentos de um mesmo lote são sempre
# da mesma categoria) — ver CATEGORIAS/CATEGORIA_SERVICO/CATEGORIA_OBRA_OS.
# CADA PDF É UM CONTRATO/ADITIVO INDEPENDENTE: os prompts rodam sobre o texto de
# UM ÚNICO arquivo por vez (nunca misturando o conteúdo de arquivos diferentes), e os
# resultados são combinados numa única linha, na ordem final de COLUMNS.
CATEGORIA_SERVICO = "servico"
CATEGORIA_OBRA_OS = "obra_os"
CATEGORIAS = {
    CATEGORIA_SERVICO: "Contrato de Prestação de Serviço",
    CATEGORIA_OBRA_OS: "Contrato de Obra e Ordem de Serviço (OS)",
}
# Coluna de metadado preenchida pela aplicação (não pela IA) com a categoria do
# lote selecionada na tela (Serviço ou Obra/OS) — ver CATEGORIAS.
COLUMNS_CATEGORIA = [
    ("categoria_contrato", "CATEGORIA DO CONTRATO (SERVIÇO OU OBRA/OS)"),
]

COLUMNS_1 = [
    ("tipo_documento", "TIPO DO DOCUMENTO (CONTRATO OU ADITIVO)"),
    ("numero_contrato", "NÚMERO DO CONTRATO"),
    ("numero_contrato_sap", "NÚMERO DO CONTRATO SAP (46)"),
    ("numero_pedido_sap", "NÚMERO DO PEDIDO DE COMPRA SAP (45)"),
    ("razao_social_contratante", "RAZÃO SOCIAL DA EMPRESA CONTRATANTE"),
    ("cnpj_contratante", "CNPJ DA EMPRESA CONTRATANTE"),
    ("razao_social_contratada", "RAZÃO SOCIAL DA EMPRESA CONTRATADA"),
    ("cnpj_contratada", "CNPJ DA EMPRESA CONTRATADA"),
    ("objeto_contrato", "OBJETO DO CONTRATO"),
    ("valor_total", "VALOR TOTAL DO CONTRATO - VALOR DA CONTRATAÇÃO"),
    ("detalhes_valor", "DETALHES DO VALOR DO CONTRATO"),
    ("valores_extras", "VALORES EXTRAS REEMBOLSÁVEIS"),
    ("havera_reajuste", "HAVERÁ REAJUSTE"),
    ("indice_reajuste", "ÍNDICE DE REAJUSTE"),
    ("local_servico", "LOCAL ONDE O SERVIÇO SERÁ REALIZADO"),
    ("gestor_contratante", "GESTOR DO CONTRATO POR PARTE DA CONTRATANTE (NOME E E-MAIL)"),
    ("gestor_contratada", "GESTOR DO CONTRATO POR PARTE DA CONTRATADA (NOME E E-MAIL)"),
    ("arquivo_origem", "ARQUIVO(S) DE ORIGEM"),
]

COLUMNS_2 = [
    ("tipo_documento", "TIPO DO DOCUMENTO (CONTRATO OU ADITIVO)"),
    ("numero_contrato", "NÚMERO DO CONTRATO"),
    ("data_assinatura", "DATA DA ASSINATURA DO DOCUMENTO"),
    ("data_inicio_vigencia", "DATA DE INÍCIO DA VIGÊNCIA"),
    ("data_final_vigencia", "DATA FINAL DA VIGÊNCIA"),
    ("prazo_vigencia", "PRAZO DE VIGÊNCIA"),
    ("periodo_medicao", "PERÍODO DE MEDIÇÃO MENSAL DO CONTRATO"),
    ("arquivo_origem", "ARQUIVO(S) DE ORIGEM"),
]

COLUMNS_3 = [
    ("tipo_documento", "TIPO DO DOCUMENTO (CONTRATO OU ADITIVO)"),
    ("numero_contrato", "NÚMERO DO CONTRATO"),
    ("condicao_pagamento", "CONDIÇÃO DE PAGAMENTO"),
    ("garantia_financeira", "GARANTIA FINANCEIRA / FIANÇA"),
    ("retencao_caucao", "RETENÇÃO CONTRATUAL / CAUÇÃO"),
    ("subcontratacao_faturamento_direto", "AUTORIZADA SUBCONTRATAÇÃO / FATURAMENTO DIRETO"),
    ("arquivo_origem", "ARQUIVO(S) DE ORIGEM"),
]

# Ordem final da planilha (rótulos vêm de COLUMNS_CATEGORIA/1/2/3 — fonte única de verdade).
_ORDEM_FINAL = [
    "categoria_contrato",
    "tipo_documento",
    "numero_contrato",
    "numero_contrato_sap",
    "numero_pedido_sap",
    "razao_social_contratante",
    "cnpj_contratante",
    "razao_social_contratada",
    "cnpj_contratada",
    "objeto_contrato",
    "data_assinatura",
    "data_inicio_vigencia",
    "data_final_vigencia",
    "prazo_vigencia",
    "valor_total",
    "detalhes_valor",
    "valores_extras",
    "condicao_pagamento",
    "havera_reajuste",
    "indice_reajuste",
    "garantia_financeira",
    "retencao_caucao",
    "periodo_medicao",
    "local_servico",
    "subcontratacao_faturamento_direto",
    "gestor_contratante",
    "gestor_contratada",
    "arquivo_origem",
]
_rotulos_por_chave = dict(COLUMNS_CATEGORIA + COLUMNS_1 + COLUMNS_2 + COLUMNS_3)
COLUMNS = [(chave, _rotulos_por_chave[chave]) for chave in _ORDEM_FINAL]
del _rotulos_por_chave

NAO_LOCALIZADO = "NÃO LOCALIZADO"

_JSON_KEYS_1 = ", ".join(f'"{chave}"' for chave, _ in COLUMNS_1)
_JSON_KEYS_2 = ", ".join(f'"{chave}"' for chave, _ in COLUMNS_2)
_JSON_KEYS_3 = ", ".join(f'"{chave}"' for chave, _ in COLUMNS_3)

_CONTEXTO_E_REGRAS_GERAIS = f"""CONTEXTO DO PROCESSAMENTO
- Cada execução deste prompt processa UM ÚNICO documento de cada vez (um PDF = um contrato ou aditivo).
- Todo documento fornecido será, exclusivamente, um CONTRATO ou um ADITIVO DE CONTRATO.
- Um ADITIVO deve ser tratado como uma linha totalmente separada e independente, com seus próprios campos extraídos exclusivamente a partir do conteúdo do próprio aditivo.
- NUNCA utilize, copie, combine ou infira informações provenientes de outros documentos anexados ao mesmo processamento (como contrato principal, outros aditivos, ordens de serviço, anexos ou documentos correlatos). Extraia exclusivamente as informações contidas no documento que está sendo analisado nesta execução, desconsiderando integralmente qualquer conteúdo de outros arquivos anexos.

IDENTIFICAÇÃO DO TIPO DE DOCUMENTO
- Identifique se o documento é um CONTRATO ou um ADITIVO e preencha o campo "tipo_documento" com "CONTRATO" ou "ADITIVO".
- Se for um ADITIVO, o campo "numero_contrato" deve conter o número do contrato principal seguido da identificação do aditivo, no formato "NÚMERO DO CONTRATO – ADITIVO Nº XX" (ex.: "ENG 778/2023 – ADITIVO Nº 01"). Se o aditivo não tiver número, use "ADITIVO" sem numeração.
- Se for um CONTRATO, o campo "numero_contrato" deve conter apenas o número do contrato.

REGRAS GERAIS
1. Analise integralmente o documento enviado para esta execução.
2. Considere, além do contrato/aditivo principal, os anexos, DocuSign e demais páginas que compõem ESTE mesmo arquivo PDF.
3. Para cada informação extraída, inclua no próprio texto do campo a origem do dado: cláusula (número e título, quando houver), anexo (quando aplicável) e a página do documento onde a informação foi localizada. As páginas estão marcadas no texto recebido com "=== {{NOME DO DOCUMENTO}} — PÁGINA {{N}} ==="; use esse nome de documento e número de página nas citações.
4. Quando uma informação estiver distribuída em mais de uma cláusula ou página, cite todas as referências utilizadas.
5. Não faça suposições nem preencha informações por dedução. Extraia apenas dados expressamente previstos no documento, ou realize cálculos apenas quando houver regra específica para isso.
6. Caso uma informação não exista ou não seja localizada, preencha o campo com "{NAO_LOCALIZADO}".
7. Mantenha a redação objetiva, preservando o significado da cláusula contratual.
8. TODO o texto de todos os campos deve estar em CAIXA ALTA (maiúsculas), incluindo e-mails."""

# ---------------------------------------------------------------------------
# PROMPT 1 — Dados gerais (qualquer tipo de contrato)
# ---------------------------------------------------------------------------
PROMPT_DADOS_GERAIS = f"""Você atuará como um analista de contratos especializado na extração de informações contratuais.

{_CONTEXTO_E_REGRAS_GERAIS}

Sua função é analisar o documento fornecido para identificar, interpretar e extrair apenas as informações relacionadas aos campos listados abaixo.

REGRAS ESPECÍFICAS POR CAMPO
MANTER A ORDEM DAS COLUNAS, CONFORME CAMPOS INDICADOS ABAIXO.

Observação: para os campos abaixo, NUNCA analisar documento que contém o nome "ORDEM DE SERVIÇO" ou "OS".

- Tipo do documento: informe "CONTRATO" ou "ADITIVO", conforme identificado.
- Número do contrato: se CONTRATO, informe o número do contrato. Se ADITIVO, informe "NÚMERO DO CONTRATO – ADITIVO Nº XX" (ou "– ADITIVO" se não houver numeração), citando cláusula/página onde a identificação foi localizada. Se o número do contrato contiver a sigla "PMR", mantenha-a exatamente como consta no documento e transcreva o número completo para a planilha, sem alterações. Exemplo: "OPR-COL-074.2025/PMR".
- Número do contrato SAP (46): informar o número de contrato SAP. Observação: número do contrato SAP inicia-se com 46, exemplo: 4600002220; alguns contratos podem não conter essa numeração, caso não encontrado preencher com "{NAO_LOCALIZADO}". Não registrar nesse campo quando iniciar com 45 (é o número do pedido de compra).
- Número do pedido de compra SAP (45): informar o número de pedido de compra SAP. Observação: número do pedido de compra SAP inicia-se com 45, exemplo: 4500052042; alguns contratos podem não conter essa numeração, caso não encontrado preencher com "{NAO_LOCALIZADO}". Não registrar nesse campo quando iniciar com 46 (é o número do contrato SAP).
- Razão Social da empresa Contratante.
- CNPJ da empresa Contratante.
- Razão Social da empresa Contratada.
- CNPJ da empresa Contratada.
- Objeto do contrato: identifique a cláusula que descreve o objeto contratual. Informe de forma fiel ao documento, resumindo apenas quando o texto for muito extenso, sem alterar o sentido. No caso de aditivo, descreva o objeto do aditivo (ex.: alteração de valor, prorrogação de vigência, inclusão de cláusula, etc.).
- Valor total do contrato - valor da contratação: informe o valor total, citando cláusula/página. Em aditivos que alteram valor, informe o novo valor total (e indique que se trata de saldo decorrente de aditivo quando aplicável).
- Detalhes do valor do contrato: informe valor total, valor mensal, valor unitário por serviço, adiantamentos e demais valores previstos. Em aditivos que alteram valor, informe o novo valor total e indique que se trata de saldo decorrente de aditivo quando aplicável.
- Valores extras reembolsáveis: informe valores adicionais previstos (reembolso de hospedagem, alimentação, viagens, diárias, deslocamentos e demais despesas reembolsáveis). Caso não exista previsão, informe "Não previstos".
- Haverá reajuste: informe "SIM" ou "NÃO", citando cláusula/página.
- Índice de reajuste: quando houver previsão de reajuste, informe o índice, a periodicidade e a cláusula/página. Quando não houver, repita a regra 5.
- Local onde o serviço será realizado: informe exatamente o local indicado no documento, sem interpretações.
- Gestor do contrato por parte da Contratante (nome e e-mail): identifique o profissional indicado pela CONTRATANTE como gestor do contrato, com respectivo e-mail. Quando houver mais de um, cite todos.
- Gestor do contrato por parte da Contratada (nome e e-mail): identifique o profissional indicado pela CONTRATADA como gestor/responsável técnico, com respectivo e-mail. Quando houver mais de um, cite todos.
- Arquivo(s) de origem: informe o nome do arquivo analisado.

IMPORTANTE
- Se o documento for um aditivo que trata APENAS de prorrogação de vigência, datas e demais campos podem permanecer com o mesmo conteúdo; ainda assim, extraia APENAS do próprio aditivo (transcreva o que o aditivo reproduzir/referenciar). Se o aditivo não reproduzir/especificar o campo, preencha com "{NAO_LOCALIZADO}" (não copie do contrato principal).

Responda EXCLUSIVAMENTE com um objeto JSON contendo exatamente estas chaves: {_JSON_KEYS_1}.
"""

# ---------------------------------------------------------------------------
# PROMPT 2.2 — Vigências (Contrato de Prestação de Serviço)
# ---------------------------------------------------------------------------
PROMPT_VIGENCIAS_SERVICO = f"""Você atuará como um analista de contratos especializado na extração de informações contratuais.

{_CONTEXTO_E_REGRAS_GERAIS}

Sua função é analisar o documento fornecido para identificar, interpretar e extrair apenas as informações relacionadas aos campos listados abaixo.

REGRAS ESPECÍFICAS POR CAMPO
MANTER A ORDEM DAS COLUNAS, NA ORDEM DOS CAMPOS LISTADOS ABAIXO.

- Tipo do documento: informe "CONTRATO" ou "ADITIVO", conforme identificado.
- Número do contrato: se CONTRATO, informe o número do contrato. Se ADITIVO, informe "NÚMERO DO CONTRATO – ADITIVO Nº XX" (ou "– ADITIVO" se não houver numeração), citando cláusula/página onde a identificação foi localizada. Se o número do contrato contiver a sigla "PMR", mantenha-a exatamente como consta no documento e transcreva o número completo para a planilha, sem alterações. Exemplo: "OPR-COL-074.2025/PMR".
- Data da assinatura do documento: analise integralmente o documento e identifique a data de assinatura do documento. Regras: 1. Procure a data junto às assinaturas das partes, no encerramento do contrato, NUNCA traga a data de assinatura digital do Docusign. 2. Não confunda a data de assinatura com: data de início ou vigência; data de emissão; data de elaboração; data de aprovação; data de reconhecimento de firma; datas mencionadas em cláusulas. Analisar apenas o documento que contém o nome "CONTRATO" ou "ADITIVO" para esse campo. NUNCA analisar o documento que contém o nome "ORDEM DE SERVIÇO" ou "OS" para esse campo.
- Data de início da vigência: identificar e extrair a data de início da vigência do contrato. Localize no contrato a data que indique explicitamente o início da vigência, utilizando expressões como "início da vigência", "vigência inicia em", "vigência terá início em", "o contrato entra em vigor em", "a partir de", "início de vigência" ou outras expressões equivalentes. Caso exista uma data de início da vigência expressamente informada, extraia essa data. Caso o contrato não informe explicitamente a data de início da vigência, mas estabeleça que a vigência se inicia na data de assinatura do contrato (ou utilize expressões equivalentes, como "na data de sua assinatura", "a partir da assinatura", "contados da assinatura"), utilize a data existente no campo "Data da assinatura do documento" como valor para este campo. Caso não seja possível identificar a data de início da vigência nem haja indicação de que ela corresponde à data de assinatura, informar "{NAO_LOCALIZADO}". NUNCA analisar o documento que contém o nome "ADITIVO" para esse campo.
- Data final da vigência: identifique o prazo de vigência previsto (ex.: 12 meses, 365 dias, 24 meses). Se a vigência terminar após esse prazo contado da data de assinatura do contrato, calcule a data final somando o prazo à data de assinatura do contrato. Caso o documento informe uma data final específica, utilize-a diretamente. Em aditivos de prorrogação, calcule a nova data final conforme o novo prazo estabelecido pelo aditivo. No documento que contém o nome "ADITIVO", se tratar apenas de prorrogação do prazo, trazer apenas a data final informada no aditivo.
- Prazo de vigência: informe o prazo previsto (dias, meses ou anos), citando cláusula, anexo e página. Em aditivos que alteram prazos, informe o novo prazo estabelecido pelo aditivo. Em aditivos de prorrogação, calcule a nova data final conforme o novo prazo estabelecido pelo aditivo.
- Período de medição mensal do contrato: informe a data inicial/final do período, periodicidade, data limite para apresentação da medição e cláusula/página. Caso não haja previsão, informe "Período de medição não previsto."
- Arquivo(s) de origem: informe o nome do arquivo analisado.

Responda EXCLUSIVAMENTE com um objeto JSON contendo exatamente estas chaves: {_JSON_KEYS_2}.
"""

# ---------------------------------------------------------------------------
# PROMPT 2.1 — Vigências (Contrato de Obra e Ordem de Serviço — OS)
# ---------------------------------------------------------------------------
PROMPT_VIGENCIAS_OBRA_OS = f"""Você atuará como um analista de contratos especializado na extração de informações contratuais.

CONTEXTO DO PROCESSAMENTO
- Cada execução deste prompt processa UM ÚNICO documento de cada vez.
- Todo documento fornecido será, exclusivamente, um CONTRATO, um ADITIVO DE CONTRATO ou uma ORDEM DE SERVIÇO (OS).
- Um ADITIVO deve ser tratado como uma linha totalmente separada e independente, com seus próprios campos extraídos exclusivamente a partir do conteúdo do próprio aditivo.
- NUNCA utilize, copie, combine ou infira informações provenientes de outros documentos anexados ao mesmo processamento (como contrato principal, outros aditivos, ordens de serviço, anexos ou documentos correlatos). Extraia exclusivamente as informações contidas no documento que está sendo analisado nesta execução, desconsiderando integralmente qualquer conteúdo de outros arquivos anexos.

IDENTIFICAÇÃO DO TIPO DE DOCUMENTO
- Identifique se o documento é um CONTRATO ou um ADITIVO e preencha o campo "tipo_documento" com "CONTRATO" ou "ADITIVO".
- Se for um ADITIVO, o campo "numero_contrato" deve conter o número do contrato principal seguido da identificação do aditivo, no formato "NÚMERO DO CONTRATO – ADITIVO Nº XX" (ex.: "ENG 778/2023 – ADITIVO Nº 01"). Se o aditivo não tiver número, use "ADITIVO" sem numeração.
- Se for um CONTRATO, o campo "numero_contrato" deve conter apenas o número do contrato.

REGRAS GERAIS
1. Analise integralmente o documento enviado para esta execução.
2. Considere, além do contrato/aditivo principal, exclusivamente os anexos, DocuSign e demais arquivos que compõem ESTE documento (não de outros documentos processados em separado).
3. Para cada informação extraída, inclua no próprio texto do campo a origem do dado: cláusula (número e título, quando houver), anexo (quando aplicável) e a página do documento onde a informação foi localizada. Os documentos estão marcados no texto recebido com "=== {{NOME DO DOCUMENTO}} — PÁGINA {{N}} ==="; use esse nome de documento e número de página nas citações.
4. Quando uma informação estiver distribuída em mais de uma cláusula ou documento (do presente documento), cite todas as referências utilizadas.
5. Não faça suposições nem preencha informações por dedução. Extraia apenas dados expressamente previstos no documento, ou realize cálculos apenas quando houver regra específica para isso.
6. Caso uma informação não exista ou não seja localizada, preencha o campo com "{NAO_LOCALIZADO}".
7. Mantenha a redação objetiva, preservando o significado da cláusula contratual.
8. TODO o texto de todos os campos deve estar em CAIXA ALTA (maiúsculas), incluindo e-mails.

Sua função é analisar o documento fornecido para identificar, interpretar e extrair apenas as informações relacionadas aos campos listados abaixo.

REGRAS ESPECÍFICAS POR CAMPO
MANTER A ORDEM DAS COLUNAS, NA ORDEM DOS CAMPOS LISTADOS ABAIXO.

- Tipo do documento: informe "CONTRATO" ou "ADITIVO", conforme identificado.
- Número do contrato: se CONTRATO, informe o número do contrato. Se ADITIVO, informe "NÚMERO DO CONTRATO – ADITIVO Nº XX" (ou "– ADITIVO" se não houver numeração), citando cláusula/página onde a identificação foi localizada. Se o número do contrato contiver a sigla "PMR", mantenha-a exatamente como consta no documento e transcreva o número completo para a planilha, sem alterações. Exemplo: "OPR-COL-074.2025/PMR".
- Data da assinatura do documento: analise integralmente o documento e identifique a data de assinatura do documento. Regras: 1. Procure a data junto às assinaturas das partes, no encerramento do contrato, NUNCA traga a data de assinatura digital do Docusign. 2. Não confunda a data de assinatura com: data de início ou vigência; data de emissão; data de elaboração; data de aprovação; data de reconhecimento de firma; datas mencionadas em cláusulas. Analisar apenas o documento que contém o nome "CONTRATO" ou "ADITIVO" para esse campo. NUNCA analisar o documento que contém o nome "ORDEM DE SERVIÇO" ou "OS" para esse campo.
- Data de início da vigência: analise integralmente o documento e identifique a data de início da vigência. Extrair dados conforme regras de busca: 1. Se a data de início estiver explícita (exemplo: "vigência a partir de 01/01/2026"), extrair a data informada; 2. Se a data de início for conforme a assinatura do documento (exemplo: "vigência a partir da data de assinatura do contrato"), extrair a data de assinatura do documento — NUNCA buscar a data da assinatura eletrônica (Docusign) quando buscar do documento que contém no nome "Contrato"; 3. Se a data de início for a data de assinatura da "Ordem de Serviço (OS)" (exemplo: "vigência a partir da data de assinatura da Ordem de Serviço"), extrair a data de assinatura da Ordem de Serviço (OS) — primeira busca: a data de assinatura do documento; caso não encontrado, segunda busca: a data de conclusão da assinatura eletrônica da Ordem de Serviço. NUNCA analisar o documento que contém o nome "ADITIVO" para esse campo.
- Data final da vigência: identifique o prazo de vigência previsto (ex.: 12 meses, 365 dias, 24 meses). Se a vigência terminar após esse prazo contado da data de assinatura da OS, calcule a data final somando o prazo à data de assinatura da OS. Caso o documento informe uma data final específica, utilize-a diretamente. No documento que contém o nome "ADITIVO", se tratar apenas de prorrogação do prazo, trazer apenas a data final informada no aditivo.
- Prazo de vigência: informe o prazo previsto (dias, meses ou anos), citando cláusula, anexo e página. Em aditivos que alteram prazos, informe o novo prazo estabelecido pelo aditivo. Em aditivos de prorrogação, calcule a nova data final conforme o novo prazo estabelecido pelo aditivo.
- Período de medição mensal do contrato: informe a data inicial/final do período, periodicidade, data limite para apresentação da medição e cláusula/página. Caso não haja previsão, informe "Período de medição não previsto." Analisar apenas o documento que contém o nome "CONTRATO" ou "ADITIVO" para esse campo. NUNCA analisar o documento que contém o nome "ORDEM DE SERVIÇO" ou "OS" para esse campo.
- Arquivo(s) de origem: informe o nome do arquivo analisado.

Responda EXCLUSIVAMENTE com um objeto JSON contendo exatamente estas chaves: {_JSON_KEYS_2}.
"""

# ---------------------------------------------------------------------------
# PROMPT 3 — Pagamentos: condição de pagamento, garantias/retenção e
# faturamento direto (todos os contratos)
# ---------------------------------------------------------------------------
PROMPT_PAGAMENTOS = f"""Você atuará como um analista de contratos especializado na extração de informações contratuais.

{_CONTEXTO_E_REGRAS_GERAIS}

Sua função é analisar o documento fornecido para identificar, interpretar e extrair apenas as informações relacionadas aos campos listados abaixo.

REGRAS ESPECÍFICAS POR CAMPO
MANTER A ORDEM DAS COLUNAS, NA ORDEM DOS CAMPOS LISTADOS ABAIXO.

Observação: para os campos abaixo, NUNCA analisar documento que contém o nome "ORDEM DE SERVIÇO" ou "OS".

- Tipo do documento: informe "CONTRATO" ou "ADITIVO", conforme identificado.
- Número do contrato: se CONTRATO, informe o número do contrato. Se ADITIVO, informe "NÚMERO DO CONTRATO – ADITIVO Nº XX" (ou "– ADITIVO" se não houver numeração), citando cláusula/página onde a identificação foi localizada. Se o número do contrato contiver a sigla "PMR", mantenha-a exatamente como consta no documento e transcreva o número completo para a planilha, sem alterações. Exemplo: "OPR-COL-074.2025/PMR".
- Condição de pagamento: analise o PDF do contrato. Identifique todas as condições de pagamento previstas no contrato: se existe pagamento antecipado e o respectivo percentual ou valor; se o pagamento é realizado em parcela única ou em parcelas; se houver pagamento por etapas, marcos ou entregas do serviço, descreva cada etapa e o respectivo percentual ou valor a ser pago; se houver prazo para pagamento (ex.: 30 dias após emissão da nota fiscal, 15 dias após aceite da entrega etc.), informe o prazo. Caso não exista pagamento antecipado ou parcelamento por etapas, informe a condição de pagamento exatamente como descrita no contrato. Regras obrigatórias: NUNCA utilize, consulte, copie ou extraia informações da proposta comercial, orçamento, ordem de serviço ou de qualquer outro documento anexo ao processamento, ainda que tais documentos contenham condições de pagamento; considere apenas as informações expressamente previstas no contrato objeto da análise; caso o contrato faça apenas referência à proposta comercial, sem reproduzir a condição de pagamento em seu próprio texto, informe: "Condição de pagamento não identificada no contrato."
- Garantia Financeira/ Fiança: informe se há exigência de instrumento de garantia complementar (fiança bancária, seguro-garantia, apólice, nota promissória, garantia de adiantamento, garantia de performance, garantia em dinheiro ou outra modalidade). Preencha de forma objetiva, no padrão: (i) existência: "SIM", "NÃO" ou "NÃO APLICÁVEL"; (ii) modalidade(s) aceita(s); (iii) percentual e/ou valor da cobertura sobre o valor do contrato; (iv) momento de apresentação (ex.: na assinatura do contrato); (v) prazo de vigência e/ou restituição; (vi) cláusula/anexo/página de origem. A expressão "retenção" não determina sozinha esta coluna: prevalece o CONTEXTO ESTRUTURAL da cláusula.
- Retenção Contratual/ Caução: informe se há retenção mensal sobre as medições ou caução. Preencha de forma objetiva, no padrão: (i) existência: "SIM" ou "NÃO"; (ii) percentual da retenção sobre o valor bruto de cada medição e/ou valor fixo (ex.: R$ 5.000,00 ou 1%, prevalecendo o maior); (iii) base de cálculo (valor da medição, cada medição, última medição, etc.); (iv) prazo e condição de devolução (ex.: 180 dias após a medição final; 12 meses após o Termo de Recebimento Definitivo; sem correção monetária); (v) se a retenção pode ou não ser substituída por fiança bancária ou outra modalidade; (vi) cláusula/anexo/página de origem.
- Autorizada subcontratação / Faturamento direto: analise o documento em busca de cláusulas relacionadas à subcontratação, terceirização, cessão de atividades, faturamento direto ou pagamento direto a terceiros. Identifique se a subcontratação é: permitida sem restrições; permitida mediante autorização prévia da CONTRATANTE; permitida parcialmente (apenas para determinadas atividades); ou proibida. Identifique se existe previsão de faturamento direto, pagamento direto a subcontratados ou qualquer outra forma de faturamento por terceiros. Resuma as condições previstas, informando se a subcontratação é autorizada e em quais condições, e se há previsão de faturamento direto e quais são os requisitos para sua realização.
- Arquivo(s) de origem: informe o nome do arquivo analisado.

Responda EXCLUSIVAMENTE com um objeto JSON contendo exatamente estas chaves: {_JSON_KEYS_3}.
"""


def _get_client():
    api_key = cfg("OPENAI_API_KEY")
    if not api_key:
        st.error("Chave OPENAI_API_KEY não configurada. Adicione em Settings → Secrets no Streamlit Cloud.")
        st.stop()
    return OpenAI(api_key=api_key)


def extrair_texto_documentos(arquivos: list[tuple[str, str]]) -> str:
    """Recebe lista de (rótulo_do_documento, caminho_pdf) e retorna o texto combinado,
    com marcadores de documento e página para permitir citação correta da origem."""
    partes = []
    for rotulo, caminho in arquivos:
        with pdfplumber.open(caminho) as pdf:
            for i, pagina in enumerate(pdf.pages, start=1):
                texto = pagina.extract_text()
                if texto:
                    partes.append(f"=== {rotulo.upper()} — PÁGINA {i} ===\n{texto}")
    return "\n\n".join(partes)


def _extrair_campos(client, prompt: str, texto: str, colunas: list[tuple[str, str]]) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Texto extraído do documento:\n{texto}"},
        ],
    )
    dados = json.loads(response.choices[0].message.content)

    resultado = {}
    for chave, _ in colunas:
        valor = dados.get(chave)
        resultado[chave] = str(valor).upper() if valor not in (None, "") else NAO_LOCALIZADO
    return resultado


def analisar_documento(rotulo: str, caminho: str, categoria: str = CATEGORIA_SERVICO, on_progress=None) -> dict:
    """Roda os 3 prompts sobre UM ÚNICO arquivo PDF (um PDF = um contrato/aditivo,
    processado isoladamente, sem misturar com o conteúdo de outros arquivos) e
    combina os resultados numa única linha, na ordem de COLUMNS.

    categoria define qual prompt de vigências é usado: CATEGORIA_SERVICO (prompt
    2.2, contrato de prestação de serviço) ou CATEGORIA_OBRA_OS (prompt 2.1,
    contrato de obra e ordem de serviço). Um mesmo lote é sempre de uma única
    categoria.

    on_progress, se informado, é chamado com uma mensagem de texto a cada etapa
    (leitura do PDF, cada prompt, consolidação), para permitir exibir o andamento
    na interface enquanto o processamento ocorre."""
    def _emit(mensagem: str):
        if on_progress:
            on_progress(mensagem)

    if categoria not in CATEGORIAS:
        raise ValueError(f"Categoria inválida: {categoria!r}. Use uma de {list(CATEGORIAS)}.")

    client = _get_client()

    _emit("📄 Lendo o documento...")
    texto = extrair_texto_documentos([(rotulo, caminho)])

    _emit("🔎 Rodando prompt 1/3 — dados gerais...")
    dados_gerais = _extrair_campos(client, PROMPT_DADOS_GERAIS, texto, COLUMNS_1)

    prompt_vigencias = PROMPT_VIGENCIAS_OBRA_OS if categoria == CATEGORIA_OBRA_OS else PROMPT_VIGENCIAS_SERVICO
    _emit("🔎 Rodando prompt 2/3 — vigências...")
    dados_vigencias = _extrair_campos(client, prompt_vigencias, texto, COLUMNS_2)

    _emit("🔎 Rodando prompt 3/3 — pagamentos...")
    dados_pagamentos = _extrair_campos(client, PROMPT_PAGAMENTOS, texto, COLUMNS_3)

    _emit("🧩 Consolidando resultados...")
    combinado = {**dados_vigencias, **dados_pagamentos, **dados_gerais}
    combinado["categoria_contrato"] = CATEGORIAS[categoria].upper()
    return {chave: combinado.get(chave, NAO_LOCALIZADO) for chave, _ in COLUMNS}


def listar_pdfs_zip(tmpdir: str) -> list[tuple[str, str]]:
    """Varre recursivamente o diretório extraído do ZIP e retorna a lista de
    (rótulo, caminho) — um item por PDF encontrado, em qualquer profundidade de
    pastas. Cada PDF é um contrato independente, processado isoladamente."""
    documentos = []
    for root, _dirs, files in os.walk(tmpdir):
        for file in sorted(files):
            if file.lower().endswith(".pdf"):
                rotulo = os.path.splitext(file)[0]
                documentos.append((rotulo, os.path.join(root, file)))
    return sorted(documentos, key=lambda item: item[1])
