# CNPJ
import json
import requests
import time
import pandas as pd


# 1. Carregar o arquivo CSV (convertido do Excel enviado)
# O nome do arquivo salvo é 'CNPJs.xlsx - Página1.csv'
caminho_excel = 'CNPJs.xlsx'
# 2. Ler o arquivo especificando o nome da aba
df = pd.read_excel(caminho_excel, sheet_name='CNPJ')

# 2. Exibir as primeiras linhas para conferência
print("DataFrame carregado com sucesso:")
print(df.head())

# Supondo que você já tenha o DataFrame 'df'
for index, row in df.iterrows():
    cnpj = row['CGC_emp']
    url = f"https://receitaws.com.br/v1/cnpj/{cnpj}"
    headers = {
        "Accept": "application/json",
    }

    # Tentar fazer a requisição
    try:
        response = requests.get(url, headers=headers)
        print(response)
        print('ANTES DE ESPERAR')
        time.sleep(60)  # Esperar 60 segundos entre as requisições para não sobrecarregar o serviço
        print('DEPOIS DE ESPERAR')
        if (pd.isna(row['Situação cadastral']) or row['Situação cadastral'] == '') and \
           (pd.isna(row['Data da situação cadastral']) or row['Data da situação cadastral'] == '') and \
           (pd.isna(row['CNAEs Secundários']) or row['CNAEs Secundários'] == ''):

            if response.status_code == 200:
                dados_cnpj = response.json()

                # Atualizar o DataFrame com os novos dados
                df.at[index, 'Data da situação cadastral'] = dados_cnpj.get('data_situacao', '')
                df.at[index, 'Situação cadastral'] = dados_cnpj.get('situacao', '')
                df.at[index, 'CNAEs Secundários'] = json.dumps(dados_cnpj.get('atividades_secundarias', []), ensure_ascii=False)
                df.at[index, 'QSA'] = json.dumps(dados_cnpj.get('qsa', []), ensure_ascii=False)

                # Extrair todos os nomes onde 'qual' seja '05-Administrador'
                administradores = [item['nome'] for item in dados_cnpj.get('qsa', []) if item['qual'] == '05-Administrador']

                # Adicionar a nova coluna com os nomes dos administradores
                df.at[index, 'Administradores'] = ', '.join(administradores)
                print(df)
                print('+1')
            else:
                print(f"Erro: {response.status_code}, {response.text}")

    except Exception as e:
        print(f"Ocorreu um erro ao processar o CNPJ {cnpj}: {e}")
        continue  # Continuar para a próxima linha do DataFrame

# Salvar o DataFrame atualizado em um arquivo Excel
excel_file_path = 'requests_empresas.xlsx'
df.to_excel(excel_file_path, index=False)