def extract_report_tempo_real():
    import time

    from selenium import webdriver
    from webdriver_manager.firefox import GeckoDriverManager
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.common.by import By
    fp = Options()

    fp.add_argument("--headless") # executar sem o browser aparecer
    fp.set_preference("browser.download.folderList", 2)  # 2 indica uma pasta personalizada
    fp.set_preference("browser.download.manager.showWhenStarting", False)
    fp.set_preference("browser.download.dir", r"/home/felipe/tempo-real-etl/contadoria_tempo_real/data_tempo_real")  # Substitua pelo caminho da sua pasta
    fp.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/vnd.ms-excel")  # Tipo de arquivo XLS

    servico = Service(GeckoDriverManager().install())

    navegador = webdriver.Firefox(options=fp,service=servico)

    navegador.get("https://www.tjpe.jus.br/tjpereports/xhtml/login.xhtml")

    time.sleep(3)

    navegador.find_element('xpath','//*[@id="j_id5:cpf"]').send_keys("06016077402")

    navegador.find_element('xpath','/html/body/form/table/tbody/tr/td/table/tbody/tr[3]/td[2]/table/tbody/tr[2]/td[2]/input').send_keys("230928CiLuBi*")

    navegador.find_element('xpath',
                        '/html/body/form/table/tbody/tr/td/table/tbody/tr[3]/td[2]/table/tbody/tr[3]/td/input[1]').click()

    time.sleep(10)
    navegador.find_element('xpath', '/html/body/div/div/div/div/div[9]/div/form/div[2]/div[2]/table/tbody/tr[1]/td[2]/input').send_keys("PJe 1º Grau | Acervo em Tramitação em tempo real d")
    time.sleep(8)
    navegador.find_element('xpath', '//*[@id="relatorioForm:pesquisarButton"]').click()
    time.sleep(8)
    navegador.find_element('xpath', '/html/body/div/div/div/div/div[9]/div/form/table/tbody/tr/td[7]/table/tbody/tr/td/a/img').click()
    time.sleep(8)
    navegador.find_element('xpath', '//*[@id="filtroRelatorioForm:GRUPO"]').send_keys("TODAS")
    time.sleep(4)
    navegador.find_element('xpath', '//*[@id="filtroRelatorioForm:ORGAO"]').send_keys("TODOS")
    time.sleep(4)
    navegador.find_element('xpath', '//*[@id="filtroRelatorioForm:j_id95:0"]').click()
    time.sleep(4)
    navegador.find_element('xpath', '//*[@id="filtroRelatorioForm:j_id102:1"]').click()
    time.sleep(4)

    navegador.find_element('xpath', '//*[@id="filtroRelatorioForm:btnExportarXlsx"]').click()

    time.sleep(120)

    navegador.close()

def transform_tempo_real():

    import pandas as pd
    import glob
    import shutil
    import os
    from datetime import datetime

    # Encontrar o arquivo mais recente na pasta
    list_of_files = glob.glob('/home/felipe/tempo-real-etl/contadoria_tempo_real/data_tempo_real/*.xlsx')
    file_path = max(list_of_files, key=os.path.getctime)

    # Carregar a planilha e excluir a primeira linha
    df = pd.read_excel(file_path, skiprows=1)

    # Verificar o número de colunas no DataFrame
    num_colunas = df.shape[1]
    print(f"Número de colunas no DataFrame: {num_colunas}")

    # Selecione as colunas especificadas, se existirem
    selected_columns = [5, 7, 17, 19, 24, 25, 32]
    selected_columns = [col for col in selected_columns if col < num_colunas]

    if len(selected_columns) < 6:
        raise ValueError("O DataFrame não contém todas as colunas necessárias.")

    df_selected = df.iloc[:, selected_columns]

    # Renomear as colunas e reorganizar a ordem
    novas = ['vara', 'processo', 'data', 'dias', 'prioridade', 'lista_prioridades', 'nucleo']
    df_selected.columns = novas[:len(df_selected.columns)]
    df_selected = df_selected[['nucleo','processo', 'vara', 'data', 'dias', 'prioridade', 'lista_prioridades']]

    # Função para determinar a prioridade
    def determinar_prioridade(lista_prioridades):
        if pd.isna(lista_prioridades):
            return "Sem prioridade"
        prioridades = lista_prioridades.split(';')
        super_prioridades = ["Pessoa idosa (80+)", "Doença terminal", "Pessoa com deficiência", "Deficiente físico"]
        for prioridade in prioridades:
            if prioridade.strip() in super_prioridades:
                return "Super prioridade"
        return "Prioridade Legal"

    # Criar a nova coluna 'prioridades'
    df_selected['prioridades'] = df_selected['lista_prioridades'].apply(determinar_prioridade)

    df_selected = df_selected.drop(columns=['prioridade','lista_prioridades'])

    df_selected = df_selected.drop_duplicates(subset=['processo', 'data'])

    # Função para tratar a coluna de data
    def formatar_data(data):
        if pd.isna(data):
            return None
        primeira_data = data.split(',')[0].strip().replace("'","")
        data_formatada = pd.to_datetime(primeira_data, format='%d/%m/%Y %H:%M:%S', errors='coerce')
        if data_formatada is pd.NaT:
            return None
        return data_formatada.strftime('%d/%m/%Y')

    # Aplicar a função de formatação de data
    df_selected['data'] = df_selected['data'].apply(formatar_data)

    # Obter os núcleos únicos
    nucleos = sorted(df_selected['nucleo'].unique())

    # Calcular a quantidade de processos por núcleo
    quantidade_processos = df_selected['nucleo'].value_counts().reset_index()
    quantidade_processos.columns = ['nucleo', 'quantidade']
    quantidade_processos['data'] = datetime.now().strftime('%d/%m/%Y')
    quantidade_processos = quantidade_processos[['data', 'nucleo','quantidade']]

    # CONSOLIDADO
    consolidado = df_selected

    # Criar um arquivo Excel com várias abas
    divided_file_path = 'final_tempo_real.xlsx'

    with pd.ExcelWriter(divided_file_path) as writer:
        for nucleo in nucleos:
            df_nucleo = df_selected[df_selected['nucleo'] == nucleo]
            df_nucleo = df_nucleo.sort_values(by='dias')  # Ordenar pela data em ordem crescente
            df_nucleo.to_excel(writer, sheet_name=nucleo, index=False)
        
        # Adicionar a aba 'quantidade'
        quantidade_processos.to_excel(writer, sheet_name='QUANTIDADE', index=False)
        consolidado.to_excel(writer, sheet_name='CONSOLIDADO', index=False)
    # Mover a planilha principal para a pasta data_backup
    shutil.move(file_path, '/home/felipe/tempo-real-etl/contadoria_tempo_real/data_backup' + os.path.basename(file_path))
    # Mover a planilha dividida para a pasta data_transform
    shutil.move(divided_file_path, '/home/felipe/tempo-real-etl/contadoria_tempo_real/data_transform' + divided_file_path)

    # Mensagem de sucesso
    print(f"A tabela modificada foi salva como {divided_file_path}")

def load_tempo_real():
    import os.path

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import pandas as pd

    # Autenticação
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SERVICE_ACCOUNT_FILE = '/home/felipe/acompamhamento_contadoria/acompamhamento_contadoria/pipeline/credentials.json'  # Caminho para o seu arquivo credentials.json

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
            "/home/felipe/tempo-real-etl/contadoria_tempo_real/pipeline/credentials.json", SCOPES
        )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build('sheets', 'v4', credentials=creds)

    # ID da planilha do Google Sheets
    SPREADSHEET_ID = '1-hXLDTxGmDlPgbr_jIq73o49divD75c1jJ6Tbsw61iU'


    # Leitura do arquivo XLS local, incluindo todas as abas
    file_path = '/home/felipe/tempo-real-etl/contadoria_tempo_real/data_transform/final_tempo_real.xlsx'
    sheets = pd.read_excel(file_path, sheet_name=None)  # Lê todas as abas


    for sheet_name, df in sheets.items():
        # Convertendo DataFrame para lista de listas
        values = [df.columns.values.tolist()] + df.values.tolist()
    
        # Preparação dos dados
        body = {
            'values': values
        }         
        
        # Limpeza do conteúdo existente e atualização com novos dados
        range_name = f'{sheet_name}!A1:F6000'  # Define o range para cada aba
        service.spreadsheets().values().clear(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range=range_name,
            valueInputOption='RAW', body=body).execute()

        print(f'{result.get("updatedCells")} células atualizadas na aba {sheet_name}.')

def main():
    extract_report_tempo_real()
    transform_tempo_real()
    load_tempo_real()

if __name__ == '__main__':
    main()