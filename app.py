import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import calendar

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Escala Field Service McDonalds", layout="wide")

# 2. FUNÇÃO PARA PROCESSAR O EXCEL REAL
def processar_excel(file):
    # Lê o excel pulando a primeira linha se for apenas cabeçalho de grupo ou lê direto
    df = pd.read_excel(file)
    
    # Mapeando as colunas conforme sua descrição
    # Coluna C (índice 2) = Região, D (3) = Horário, E (4) = Técnico
    # Colunas F em diante (5:) = Datas
    
    info_cols = df.iloc[:, [2, 3, 4]]
    info_cols.columns = ['Regiao', 'Horario', 'Tecnico']
    
    datas_cols = df.iloc[:, 5:]
    
    # Unindo as informações com as datas
    df_unido = pd.concat([info_cols, datas_cols], axis=1)
    
    # Transformando a tabela larga (Wide) em comprida (Long)
    # Isso faz com que cada dia vire uma linha para podermos filtrar
    df_long = df_unido.melt(id_vars=['Regiao', 'Horario', 'Tecnico'], 
                           var_name='Data_Bruta', 
                           value_name='Status')
    
    # Limpando a data (O Excel às vezes traz como string ou datetime)
    # Se for string como "seg 13/04", precisamos tratar, se for data, só converter
    df_long['Data'] = pd.to_datetime(df_long['Data_Bruta'], errors='coerce')
    
    # Remove linhas onde a data não foi identificada ou o técnico está vazio
    df_long = df_long.dropna(subset=['Data', 'Tecnico'])
    
    return df_long

# 3. ESTILIZAÇÃO DAS CORES
def style_status(val):
    if not isinstance(val, str) or val == "": return ''
    color_map = {
        'TB': 'background-color: #C8E6C9; color: black; font-weight: bold;', # Verde
        'FG': 'background-color: #BBDEFB; color: black;', # Azul
        'LM': 'background-color: #FFCDD2; color: black;', # Vermelho
        'FT': 'background-color: #EF9A9A; color: black;', # Vermelho Forte
        'TR': 'background-color: #FFF9C4; color: black;', # Amarelo
        'PV': 'background-color: #E1BEE7; color: black;'  # Roxo
    }
    for sigla, estilo in color_map.items():
        if sigla in val: return estilo
    return ''

# 4. INTERFACE DE UPLOAD
st.sidebar.title("📁 Importação")
arquivo_upload = st.sidebar.file_uploader("Suba sua planilha de Escala (XLSX)", type=['xlsx'])

if arquivo_upload is not None:
    with st.spinner('Processando escala de 80 técnicos...'):
        df_base = processar_excel(arquivo_upload)
    
    # --- MENU DE NAVEGAÇÃO ---
    st.sidebar.divider()
    visao = st.sidebar.selectbox("Mudar Visão:", 
        ["Calendário (Técnico)", "Mensal (Gestor)", "Semanal (Gestor)", "Espelho de Ponto (28-27)"])

    # FILTROS GLOBAIS
    regioes_unicas = df_base['Regiao'].unique()
    regioes_sel = st.sidebar.multiselect("Filtrar Regiões:", regioes_unicas, default=regioes_unicas)
    df_filtrado = df_base[df_base['Regiao'].isin(regioes_sel)]

    # --- VISÕES ---

    if visao == "Calendário (Técnico)":
        st.header("🗓️ Visualização por Técnico")
        col1, col2 = st.columns(2)
        with col1:
            tec = st.selectbox("Selecione o Técnico:", df_filtrado['Tecnico'].unique())
        with col2:
            mes = st.selectbox("Mês:", range(1, 13), index=datetime.now().month-1, format_func=lambda x: calendar.month_name[x])
        
        # Lógica do Grid de Calendário
        ano = df_filtrado['Data'].dt.year.max()
        cal_matriz = calendar.monthcalendar(ano, mes)
        df_cal = pd.DataFrame(cal_matriz, columns=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']).astype(object)

        for row in range(len(df_cal)):
            for col in range(7):
                dia = df_cal.iloc[row, col]
                if dia != 0:
                    data_f = datetime(ano, mes, dia)
                    status_val = df_filtrado[(df_filtrado['Tecnico'] == tec) & (df_filtrado['Data'] == data_f)]['Status'].values
                    status = status_val[0] if len(status_val) > 0 else "---"
                    df_cal.iloc[row, col] = f"{dia} - {status}"
                else:
                    df_cal.iloc[row, col] = ""
        
        st.table(df_cal.style.map(style_status))

    elif visao == "Mensal (Gestor)":
        mes_gestor = st.sidebar.slider("Mês de análise", 1, 12, datetime.now().month)
        st.header(f"📆 Escala Mensal Empilhada - Mês {mes_gestor}")
        
        df_m = df_filtrado[df_filtrado['Data'].dt.month == mes_gestor]
        df_pivot = df_m.pivot(index=['Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status')
        df_pivot.columns = [f"{d.strftime('%a %d/%m')}" for d in df_pivot.columns]
        
        st.dataframe(df_pivot.style.map(style_status), height=600)

    elif visao == "Semanal (Gestor)":
        st.header("📅 Escala Semanal")
        data_ref = st.date_input("Ver semana a partir de:")
        ini = data_ref - timedelta(days=data_ref.weekday())
        fim = ini + timedelta(days=6)
        
        df_s = df_filtrado[(df_filtrado['Data'].dt.date >= ini) & (df_filtrado['Data'].dt.date <= fim)]
        df_pivot_s = df_s.pivot(index=['Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status')
        df_pivot_s.columns = [f"{d.strftime('%a %d/%m')}" for d in df_pivot_s.columns]
        
        st.dataframe(df_pivot_s.style.map(style_status), use_container_width=True)

    elif visao == "Espelho de Ponto (28-27)":
        st.header("📋 Fechamento para Espelho de Ponto")
        tec_p = st.selectbox("Técnico para conferência:", df_filtrado['Tecnico'].unique())
        
        # Exemplo de seleção de período (Pode ser automatizado)
        st.write("Período de Referência: 28/03 a 27/04")
        d_ini, d_fim = datetime(2026, 3, 28), datetime(2026, 4, 27)
        
        df_p = df_filtrado[(df_filtrado['Data'] >= d_ini) & (df_filtrado['Data'] <= d_fim) & (df_filtrado['Tecnico'] == tec_p)].copy()
        df_p['Dia Semana'] = df_p['Data'].dt.strftime('%A')
        
        st.table(df_p[['Data', 'Dia Semana', 'Status']].set_index('Data').style.map(style_status))

else:
    # Mensagem caso não tenha subido o arquivo ainda
    st.info("👋 Olá Supervisor! Por favor, faça o upload da planilha de escala no menu ao lado para começar.")
    st.image("https://img.icons8.com/clouds/200/microsoft-excel.png")
