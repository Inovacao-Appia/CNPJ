import json
import os

import pandas as pd
import pdfplumber
import streamlit as st
from openai import OpenAI
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# Fonte única de verdade: (chave_json, rótulo da coluna) na ordem exigida pelo prompt.
COLUMNS = [
    ("numero_contrato", "NÚMERO DO CONTRATO"),
    ("numero_pedido_sap", "NÚMERO DO PEDIDO DE COMPRA SAP"),
    ("razao_social_contratante", "RAZÃO SOCIAL DA EMPRESA CONTRATANTE"),
    ("cnpj_contratante", "CNPJ DA EMPRESA CONTRATANTE"),
    ("razao_social_contratada", "RAZÃO SOCIAL / NOME FANTASIA DA CONTRATADA"),
    ("cnpj_contratada", "CNPJ DA EMPRESA CONTRATADA"),
    ("objeto_contrato", "OBJETO DO CONTRATO"),
    ("data_assinatura", "DATA DA ASSINATURA DO CONTRATO"),
    ("data_inicio_vigencia", "DATA DE INÍCIO DA VIGÊNCIA"),
    ("data_final_vigencia", "DATA FINAL DA VIGÊNCIA"),
    ("prazo_vigencia", "PRAZO DE VIGÊNCIA"),
    ("valor_total", "VALOR TOTAL DO CONTRATO"),
    ("detalhes_valor", "DETALHES DO VALOR DO CONTRATO"),
    ("valores_extras", "VALORES EXTRAS"),
    ("condicao_pagamento", "CONDIÇÃO DE PAGAMENTO"),
    ("havera_reajuste", "HAVERÁ REAJUSTE (SIM/NÃO)"),
    ("indice_reajuste", "ÍNDICE DE REAJUSTE"),
    ("garantia_retencao", "GARANTIA OU RETENÇÃO CONTRATUAL"),
    ("periodo_medicao", "PERÍODO DE MEDIÇÃO MENSAL DO CONTRATO"),
    ("local_servico", "LOCAL ONDE O SERVIÇO SERÁ REALIZADO"),
    ("especificacoes_faturamento", "ESPECIFICAÇÕES PARA FATURAMENTO"),
    ("subcontratacao_faturamento_direto", "AUTORIZADA SUBCONTRATAÇÃO / FATURAMENTO DIRETO"),
    ("enquadramento_reidi", "ENQUADRAMENTO REIDI"),
    ("gestor_contratante_nome", "GESTOR DO CONTRATO POR PARTE DA CONTRATANTE - NOME"),
    ("gestor_contratante_email", "GESTOR DO CONTRATO POR PARTE DA CONTRATANTE - E-MAIL"),
    ("gestor_contratada_nome", "GESTOR DO CONTRATO POR PARTE DA CONTRATADA - NOME"),
    ("gestor_contratada_email", "GESTOR DO CONTRATO POR PARTE DA CONTRATADA - E-MAIL"),
]

NAO_LOCALIZADO = "NÃO LOCALIZADO"

_JSON_KEYS = ", ".join(f'"{chave}"' for chave, _ in COLUMNS)

PROMPT_CONTRATO = f"""Você atuará como um analista de contratos especializado na extração de informações contratuais.

Sua função é analisar todos os documentos fornecidos para um contrato (contrato principal, Ordem de Serviço, anexos, aditivos, DocuSign e demais arquivos relacionados) para identificar, interpretar e extrair as informações solicitadas.

REGRAS GERAIS
1. Analise integralmente todos os documentos enviados.
2. Considere, além do contrato principal, anexos, aditivos, Ordem de Serviço (OS), documentos do DocuSign e demais arquivos relacionados.
3. Quando houver divergência entre documentos, aplique as regras específicas de cada campo abaixo.
4. Para cada informação extraída, inclua no próprio texto do campo a origem do dado: cláusula (número e título, quando houver), anexo (quando aplicável) e a página do documento onde a informação foi localizada. Os documentos estão marcados no texto recebido com "=== {{NOME DO DOCUMENTO}} — PÁGINA {{N}} ==="; use esse nome de documento e número de página nas citações.
5. Quando uma informação estiver distribuída em mais de uma cláusula ou documento, cite todas as referências utilizadas.
6. Não faça suposições nem preencha informações por dedução. Extraia apenas dados expressamente previstos nos documentos, ou realize cálculos apenas quando houver regra específica para isso (ex.: cálculo da data final de vigência a partir do prazo + data de assinatura da OS).
7. Caso uma informação não exista ou não seja localizada, preencha o campo com "{NAO_LOCALIZADO}".
8. Mantenha a redação objetiva, preservando o significado da cláusula contratual.
9. TODO o texto de todos os campos deve estar em CAIXA ALTA (maiúsculas), incluindo e-mails.

REGRAS ESPECÍFICAS POR CAMPO
- Objeto do contrato: identifique a cláusula que descreve o objeto contratual. Informe de forma fiel ao contrato, resumindo apenas quando o texto for muito extenso, sem alterar o sentido.
- Data da assinatura do contrato: se houver informações de DocuSign, use a Data de Conclusão (Completed Date) do CONTRATO. Caso não exista DocuSign, localize a página do contrato com as assinaturas e use a data ali constante.
- Data de início da vigência: se o contrato estabelecer que a vigência se inicia na data de assinatura da Ordem de Serviço, localize a data de assinatura no documento da OS (Completed Date do DocuSign da OS, ou a data da página de assinaturas da OS caso não haja DocuSign) e utilize-a. Caso o contrato informe uma data de início específica, utilize a data expressamente indicada no contrato.
- Data final da vigência: identifique o prazo de vigência previsto no contrato (ex.: 12 meses, 365 dias, 24 meses). Se a vigência terminar após esse prazo contado da data de assinatura da OS, calcule a data final somando o prazo à data de assinatura da OS. Caso o contrato informe uma data final específica, utilize-a diretamente.
- Prazo de vigência: informe o prazo previsto no contrato (dias, meses ou anos), citando cláusula, anexo e página.
- Detalhes do valor do contrato: informe valor total, valor mensal, valor unitário por serviço, adiantamentos e demais valores previstos.
- Valores extras: informe valores adicionais previstos (reembolso de hospedagem, alimentação, viagens, diárias, deslocamentos, outras despesas reembolsáveis).
- Condição de pagamento: informe se há pagamento antecipado (percentual/valor), parcela única ou parcelada, pagamento por etapas/marcos/entregas (com percentual/valor de cada etapa) e prazo para pagamento. Caso não exista antecipação/parcelamento por etapas, informe a condição exatamente como descrita no contrato.
- Índice de reajuste: quando houver previsão de reajuste, informe o índice, a periodicidade e a cláusula/página.
- Garantia ou retenção contratual: informe o tipo (retenção, caução, seguro-garantia, fiança bancária ou outro), o percentual/valor e as condições de liberação, quando previstas. Caso não exista, informe "Não possui garantia ou retenção contratual".
- Período de medição mensal do contrato: informe a data inicial/final do período, periodicidade, data limite para apresentação da medição e cláusula/página. Caso não haja previsão, informe "Período de medição não previsto no contrato."
- Local onde o serviço será realizado: informe exatamente o local indicado no contrato, sem interpretações.
- Especificações para faturamento: resuma as exigências prévias ao faturamento (aprovação/aceite do serviço, assinatura de boletim de medição, entrega de certidões/documentos, autorização formal para emissão da NF etc.).
- Autorizada subcontratação / Faturamento direto: identifique se a subcontratação é permitida sem restrições, mediante autorização prévia, parcialmente ou proibida; e se há previsão de faturamento direto/pagamento direto a terceiros e seus requisitos.

Responda EXCLUSIVAMENTE com um objeto JSON contendo exatamente estas chaves: {_JSON_KEYS}."""


def _get_client():
    api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
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


def analisar_contrato(texto: str) -> dict:
    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {"role": "system", "content": PROMPT_CONTRATO},
            {"role": "user", "content": f"Texto extraído dos documentos do contrato:\n{texto}"},
        ],
    )
    dados = json.loads(response.choices[0].message.content)

    resultado = {}
    for chave, _ in COLUMNS:
        valor = dados.get(chave)
        resultado[chave] = str(valor).upper() if valor not in (None, "") else NAO_LOCALIZADO
    return resultado


def agrupar_arquivos_zip(tmpdir: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """Varre o diretório extraído do ZIP e agrupa os PDFs por contrato:
    - cada subpasta (em qualquer profundidade) vira um grupo, contendo todos os PDFs
      encontrados recursivamente dentro dela;
    - cada PDF solto diretamente na raiz do ZIP vira seu próprio grupo (documento único).
    """
    grupos: list[tuple[str, list[tuple[str, str]]]] = []

    itens_raiz = sorted(os.listdir(tmpdir))
    for item in itens_raiz:
        caminho_item = os.path.join(tmpdir, item)

        if os.path.isdir(caminho_item):
            documentos = []
            for root, _, files in os.walk(caminho_item):
                for file in sorted(files):
                    if file.lower().endswith(".pdf"):
                        rotulo = os.path.splitext(file)[0]
                        documentos.append((rotulo, os.path.join(root, file)))
            if documentos:
                grupos.append((item, documentos))
        elif item.lower().endswith(".pdf"):
            rotulo = os.path.splitext(item)[0]
            grupos.append((rotulo, [(rotulo, caminho_item)]))

    return grupos


# Larguras de coluna (em caracteres) por tipo de campo, para aproximar o autofit do Excel.
_COLUNAS_ESTREITAS = {
    "numero_contrato", "numero_pedido_sap", "cnpj_contratante", "cnpj_contratada",
    "data_assinatura", "data_inicio_vigencia", "data_final_vigencia", "prazo_vigencia",
    "valor_total", "havera_reajuste", "enquadramento_reidi",
    "gestor_contratante_email", "gestor_contratada_email",
}
_LARGURA_ESTREITA = 18
_LARGURA_LARGA = 45
_CARACTERES_POR_LINHA = 60
_ALTURA_POR_LINHA = 12.5


def gerar_excel_formatado(df) -> bytes:
    """Gera um .xlsx seguindo a formatação exigida: Calibri 9, caixa alta, quebra de
    texto, alinhamento centralizado/à esquerda e cabeçalho verde em negrito."""
    from io import BytesIO

    wb = Workbook()
    ws = wb.active
    ws.title = "Contratos"

    fonte_padrao = Font(name="Calibri", size=9)
    fonte_cabecalho = Font(name="Calibri", size=9, bold=True, color="000000")
    preenchimento_cabecalho = PatternFill(start_color="00B050", end_color="00B050", fill_type="solid")
    alinhamento = Alignment(horizontal="left", vertical="center", wrap_text=True)

    colunas = list(df.columns)
    ws.append([str(c).upper() for c in colunas])
    for cel in ws[1]:
        cel.font = fonte_cabecalho
        cel.fill = preenchimento_cabecalho
        cel.alignment = alinhamento

    chaves_por_indice = [chave for chave, _rotulo in COLUMNS]

    for _, linha in df.iterrows():
        valores = ["" if pd.isna(v) else str(v).upper() for v in linha]
        ws.append(valores)

    for idx, nome_coluna in enumerate(colunas, start=1):
        chave = chaves_por_indice[idx - 1] if idx - 1 < len(chaves_por_indice) else None
        largura = _LARGURA_ESTREITA if chave in _COLUNAS_ESTREITAS else _LARGURA_LARGA
        ws.column_dimensions[get_column_letter(idx)].width = largura

    for row_idx in range(2, ws.max_row + 1):
        max_linhas = 1
        for col_idx in range(1, ws.max_column + 1):
            celula = ws.cell(row=row_idx, column=col_idx)
            celula.font = fonte_padrao
            celula.alignment = alinhamento
            largura_col = ws.column_dimensions[get_column_letter(col_idx)].width or _LARGURA_LARGA
            texto = str(celula.value or "")
            linhas_texto = texto.count("\n") + 1
            linhas_estimadas = max(linhas_texto, -(-len(texto) // max(int(largura_col), 1)))
            max_linhas = max(max_linhas, linhas_estimadas)
        ws.row_dimensions[row_idx].height = max(15, max_linhas * _ALTURA_POR_LINHA)

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
