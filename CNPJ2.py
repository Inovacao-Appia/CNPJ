import json
import requests
import time
import pandas as pd
import re
from datetime import datetime

# 1. Carregar o arquivo
caminho_excel = 'CNPJs.xlsx'
df = pd.read_excel(caminho_excel, sheet_name='CNPJ')

def limpa_cnpj(cnpj):
    return re.sub(r'\D', '', str(cnpj))

def formatar_cnae(cnae_obj):
    if not cnae_obj or 'code' not in cnae_obj:
        return ""
    return f"{cnae_obj.get('code')} | {cnae_obj.get('text')}"

print(f"Iniciando processamento de {len(df)} registros...")

# Colunas conforme solicitado
colunas_socios = [f'SOCIO {i}' for i in range(1, 11)]
colunas_finais = [
    'CNPJ', 'NOME', 'CNAE PRIMARIO', 'CNAE SECUNDARIO', 'CAPITAL SOCIAL', 
    'SITUACAO CADASTRAL', 'DATA SITUACAO CADASTRADA', 'EMAIL', 'ENDEREÇO'
] + colunas_socios

# Garante que o DataFrame tenha essas colunas
for col in colunas_finais:
    if col not in df.columns:
        df[col] = ""

for index, row in df.iterrows():
    cnpj_bruto = row.get('CGC_emp') or row.get('CNPJ')
    cnpj_limpo = limpa_cnpj(cnpj_bruto)
    
    if not cnpj_limpo:
        continue

    url = f"https://receitaws.com.br/v1/cnpj/{cnpj_limpo}"
    headers = {"Accept": "application/json"}

    try:
        # Lógica de verificação
        if pd.isna(df.at[index, 'SITUACAO CADASTRAL']) or df.at[index, 'SITUACAO CADASTRAL'] == '':
            
            print(f"Consultando CNPJ: {cnpj_limpo}...")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                dados = response.json()
                
                if dados.get('status') == 'ERROR':
                    print(f"Erro na API para {cnpj_limpo}: {dados.get('message')}")
                else:
                    df.at[index, 'CNPJ'] = cnpj_limpo
                    df.at[index, 'NOME'] = dados.get('nome', '')
                    df.at[index, 'SITUACAO CADASTRAL'] = dados.get('situacao', '')
                    df.at[index, 'DATA SITUACAO CADASTRADA'] = dados.get('data_situacao', '')
                    df.at[index, 'EMAIL'] = dados.get('email', '')
                    
                    # Capital Social (Salvo como número)
                    try:
                        df.at[index, 'CAPITAL SOCIAL'] = float(dados.get('capital_social', 0))
                    except:
                        df.at[index, 'CAPITAL SOCIAL'] = 0

                    # CNAEs
                    df.at[index, 'CNAE PRIMARIO'] = formatar_cnae(dados.get('atividade_principal', [{}])[0])
                    sec = dados.get('atividades_secundarias', [])
                    df.at[index, 'CNAE SECUNDARIO'] = "\n".join([formatar_cnae(s) for s in sec])

                    # Endereço
                    end = [dados.get('logradouro'), dados.get('numero'), dados.get('municipio'), dados.get('bairro'), dados.get('uf')]
                    df.at[index, 'ENDEREÇO'] = ", ".join([str(p) for p in end if p])

                    # Sócios
                    qsa = dados.get('qsa', [])
                    for i in range(10):
                        df.at[index, f'SOCIO {i+1}'] = qsa[i].get('nome', '') if i < len(qsa) else ""

                    print(f"Sucesso: {dados.get('nome')}")
            
            elif response.status_code == 429:
                print("Aguardando 60s (Limite API)...")
                time.sleep(60)
            
            time.sleep(20) # Delay obrigatório da API gratuita

    except Exception as e:
        print(f"Erro no CNPJ {cnpj_limpo}: {e}")

# --- SALVAMENTO SIMPLES (SEM XLSXWRITER) ---
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
excel_file_path = f'Relatorio_CNPJ_{timestamp}.xlsx'

# Filtra apenas as colunas desejadas na ordem correta
df_final = df[colunas_finais]
df_final.to_excel(excel_file_path, index=False)

print(f"\nPronto! Arquivo salvo como: {excel_file_path}")