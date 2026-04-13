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
        m4.metric("% Eficiência", f"{(df_dia['Is_Ativo'].sum() / (df_dia['Is_
