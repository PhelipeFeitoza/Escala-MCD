import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import calendar

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Escala Field Service McDonalds", layout="wide")

# 2. FUNÇÃO PARA PROCESSAR O EXCEL REAL
def processar_excel(file):
    # Lendo o Excel - Forçamos o motor openpyxl
    # Se a sua planilha tiver títulos acima da tabela, mude header=0 para a linha correta
    df = pd.read_excel(file, engine='openpyxl')
    
    # Tentativa automática de encontrar as colunas C, D e E
    # Usamos iloc para garantir que pegamos pela posição (C=2, D=3, E=4)
    info_cols = df.iloc[:, [2, 3, 4]]
    info_cols.columns = ['Regiao', 'Horario', 'Tecnico']
    
    # As datas começam na coluna F (índice 5)
    datas_cols = df.iloc[:, 5:]
    
    # Unindo tudo
    df_unido = pd.concat([info_cols, datas_cols], axis=1)
    
    # Transformando em formato longo (Técnico | Data | Status)
    df_long = df_unido.melt(id_vars=['Regiao', 'Horario', 'Tecnico'], 
                           var_name='Data_Bruta', 
                           value_name='Status')
    
    # Tratamento de Data
    df_long['Data'] = pd.to_datetime(df_long['Data_Bruta'], errors='coerce')
    
    # Limpeza final
    df_long = df_long.dropna(subset=['Data', 'Tecnico'])
    
    return df_long

# 3. ESTILIZAÇÃO
def style_status(val):
    if not isinstance(val, str) or val == "": return ''
    color_map = {
        'TB': 'background-color: #C8E6C9; color: black; font-weight: bold;', 
        'FG': 'background-color: #BBDEFB; color: black;', 
        'LM': 'background-color: #FFCDD2; color: black;', 
        'FT': 'background-color: #EF9A9A; color: black;', 
        'TR': 'background-color: #FFF9C4; color: black;', 
        'PV': 'background-color: #E1BEE7; color: black;'  
    }
    for sigla, estilo in color_map.items():
        if sigla in str(val): return estilo
    return ''

# 4. INTERFACE
st.sidebar.title("📁 Importação")
arquivo_upload = st.sidebar.file_uploader("Suba sua planilha de Escala (XLSX)", type=['xlsx'])

if arquivo_upload is not None:
    try:
        df_base = processar_excel(arquivo_upload)
        
        # MENU
        st.sidebar.divider()
        visao = st.sidebar.selectbox("Mudar Visão:", 
            ["Calendário (Técnico)", "Mensal (Gestor)", "Semanal (Gestor)", "Espelho de Ponto (28-27)"])

        # FILTROS
        regioes = df_base['Regiao'].unique()
        regioes_sel = st.sidebar.multiselect("Filtrar Regiões:", regioes, default=regioes)
        df_filtrado = df_base[df_base['Regiao'].isin(regioes_sel)]

        # --- VISÃO: CALENDÁRIO ---
        if visao == "Calendário (Técnico)":
            st.header("🗓️ Visualização por Técnico")
            t_col, m_col = st.columns(2)
            with t_col:
                tec = st.selectbox("Selecione o Técnico:", df_filtrado['Tecnico'].unique())
            with m_col:
                mes = st.selectbox("Mês:", range(1, 13), index=datetime.now().month-1, format_func=lambda x: calendar.month_name[x])
            
            ano = df_filtrado['Data'].dt.year.max()
            cal_matriz = calendar.monthcalendar(ano, mes)
            df_cal = pd.DataFrame(cal_matriz, columns=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']).astype(object)

            for row in range(len(df_cal)):
                for col in range(7):
                    dia = df_cal.iloc[row, col]
                    if dia != 0:
                        data_f = datetime(ano, mes, dia)
                        # Busca exata do dia
                        status_val = df_filtrado[(df_filtrado['Tecnico'] == tec) & (df_filtrado['Data'] == data_f)]['Status'].values
                        status = status_val[0] if len(status_val) > 0 else "---"
                        df_cal.iloc[row, col] = f"{dia} - {status}"
                    else:
                        df_cal.iloc[row, col] = ""
            
            st.table(df_cal.style.map(style_status))

        # --- VISÃO: MENSAL GESTOR ---
        elif visao == "Mensal (Gestor)":
            mes_g = st.sidebar.slider("Mês de análise", 1, 12, datetime.now().month)
            st.header(f"📆 Escala Mensal - Mês {mes_g}")
            df_m = df_filtrado[df_filtrado['Data'].dt.month == mes_g]
            df_pivot = df_m.pivot(index=['Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status')
            df_pivot.columns = [f"{d.strftime('%a %d/%m')}" for d in df_pivot.columns]
            st.dataframe(df_pivot.style.map(style_status), height=600)

        # --- VISÃO: SEMANAL GESTOR ---
        elif visao == "Semanal (Gestor)":
            st.header("📅 Escala Semanal")
            data_ref = st.date_input("Ver semana do dia:", datetime.now())
            ini = data_ref - timedelta(days=data_ref.weekday())
            fim = ini + timedelta(days=6)
            mask = (df_filtrado['Data'].dt.date >= ini) & (df_filtrado['Data'].dt.date <= fim)
            df_s = df_filtrado[mask].pivot(index=['Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status')
            df_s.columns = [f"{d.strftime('%a %d/%m')}" for d in df_s.columns]
            st.dataframe(df_s.style.map(style_status), use_container_width=True)

        # --- VISÃO: ESPELHO DE PONTO ---
        elif visao == "Espelho de Ponto (28-27)":
            st.header("📋 Conferência de Ponto (28 a 27)")
            tec_p = st.selectbox("Técnico:", df_filtrado['Tecnico'].unique())
            # Exemplo fixo, depois podemos tornar dinâmico
            d_ini, d_fim = datetime(2026, 3, 28), datetime(2026, 4, 27)
            df_p = df_filtrado[(df_filtrado['Data'] >= d_ini) & (df_filtrado['Data'] <= d_fim) & (df_filtrado['Tecnico'] == tec_p)].copy()
            df_p['Dia'] = df_p['Data'].dt.strftime('%a %d/%m')
            st.table(df_p[['Dia', 'Status']].set_index('Dia').style.map(style_status))

    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        st.info("Verifique se as colunas C, D e E contêm Região, Horário e Técnico.")

else:
    st.info("Aguardando upload da planilha...")
