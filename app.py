import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import calendar

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Sistema Field Service McDonalds", layout="wide")

# 2. FUNÇÃO DE PROCESSAMENTO COM REGRAS RÍGIDAS
@st.cache_data
def processar_excel(file):
    df = pd.read_excel(file, engine='openpyxl')
    info_cols = df.iloc[:, [0, 2, 3, 4]].copy()
    info_cols.columns = ['ID', 'Regiao', 'Horario', 'Tecnico']
    
    # Padronização de dados
    info_cols['Regiao'] = info_cols['Regiao'].astype(str).str.upper().str.strip()
    info_cols['Tecnico'] = info_cols['Tecnico'].astype(str).str.strip()
    
    datas_cols = df.iloc[:, 5:]
    df_unido = pd.concat([info_cols, datas_cols], axis=1)
    df_long = df_unido.melt(id_vars=['ID', 'Regiao', 'Horario', 'Tecnico'], var_name='Data_Bruta', value_name='Status')
    df_long['Data'] = pd.to_datetime(df_long['Data_Bruta'], errors='coerce')
    df_long = df_long.dropna(subset=['Data'])
    
    # --- MAPEAMENTO DE REGIONAIS EXATAS ---
    def definir_grupo_regiao(reg):
        if 'INT' in reg or 'INTERIOR' in reg: return 'INTERIOR'
        if 'NOR' in reg: return 'NORDESTE'
        if 'SUL' in reg: return 'SUL'
        if 'SP' in reg: return 'SÃO PAULO'
        return 'OUTROS'

    df_long['Grupo_Regiao'] = df_long['Regiao'].apply(definir_grupo_regiao)

    # --- LÓGICA DE HEADCOUNT E CAPACITY (MUITO IMPORTANTE) ---
    def calcular_metricas(row):
        status = str(row['Status']).upper().strip()
        regiao_grupo = row['Grupo_Regiao']
        
        # STATUS QUE CONTAM COMO TRABALHO EM CAMPO (HC ATIVO)
        status_ativos = ['TBC', 'TBM', 'TBA', 'FUP']
        is_ativo = status in status_ativos
        
        # STATUS QUE CONTAM COMO ABSENTEÍSMO
        status_abs = ['VAGA', 'FT', 'LM', 'FR', 'FALTA', 'FÉRIAS', 'LICENÇA MÉDICA']
        is_abs = status in status_abs
        
        # CÁLCULO DE CAPACITY (META)
        meta = 0
        if is_ativo:
            meta = 4 if regiao_grupo == 'SÃO PAULO' else 3
            
        return pd.Series([is_ativo, is_abs, meta])

    df_long[['Is_Ativo', 'Is_Abs', 'Meta_CR']] = df_long.apply(calcular_metricas, axis=1)
    return df_long

# 3. ESTILIZAÇÃO (FONTE PRETA E NEGRITO PARA CONTRASTE)
def style_status(val):
    if not isinstance(val, str): return ''
    val_upper = val.upper()
    
    # Cores de fundo
    bg_color = "transparent"
    if any(s in val_upper for s in ['TBC', 'TBM', 'TBA', 'FUP']): bg_color = "#C8E6C9" # Verde
    elif 'FG' in val_upper or 'BH' in val_upper: bg_color = "#BBDEFB" # Azul
    elif 'LM' in val_upper or 'FT' in val_upper: bg_color = "#FFCDD2" # Vermelho
    elif 'TR' in val_upper: bg_color = "#FFF9C4" # Amarelo
    elif 'PV' in val_upper: bg_color = "#E1BEE7" # Roxo
    
    return f'background-color: {bg_color}; color: black; font-weight: bold; border: 0.1px solid #ddd;'

# 4. INTERFACE
arquivo = st.sidebar.file_uploader("📂 Suba a planilha ESCALA 2026", type=['xlsx'])

if arquivo:
    df_base = processar_excel(arquivo)
    
    menu = st.sidebar.radio("Navegação:", [
        "📈 Painel de Produtividade", 
        "📅 Escala Semanal", 
        "📆 Escala Mensal", 
        "🗓️ Escala Anual",
        "👤 Calendário do Técnico", 
        "📋 Espelho de Ponto"
    ])
    
    # Filtros
    regioes_lista = sorted(df_base['Regiao'].unique())
    regioes_sel = st.sidebar.multiselect("Filtrar por Região Específica:", regioes_lista, default=regioes_lista)
    df_f = df_base[df_base['Regiao'].isin(regioes_sel)]

    # --- 1. PAINEL DE PRODUTIVIDADE ---
    if menu == "📈 Painel de Produtividade":
        st.title("📊 Resumo Operacional")
        data_sel = st.sidebar.date_input("Selecione o dia:", df_base['Data'].min())
        df_dia = df_f[df_f['Data'].dt.date == data_sel]

        # Métricas Gerais
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Headcount Ativo", int(df_dia['Is_Ativo'].sum()))
        m2.metric("Capacity Total", int(df_dia['Meta_CR'].sum()))
        m3.metric("Absenteísmo", int(df_dia['Is_Abs'].sum()))
        m4.metric("% Eficiência", f"{(df_dia['Is_Ativo'].sum() / (df_dia['Is_Ativo'].sum() + df_dia['Is_Abs'].sum()) * 100):.1f}%" if (df_dia['Is_Ativo'].sum() + df_dia['Is_Abs'].sum()) > 0 else "0%")

        st.divider()
        
        # Tabela por Regional (Ordem solicitada: SP, Interior, Sul, Nordeste)
        st.subheader("📍 Detalhamento por Regional")
        ordem_reg = ['SÃO PAULO', 'INTERIOR', 'SUL', 'NORDESTE']
        cols = st.columns(4)
        
        for i, r_nome in enumerate(ordem_reg):
            with cols[i]:
                df_reg_total = df_dia[df_dia['Grupo_Regiao'] == r_nome]
                hc = int(df_reg_total['Is_Ativo'].sum())
                cr = int(df_reg_total['Meta_CR'].sum())
                
                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid #ff4b4b;">
                    <h4 style="margin:0;">{r_nome}</h4>
                    <hr>
                    <p style="margin:0;">HC Ativo: <b>{hc}</b></p>
                    <p style="margin:0; font-size: 1.2em; color: #2e7d32;">Call Rate: <b>{cr}</b></p>
                </div>
                """, unsafe_allow_html=True)

    # --- 2. ESCALA SEMANAL ---
    elif menu == "📅 Escala Semanal":
        data_ini = st.sidebar.date_input("Início da semana:", datetime(2026, 4, 13))
        df_s = df_f[(df_f['Data'].dt.date >= data_ini) & (df_f['Data'].dt.date <= data_ini + timedelta(days=6))]
        df_p = df_s.pivot(index=['ID', 'Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status').sort_index(level='ID')
        df_p.columns = [f"{d.strftime('%a %d/%m')}" for d in df_p.columns]
        st.dataframe(df_p.style.map(style_status), height=600)

    # --- 3. ESCALA MENSAL ---
    elif menu == "📆 Escala Mensal":
        mes = st.sidebar.slider("Mês", 1, 12, 4)
        df_m = df_f[df_f['Data'].dt.month == mes]
        df_p = df_m.pivot(index=['ID', 'Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status').sort_index(level='ID')
        df_p.columns = [f"{d.strftime('%d/%m')}" for d in df_p.columns]
        st.dataframe(df_p.style.map(style_status), height=600)

    # --- 4. CALENDÁRIO DO TÉCNICO ---
    elif menu == "👤 Calendário do Técnico":
        tec = st.selectbox("Técnico:", sorted(df_f['Tecnico'].unique()))
        mes = st.selectbox("Mês:", range(1, 13), index=3, format_func=lambda x: calendar.month_name[x])
        cal = calendar.monthcalendar(2026, mes)
        df_cal = pd.DataFrame(cal, columns=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']).astype(object)
        for r in range(len(df_cal)):
            for c in range(7):
                dia = df_cal.iloc[r, c]
                if dia != 0:
                    data_f = datetime(2026, mes, dia)
                    stat = df_base[(df_base['Tecnico'] == tec) & (df_base['Data'] == data_f)]['Status'].values
                    df_cal.iloc[r, c] = f"{dia} - {stat[0]}" if len(stat)>0 else f"{dia}"
                else: df_cal.iloc[r, c] = ""
        st.table(df_cal.style.map(style_status))

    # --- 5. ESPELHO DE PONTO (28-27) ---
    elif menu == "📋 Espelho de Ponto":
        tec = st.selectbox("Técnico:", sorted(df_f['Tecnico'].unique()))
        mes_f = st.sidebar.selectbox("Mês de Fechamento (Fim dia 27):", range(1, 13), index=3)
        fim = datetime(2026, mes_f, 27)
        ini = (fim - timedelta(days=30)).replace(day=28)
        df_p = df_base[(df_base['Data'] >= ini) & (df_base['Data'] <= fim) & (df_base['Tecnico'] == tec)].copy()
        df_p['Dia'] = df_p['Data'].dt.strftime('%a %d/%m')
        st.table(df_p[['Dia', 'Status']].set_index('Dia').style.map(style_status))

else:
    st.info("Suba sua planilha para ativar o sistema.")
