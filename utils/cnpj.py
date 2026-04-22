import requests
import re
import streamlit as st

def limpa_cnpj(cnpj):
    return re.sub(r'\D', '', str(cnpj))

def formatar_cnae(cnae_obj):
    if not cnae_obj or 'code' not in cnae_obj:
        return ""
    return f"{cnae_obj.get('code')} | {cnae_obj.get('text')}"

@st.cache_data(ttl=3600)
def consultar_cnpj(cnpj):
    url = f"https://receitaws.com.br/v1/cnpj/{cnpj}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 429:
            return {"status": "ERROR", "message": "Limite de consultas atingido (aguarde 1 min)"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}
    return None

def processar_dados_cnpj(dados):
    if not dados or dados.get("status") == "ERROR":
        return None

    end = [dados.get('logradouro'), dados.get('numero'), dados.get('municipio'), dados.get('bairro'), dados.get('uf')]
    endereco_full = ", ".join([str(p) for p in end if p])

    res = {
        "CNPJ": dados.get("cnpj"),
        "NOME": dados.get("nome"),
        "DATA ABERTURA": dados.get("abertura"),
        "CNAE PRIMARIO": formatar_cnae(dados.get("atividade_principal", [{}])[0]),
        "CNAE SECUNDARIO": "\n".join([formatar_cnae(s) for s in dados.get("atividades_secundarias", [])]),
        "CAPITAL SOCIAL": float(dados.get("capital_social", 0) or 0),
        "SITUACAO CADASTRAL": dados.get("situacao"),
        "DATA SITUACAO CADASTRADA": dados.get("data_situacao"),
        "EMAIL": dados.get("email"),
        "ENDEREÇO": endereco_full,
    }

    qsa = dados.get("qsa", [])
    for i in range(1, 11):
        res[f"SOCIO {i}"] = qsa[i - 1].get("nome", "") if i <= len(qsa) else ""

    return res
