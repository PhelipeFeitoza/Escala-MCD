import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import calendar

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Command Center - Field Service McDonalds", layout="wide")

# CSS PARA MÁXIMO CONTRASTE E CORES DA LEGENDA (LEDGER STYLE)
st.markdown("""
<style>
    .metric-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 15px; border-bottom: 1px solid #ccc; font-weight: 800; color: black !important; font-size: 13px; margin-bottom: 2px; border-radius: 4px; }
    .header-abs { background-color: #f4b084; text-align: center; font-weight: 900; font-size: 16px; padding: 10px; color: black !important; border: 1px solid #333; }
    .vaga { background-color: #d9d9d9; } .falta { background-color: #ff0000; }
    .lm { background-color: #00ffff; } .ferias { background-color: #cc99ff; }
    .folga { background-color: #5b9bd5; } .bh { background-color: #deeaf6; }
    .tr { background-color: #ffeb3b; } .pv { background-color: #c5e0b4; }
    .trabalhando { background-color: #e2efda; } .headcount { background-color: #ffd966; }
    .produtividade { background-color: #7030a0; color: white !important; font-size: 18px; padding: 12px; border-radius: 5px; text-align: center; }
    .sub-sp-card { padding: 12px; border-radius: 8px; border: 1px solid #777; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: black !important; font-weight: 900; }
    table { font-weight: bold !important; color: black !important; width: 100%; }
</style>
""", unsafe_allow_html=True)

# 2. PROCESSAMENTO DE DADOS (LOGICA REVISADA E BLINDADA)
@st.cache_data
def processar_excel(file):
    df = pd.read_excel(file, engine='openpyxl')
    info_cols = df.iloc[:, [0, 2, 3, 4]].copy()
    info_cols.columns = ['ID', 'Regiao', 'Horario', 'Tecnico']
    
    info_cols['Regiao'] = info_cols['Regiao'].astype(str).str.upper().str.strip()
    info_cols['Tecnico'] = info_cols['Tecnico'].astype(str).str.strip()
    
    datas_cols = df.iloc[:, 5:]
    df_unido = pd.concat([info_cols, datas_cols], axis=1)
    df_long = df_unido.melt(id_vars=['ID', 'Regiao', 'Horario', 'Tecnico'], var_name='Data_Bruta', value_name='Status')
    df_long['Data'] = pd.to_datetime(df_long['Data_Bruta'], errors='coerce')
    df_long = df_long.dropna(subset=['Data'])
    
    def mapear_status(row):
        st_val = str(row['Status']).upper().strip()
        reg = str(row['Regiao'])
        nome = str(row['Tecnico']).upper()
        
        # Regional Blindada
        if 'INT-' in reg or 'INTERIOR' in reg: grupo = 'INTERIOR'
        elif 'NOR-' in reg: grupo = 'NORDESTE'
        elif 'SUL-' in reg: grupo = 'SUL'
        elif 'SP-' in reg: grupo = 'SÃO PAULO'
        else: grupo = 'OUTROS'
        
        is_gestao = any(x in nome for x in ['SUPERVISOR', 'N3', 'COORDENADOR', 'GESTOR', 'BACKOFFICE'])
        is_fup = (st_val == 'FUP')
        is_trabalho = st_val in ['TB', 'TBC', 'TBM', 'TBA'] and not is_gestao and not is_fup
        is_abs = st_val in ['VAGA', 'FT', 'LM', 'FR', 'FALTA', 'FÉRIAS', 'LICENÇA MÉDICA']
        is_folga = st_val in ['FG', 'BH', 'FOLGA']
        
        cr = 0
        if is_trabalho: cr = 4 if grupo == 'SÃO PAULO' else 3
            
        return pd.Series([st_val, grupo, is_trabalho, is_abs, is_folga, cr, is_gestao])

    df_long[['ST_LIMPO', 'Grupo_Regiao', 'Is_Ativo', 'Is_Abs', 'Is_Folga', 'CR', 'Is_Gestao']] = df_long.apply(mapear_status, axis=1)
    return df_long

def style_status(val):
    if not isinstance(val, str): return ''
    v = val.upper().strip()
    bg = "transparent"
    if any(x in v for x in ['TB', 'TBC', 'TBM', 'TBA', 'FUP']): bg = "#e2efda"
    elif 'FG' in v or 'BH' in v: bg = "#5b9bd5"
    elif 'LM' in v or 'LICENÇA MÉDICA' in v: bg = "#00ffff"
    elif 'FT' in v or 'FALTA' in v: bg = "#ff0000"
    elif 'FR' in v or 'FÉRIAS' in v: bg = "#cc99ff"
    elif 'TR' in v: bg = "#ffeb3b"
    elif 'PV' in v: bg = "#c5e0b4"
    return f'background-color: {bg}; color: black; font-weight: bold; border: 0.1px solid #ddd;'

# 3. INTERFACE PRINCIPAL
arquivo = st.sidebar.file_uploader("📂 Suba a Planilha ESCALA 2026", type=['xlsx'])

if arquivo:
    df_base = processar_excel(arquivo)
    menu = st.sidebar.radio("Navegação:", ["📈 Painel de Produtividade", "📅 Escala Semanal", "📆 Escala Mensal", "🗓️ Escala Anual", "👤 Área do Técnico", "📋 Espelho de Ponto"])
    data_sel = st.sidebar.date_input("Data de referência:", df_base['Data'].min())
    
    # --- VISÃO 1: PAINEL DE PRODUTIVIDADE (COMPLETO) ---
    if menu == "📈 Painel de Produtividade":
        st.title(f"📊 Dashboard Operacional - {data_sel.strftime('%d/%m/%Y')}")
        df_dia = df_base[df_base['Data'].dt.date == data_sel]
        df_dash = df_dia[df_dia['Is_Gestao'] == False]
        c_res, c_det = st.columns([1, 2.5])
        with c_res:
            st.markdown('<div class="header-abs">INDICADORES DE EQUIPE</div>', unsafe_allow_html=True)
            v = len(df_dash[df_dash['ST_LIMPO'] == 'VAGA'])
            f = len(df_dash[df_dash['ST_LIMPO'].isin(['FT', 'FALTA'])])
            l = len(df_dash[df_dash['ST_LIMPO'].isin(['LM', 'LICENÇA MÉDICA'])])
            fr = len(df_dash[df_dash['ST_LIMPO'].isin(['FR', 'FÉRIAS'])])
            st.markdown(f'<div class="metric-row header-abs">TOTAL ABSENTEÍSMO! <span>{v+f+l+fr}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row vaga">VAGA <span>{v}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row falta">FALTA <span>{f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row lm">LICENÇA MÉDICA <span>{l}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row ferias">FÉRIAS <span>{fr}</span></div>', unsafe_allow_html=True)
            folgas = int(df_dash['Is_Folga'].sum())
            tr = len(df_dash[df_dash['ST_LIMPO'].isin(['TR', 'TREINAMENTO'])])
            pv = len(df_dash[df_dash['ST_LIMPO'] == 'PV'])
            ativos = int(df_dash['Is_Ativo'].sum())
            st.markdown(f'<div class="metric-row folga">FOLGA / BH <span>{folgas}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row tr">TREINAMENTO <span>{tr}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row pv">PREVENTIVA <span>{pv}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row trabalhando">EQUIPE TRABALHANDO <span>{ativos}</span></div>', unsafe_allow_html=True)
            hc_dia = len(df_dash) - folgas
            pct = (ativos / hc_dia * 100) if hc_dia > 0 else 0
            st.markdown(f'<div class="metric-row headcount">HC TOTAL DO DIA <span>{hc_dia}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row headcount">HC DIA ATIVO <span>{ativos}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row headcount">% EQUIPE ATIVA <span>{pct:.1f}%</span></div>', unsafe_allow_html=True)
        with c_det:
            total_cr = int(df_dash['CR'].sum())
            st.markdown(f'<div class="metric-row produtividade">PRODUTIVIDADE TOTAL (CAPACITY) <span>{total_cr}</span></div>', unsafe_allow_html=True)
            for label, busca in [('SÃO PAULO', 'SÃO PAULO'), ('INTERIOR', 'INTERIOR'), ('SUL', 'SUL'), ('NORDESTE', 'NORDESTE')]:
                df_reg = df_dash[
