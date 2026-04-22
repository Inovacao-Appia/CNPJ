import streamlit as st
import pandas as pd
import requests
import time
import re
from datetime import datetime
from io import BytesIO


# --- CONFIGURAÇÃO DA PÁGINA (OPCIONAL) ---
st.set_page_config(page_title="Appia Tools", layout="wide")

# --- LOGO NA SIDEBAR (COLOQUE AQUI) ---
# O local ideal é logo após os imports para que ele seja a primeira coisa a carregar
st.sidebar.image("Logos/Via Appia/PNG/Via Appia Negativo.png", use_container_width=True)

# --- FUNÇÕES DE CONSULTA CNPJ ---
def limpa_cnpj(cnpj):
    return re.sub(r'\D', '', str(cnpj))

def formatar_cnae(cnae_obj):
    if not cnae_obj or 'code' not in cnae_obj: return ""
    return f"{cnae_obj.get('code')} | {cnae_obj.get('text')}"

@st.cache_data(ttl=3600)  # Cache de 1 hora para não gastar API repetida
def consultar_cnpj(cnpj_limpo):
    url = f"https://receitaws.com.br/v1/cnpj/{cnpj_limpo}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            return {"status": "ERROR", "message": "Limite de consultas atingido (aguarde 1 min)"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}
    return None

def processar_dados_cnpj(dados):
    """Trata o JSON da API para o formato de dicionário que queremos"""
    if not dados or dados.get('status') == 'ERROR':
        return None
    
    # Formatação de Endereço
    end = [dados.get('logradouro'), dados.get('numero'), dados.get('municipio'), dados.get('bairro'), dados.get('uf')]
    endereco_full = ", ".join([str(p) for p in end if p])
    
    res = {
        "CNPJ": dados.get('cnpj'),
        "NOME": dados.get('nome'),
        "DATA ABERTURA": dados.get('abertura'),
        "CNAE PRIMARIO": formatar_cnae(dados.get('atividade_principal', [{}])[0]),
        "CNAE SECUNDARIO": "\n".join([formatar_cnae(s) for s in dados.get('atividades_secundarias', [])]),
        "CAPITAL SOCIAL": float(dados.get('capital_social', 0)),
        "SITUACAO CADASTRAL": dados.get('situacao'),
        "DATA SITUACAO CADASTRADA": dados.get('data_situacao'),
        "EMAIL": dados.get('email'),
        "ENDEREÇO": endereco_full
    }
    
    # Sócios (1 a 10)
    qsa = dados.get('qsa', [])
    for i in range(1, 11):
        res[f"SOCIO {i}"] = qsa[i-1].get('nome', '') if i <= len(qsa) else ""
        
    return res

# --- ADICIONAR AO MENU DO STREAMLIT ---
# (Simulando a adição do item "Consulta CNPJ" na sua sidebar)
st.sidebar.divider()
st.sidebar.subheader("Ferramentas Úteis")
modo_cnpj = st.sidebar.checkbox("🔍 Consulta CNPJ")

if modo_cnpj:
    st.title("🔍 Consulta de Dados CNPJ")
    tab_unitario, tab_massa = st.tabs(["Consulta Única", "Processamento em Massa"])

    # --- ABA: CONSULTA ÚNICA ---
    with tab_unitario:
        cnpj_input = st.text_input("Digite o CNPJ (apenas números)")
        if st.button("Consultar"):
            cnpj_limpo = limpa_cnpj(cnpj_input)
            if len(cnpj_limpo) == 14:
                with st.spinner("Buscando dados na Receita..."):
                    resultado = consultar_cnpj(cnpj_limpo)
                    dados_finais = processar_dados_cnpj(resultado)
                
                if dados_finais:
                    st.success(f"Dados de {dados_finais['NOME']}")
                    
                    # 1. Informações Principais (Métricas)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Situação", dados_finais["SITUACAO CADASTRAL"])
                    c2.metric("Capital Social", f"R$ {dados_finais['CAPITAL SOCIAL']:,.2f}")
                    c3.metric("Data de Abertura", dados_finais["DATA ABERTURA"])

                    st.divider()

                    # 2. Detalhes de Contato e Localização
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.markdown(f"**📧 Email:** {dados_finais['EMAIL'] if dados_finais['EMAIL'] else 'Não informado'}")
                        st.markdown(f"**📍 Endereço:** {dados_finais['ENDEREÇO']}")
                    with col_info2:
                        st.markdown(f"**📅 Data da Situação:** {dados_finais['DATA SITUACAO CADASTRADA']}")
                        st.markdown(f"**🆔 CNPJ:** {dados_finais['CNPJ']}")

                    st.divider()

                    # 3. Atividades (CNAEs)
                    st.subheader("Atividades Econômicas")
                    st.info(f"**Primária:** {dados_finais['CNAE PRIMARIO']}")
                    with st.expander("Ver Atividades Secundárias"):
                        if dados_finais['CNAE SECUNDARIO']:
                            st.text(dados_finais['CNAE SECUNDARIO'])
                        else:
                            st.write("Sem atividades secundárias registradas.")

                    st.divider()

                    # 4. Quadro de Sócios (QSA)
                    st.subheader("Quadro de Sócios e Administradores")
                    socios = [dados_finais[f"SOCIO {i}"] for i in range(1, 11) if dados_finais[f"SOCIO {i}"]]
                    
                    if socios:
                        # Exibe os sócios em uma lista bonita
                        for i, socio in enumerate(socios, 1):
                            st.write(f"{i}. {socio}")
                    else:
                        st.write("Informação de sócios não disponível.")

                else:
                    st.error(resultado.get('message', "Erro desconhecido ou CNPJ não encontrado."))
            else:
                st.warning("CNPJ Inválido. Deve conter 14 dígitos.")

    # --- ABA: PROCESSAMENTO EM MASSA ---
    with tab_massa:
        st.info("⚠️ O processamento em massa levará 20 segundos por CNPJ devido ao limite da API gratuita.")
    
        # --- BOTÃO DE MODELO ADICIONADO AQUI ---
        col_modelo_1, col_modelo_2 = st.columns([3, 1])
        with col_modelo_1:
            st.write("1. Baixe o modelo se ainda não tiver a lista formatada:")
        with col_modelo_2:
            # Gerando o modelo simples em memória
            df_modelo = pd.DataFrame({"CNPJ": ["00.000.000/0000-00"]})
            buffer_modelo = BytesIO()
            with pd.ExcelWriter(buffer_modelo, engine='openpyxl') as writer:
                df_modelo.to_excel(writer, index=False)
            
            st.download_button(
                label="📄 Baixar Modelo",
                data=buffer_modelo.getvalue(),
                file_name="modelo_cnpjs.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        st.divider()
        
        st.write("2. Suba sua planilha preenchida:")
        up_cnpj = st.file_uploader("Arraste o arquivo aqui", type=["xlsx"], label_visibility="collapsed")
        if up_cnpj:
            df_entrada = pd.read_excel(up_cnpj)
            st.write("Visualização da entrada:", df_entrada.head())
            
            if st.button("🚀 Iniciar Processamento"):
                progresso = st.progress(0)
                resultados_lote = []
                
                # Procura a coluna CNPJ independente de estar maiúsculo ou minúsculo
                col_cnpj = next((c for c in df_entrada.columns if 'cnpj' in c.lower()), None)
                
                if col_cnpj:
                    lista_cnpjs = df_entrada[col_cnpj].dropna().tolist()
                    total = len(lista_cnpjs)
                    
                    for i, c in enumerate(lista_cnpjs):
                        cnpj_limpo = limpa_cnpj(c)
                        st.write(f"Processando {i+1}/{total}: {cnpj_limpo}")
                        
                        res_api = consultar_cnpj(cnpj_limpo)
                        dados_tratados = processar_dados_cnpj(res_api)
                        
                        if dados_tratados:
                            resultados_lote.append(dados_tratados)
                        
                        progresso.progress((i + 1) / total)
                        
                        # Delay para não ser bloqueado pela API (apenas se não for o último)
                        if i < total - 1:
                            time.sleep(21) 
                    
                    df_resultado = pd.DataFrame(resultados_lote)
                    st.dataframe(df_resultado)
                    
                    # Download do Resultado
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_resultado.to_excel(writer, index=False)
                    
                    st.success("✅ Processamento concluído!")
                    st.download_button(
                        "📥 Baixar Planilha Completa",
                        output.getvalue(),
                        file_name=f"Resultado_CNPJ_{datetime.now().strftime('%H%M%S')}.xlsx"
                    )
                else:
                    st.error("Coluna 'CNPJ' não encontrada na planilha.")