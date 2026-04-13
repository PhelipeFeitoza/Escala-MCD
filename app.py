import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import calendar

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Sistema Field Service McDonalds", layout="wide")

# 2. FUNÇÃO DE PROCESSAMENTO ROBUSTA
@st.cache_data
def processar_excel(file):
    df = pd.read_excel(file, engine='openpyxl')
    
    # Mapeando: A(0)=ID, C(2)=Região, D(3)=Horário, E(4)=Técnico
    info_cols = df.iloc[:, [0, 2, 3, 4]].copy()
    info_cols.columns = ['ID', 'Regiao', 'Horario', 'Tecnico']
    
    # Limpeza de strings para evitar erro de comparação
    info_cols['ID'] = pd.to_numeric(info_cols['ID'], errors='coerce')
    info_cols['Regiao'] = info_cols['Regiao'].astype(str).str.upper().str.strip()
    info_cols['Tecnico'] = info_cols['Tecnico'].astype(str).str.strip()
    info_cols['Horario'] = info_cols['Horario'].astype(str).str.strip()
    
    datas_cols = df.iloc[:, 5:]
    df_unido = pd.concat([info_cols, datas_cols], axis=1)
    
    df_long = df_unido.melt(id_vars=['ID', 'Regiao', 'Horario', 'Tecnico'], var_name='Data_Bruta', value_name='Status')
    df_long['Data'] = pd.to_datetime(df_long['Data_Bruta'], errors='coerce')
    df_long = df_long.dropna(subset=['Data'])
    
    # Regras de Negócio para o Dashboard
    def calcular_metricas(row):
        status = str(row['Status']).upper().strip()
        regiao = str(row['Regiao'])
        
        # Trabalho Ativo (TBC, TBM, TBA, FUP)
        is_trabalho = any(s in status for s in ['TBC', 'TBM', 'TBA', 'FUP']) and 'TBH' not in status
        
        # Absenteísmo (VAGA, FT, LM, FR)
        is_abs = any(s in status for s in ['VAGA', 'FT', 'LM', 'FR', 'FALTA', 'FÉRIAS', 'LICENÇA'])
        
        # Meta Call Rate
        meta = 0
        if is_trabalho:
            meta = 4 if 'SP' in regiao and 'INTERIOR' not in regiao else 3
            
        return pd.Series([is_trabalho, is_abs, meta])

    df_long[['Is_Ativo', 'Is_Abs', 'Meta_CR']] = df_long.apply(calcular_metricas, axis=1)
    return df_long.sort_values(by=['ID', 'Data'])

# 3. ESTILIZAÇÃO
def style_status(val):
    color_map = {
        'TBC': 'background-color: #C8E6C9;', 'TBM': 'background-color: #C8E6C9;', 
        'TBA': 'background-color: #C8E6C9;', 'FUP': 'background-color: #C8E6C9;',
        'FG': 'background-color: #BBDEFB;', 'LM': 'background-color: #FFCDD2;', 
        'FT': 'background-color: #EF9A9A;', 'TR': 'background-color: #FFF9C4;', 
        'PV': 'background-color: #E1BEE7;', 'HOME': 'background-color: #F5F5F5;'
    }
    for sigla, estilo in color_map.items():
        if sigla in str(val).upper(): return estilo
    return ''

# 4. INTERFACE PRINCIPAL
arquivo = st.sidebar.file_uploader("📂 Suba a planilha ESCALA 2026", type=['xlsx'])

if arquivo:
    df_base = processar_excel(arquivo)
    
    menu = st.sidebar.radio("Navegação:", [
        "📈 Painel de Produtividade", 
        "📅 Escala Semanal", 
        "📆 Escala Mensal", 
        "🗓️ Escala Anual",
        "👤 Calendário do Técnico", 
        "📋 Espelho de Ponto (28-27)"
    ])
    
    # Filtros Globais
    regioes_lista = sorted(df_base['Regiao'].unique())
    regioes_sel = st.sidebar.multiselect("Filtrar Regiões:", regioes_lista, default=regioes_lista)
    df_f = df_base[df_base['Regiao'].isin(regioes_sel)]

    # --- 1. PAINEL DE PRODUTIVIDADE ---
    if menu == "📈 Painel de Produtividade":
        data_sel = st.sidebar.date_input("Data de Análise:", df_base['Data'].min())
        df_dia = df_f[df_f['Data'].dt.date == data_sel]
        
        st.title(f"📊 Dashboard Operacional - {data_sel.strftime('%d/%m/%Y')}")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Equipe Trabalhando", int(df_dia['Is_Ativo'].sum()))
        m2.metric("Produtividade Total", int(df_dia['Meta_CR'].sum()))
        m3.metric("Total Absenteísmo", int(df_dia['Is_Abs'].sum()))
        m4.metric("Headcount Total", len(df_dia))

        st.divider()
        st.subheader("📍 HC por Regional")
        # Ajuste para pegar NORDESTE mesmo se estiver como NOR-FORTALEZA
        cols_reg = st.columns(4)
        for i, r in enumerate(['SP', 'SUL', 'NOR', 'INTERIOR']):
            with cols_reg[i]:
                val = df_dia[df_dia['Regiao'].str.contains(r)]['Is_Ativo'].sum()
                st.info(f"**{r}**\n\nHC Ativo: {int(val)}")

    # --- 2. ESCALA SEMANAL ---
    elif menu == "📅 Escala Semanal":
        data_ref = st.sidebar.date_input("Início da Semana:", datetime(2026, 4, 13))
        fim_ref = data_ref + timedelta(days=6)
        df_s = df_f[(df_f['Data'].dt.date >= data_ref) & (df_f['Data'].dt.date <= fim_ref)]
        df_p = df_s.pivot(index=['ID', 'Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status').sort_index(level='ID')
        df_p.columns = [f"{d.strftime('%a %d/%m')}" for d in df_p.columns]
        st.dataframe(df_p.style.map(style_status), use_container_width=True)

    # --- 3. ESCALA MENSAL ---
    elif menu == "📆 Escala Mensal":
        mes = st.sidebar.slider("Mês", 1, 12, 4)
        df_m = df_f[df_f['Data'].dt.month == mes]
        df_p = df_m.pivot(index=['ID', 'Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status').sort_index(level='ID')
        df_p.columns = [f"{d.strftime('%d/%m')}" for d in df_p.columns]
        st.dataframe(df_p.style.map(style_status), height=600)

    # --- 4. ESCALA ANUAL ---
    elif menu == "🗓️ Escala Anual":
        st.title("Escala Anual Completa")
        df_p = df_f.pivot(index=['ID', 'Regiao', 'Tecnico'], columns='Data', values='Status').sort_index(level='ID')
        st.dataframe(df_p.style.map(style_status), height=600)

    # --- 5. CALENDÁRIO DO TÉCNICO (GRID) ---
    elif menu == "👤 Calendário do Técnico":
        tec = st.selectbox("Selecione o Técnico:", sorted(df_f['Tecnico'].unique()))
        mes = st.selectbox("Mês:", range(1, 13), index=3, format_func=lambda x: calendar.month_name[x])
        cal = calendar.monthcalendar(2026, mes)
        df_cal = pd.DataFrame(cal, columns=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']).astype(object)
        for r in range(len(df_cal)):
            for c in range(7):
                dia = df_cal.iloc[r, c]
                if dia != 0:
                    data_f = datetime(2026, mes, dia)
                    res = df_base[(df_base['Tecnico'] == tec) & (df_base['Data'] == data_f)]['Status'].values
                    df_cal.iloc[r, c] = f"{dia} - {res[0]}" if len(res)>0 else f"{dia}"
                else: df_cal.iloc[r, c] = ""
        st.table(df_cal.style.map(style_status))

    # --- 6. ESPELHO DE PONTO (28-27) ---
    elif menu == "📋 Espelho de Ponto (28-27)":
        tec = st.selectbox("Selecione o Técnico:", sorted(df_f['Tecnico'].unique()))
        mes_ref = st.sidebar.selectbox("Mês de Fechamento (Fim no dia 27):", range(1, 13), index=3)
        # Lógica 28 do mês anterior ao 27 do mês selecionado
        fim = datetime(2026, mes_ref, 27)
        ini = fim - timedelta(days=30) # Aproximação para o dia 28 do anterior
        ini = datetime(ini.year, ini.month, 28)
        
        st.subheader(f"Período: {ini.strftime('%d/%m')} a {fim.strftime('%d/%m')}")
        df_p = df_base[(df_base['Data'] >= ini) & (df_base['Data'] <= fim) & (df_base['Tecnico'] == tec)].copy()
        df_p['Dia Semana'] = df_p['Data'].dt.strftime('%a')
        st.table(df_p[['Data', 'Dia Semana', 'Status']].set_index('Data').style.map(style_status))

else:
    st.info("Suba sua planilha para ativar o sistema.")
