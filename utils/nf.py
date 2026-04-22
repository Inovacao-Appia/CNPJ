import pdfplumber
import json
import os
import streamlit as st
from openai import OpenAI

_api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=_api_key)

def extrair_texto_pdf(path):
    texto = ""
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            t = p.extract_text()
            if t:
                texto += t + "\n"
    return texto


PROMPT_NF = """Você é um especialista financeiro e assistente de extração de dados.
Sua tarefa é extrair informações da Nota Fiscal e retornar EXCLUSIVAMENTE um objeto JSON válido.
Chaves obrigatórias: numero_nota, data_emissao, nome_prestador, valor_bruto, valor_liquido, descricao_servico, vencimento_boleto, numero_pedido"""


def analisar_nf(texto):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {"role": "system", "content": PROMPT_NF},
            {"role": "user", "content": f"Texto extraído do PDF:\n{texto}"},
        ],
    )
    return json.loads(response.choices[0].message.content)
