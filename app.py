import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import calendar

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gestão Field Service McDonalds", layout="wide")

# 2. FUNÇÃO PARA PROCESSAR O EXCEL
def processar_excel(file):
    df = pd.read_excel(file, engine='openpyxl')
    
    # Colunas: A(0)=ID, C(2)=Região, D(3)=Horário, E(4)=Técnico
    info_cols = df.iloc[:, [0, 2, 3, 4]].copy()
    info_cols.columns = ['ID', 'Regiao', 'Horario', 'Tecnico']
    
    # Limpeza de nomes e tipos
    info_cols['ID'] = pd.to_numeric(info_cols['ID'], errors='coerce')
    info_cols['Regiao'] = info_cols['Regiao'].astype(str).replace('nan', 'N/D')
    
    datas_cols = df.iloc[:, 5:]
    df_unido = pd.concat([info_cols, datas_cols], axis=1)
    
    # Transforma em formato longo
    df_long = df_unido.melt(id_vars=['ID', 'Regiao', 'Horario', 'Tecnico'], var_name='Data_Bruta', value_name='Status')
    df_long['Data'] = pd.to_datetime(df_long['Data_Bruta'], errors='coerce')
    df_long = df_long.dropna(subset=['Data'])
    
    # --- NOVA LÓGICA DE CONTAGEM (FLEXÍVEL) ---
    def calcular_meta(row):
        status = str(row['Status']).upper().strip()
        # Se começar com TB (TBC, TBM, TBA) mas não for TBH (Home)
        if status.startswith('TB') and status != 'TBH':
            return 4 if 'SP' in str(row['Regiao']).upper() else 3
        return 0

    df_long['Capacity'] = df_long.apply(calcular_meta, axis=1)
    
    # Lógica de Absenteísmo (VAGA, FT, FR, LM)
    status_abs = ['VAGA', 'FT', 'FR', 'LM', 'FALTA', 'FÉRIAS']
    df_long['Is_Abs'] = df_long['Status'].apply(lambda x: 1 if str(x).upper().strip() in status_abs else 0)
    
    return df_long.sort_values(by=['ID', 'Data'])

# 3. ESTILIZAÇÃO
def style_status(val):
    color_map = {
        'TB': 'background-color: #C8E6C9; color: black;', # Verde para qualquer TB (TBC, TBM...)
        'FG': 'background-color: #BBDEFB; color: black;', 
        'LM': 'background-color: #FFCDD2; color: black;', 
        'FT': 'background-color: #EF9A9A; color: black;', 
        'TR': 'background-color: #FFF9C4; color: black;', 
        'PV': 'background-color: #E1BEE7; color: black;',
        'HOME': 'background-color: #F5F5F5; color: #9E9E9E;'
    }
    for sigla, estilo in color_map.items():
        if sigla in str(val).upper(): return estilo
    return ''

# 4. INTERFACE
st.sidebar.title("📁 Importação")
arquivo_upload = st.sidebar.file_uploader("Suba a planilha ESCALA 2026", type=['xlsx'])

if arquivo_upload is not None:
    df_base = processar_excel(arquivo_upload)
    
    # --- SELETOR DE DATA PARA O DASHBOARD ---
    st.sidebar.divider()
    st.sidebar.subheader("📅 Data do Resumo")
    data_resumo = st.sidebar.date_input("Escolha o dia para analisar:", datetime(2026, 4, 1))

    visao = st.sidebar.selectbox("Mudar Visão Principal:", ["Mensal (Gestor)", "Calendário (Técnico)", "Semanal (Gestor)", "Espelho de Ponto"])
    
    regioes = sorted(df_base['Regiao'].unique())
    regioes_sel = st.sidebar.multiselect("Filtrar Regiões:", regioes, default=regioes)
    df_f = df_base[df_base['Regiao'].isin(regioes_sel)]

    # --- DASHBOARD DINÂMICO ---
    st.markdown(f"### 📊 Resumo Operacional - Dia {data_resumo.strftime('%d/%m/%Y')}")
    
    # Filtrando apenas o dia selecionado
    df_hoje = df_f[df_f['Data'].dt.date == data_resumo]
    
    if not df_hoje.empty:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            # Conta quem tem status que começa com TB e não é TBH
            hc_ativo = len(df_hoje[(df_hoje['Capacity'] > 0)])
            st.metric("Headcount Ativo", hc_ativo)
        with c2:
            cap_total = df_hoje['Capacity'].sum()
            st.metric("Capacity (Chamados)", f"{int(cap_total)}")
        with c3:
            abs_total = df_hoje['Is_Abs'].sum()
            st.metric("Absenteísmo", abs_total)
        with c4:
            # Técnicos previstos (Ativos + Absenteístas)
            total_previsto = hc_ativo + abs_total
            pct = (hc_ativo / total_previsto * 100) if total_previsto > 0 else 0
            st.metric("Disponibilidade", f"{pct:.1f}%")
    else:
        st.warning("Sem dados para a data selecionada no seletor lateral.")

    st.divider()

    # --- VISÕES ---
    if visao == "Mensal (Gestor)":
        mes_g = st.sidebar.slider("Mês", 1, 12, int(data_resumo.month))
        df_m = df_f[df_f['Data'].dt.month == mes_g]
        df_pivot = df_m.pivot(index=['ID', 'Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status').sort_index(level='ID')
        df_pivot.columns = [f"{d.strftime('%a %d/%m')}" for d in df_pivot.columns]
        st.dataframe(df_pivot.style.map(style_status), height=600)

    elif visao == "Calendário (Técnico)":
        st.header("🗓️ Calendário Individual")
        tec = st.selectbox("Selecione o Técnico:", df_f.sort_values('ID')['Tecnico'].unique())
        mes = st.selectbox("Mês:", range(1, 13), index=data_resumo.month-1, format_func=lambda x: calendar.month_name[x])
        
        cal = calendar.monthcalendar(2026, mes)
        df_cal = pd.DataFrame(cal, columns=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']).astype(object)
        for r in range(len(df_cal)):
            for c in range(7):
                dia = df_cal.iloc[r, c]
                if dia != 0:
                    data_f = datetime(2026, mes, dia)
                    status = df_f[(df_f['Tecnico'] == tec) & (df_f['Data'] == data_f)]['Status'].values
                    df_cal.iloc[r, c] = f"{dia} - {status[0]}" if len(status)>0 else f"{dia}"
                else: df_cal.iloc[r, c] = ""
        st.table(df_cal.style.map(style_status))

else:
    st.info("Suba sua planilha para visualizar o Dashboard.")
