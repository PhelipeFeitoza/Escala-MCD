import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import calendar

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Command Center - Field Service", layout="wide")

# CSS Ajustado para textos longos e máximo contraste
st.markdown("""
<style>
    .metric-row { 
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        padding: 8px 15px; 
        border-bottom: 1px solid #ccc; 
        font-weight: 800; 
        color: black !important; 
        font-size: 13px;
        margin-bottom: 2px;
        border-radius: 4px;
    }
    .header-abs { background-color: #f4b084; text-align: center; font-weight: 900; font-size: 16px; padding: 10px; }
    .vaga { background-color: #d9d9d9; } 
    .falta { background-color: #ff5252; }
    .lm { background-color: #9bc2e6; } 
    .ferias { background-color: #c5e0b4; }
    .folga { background-color: #8faadc; } 
    .bh { background-color: #fff2cc; }
    .tr { background-color: #ffe699; } 
    .pv { background-color: #e2efda; }
    .trabalhando { background-color: #a9d08e; } 
    .headcount { background-color: #ffd966; }
    .produtividade { background-color: #7030a0; color: white !important; font-size: 18px; padding: 12px; }
    .sub-sp { background-color: #e2efda; font-size: 0.9em; border: 1px solid #999; }
    .reg-container { margin-bottom: 20px; border: 1px solid #ddd; padding: 5px; border-radius: 8px; background-color: #fdfdfd; }
</style>
""", unsafe_allow_html=True)

# 2. PROCESSAMENTO (MANTIDA A LÓGICA QUE FUNCIONOU)
@st.cache_data
def processar_excel(file):
    df = pd.read_excel(file, engine='openpyxl')
    info_cols = df.iloc[:, [0, 2, 3, 4]].copy()
    info_cols.columns = ['ID', 'Regiao', 'Horario', 'Tecnico']
    
    for col in ['Regiao', 'Tecnico']:
        info_cols[col] = info_cols[col].astype(str).str.upper().str.strip()
    
    datas_cols = df.iloc[:, 5:]
    df_unido = pd.concat([info_cols, datas_cols], axis=1)
    df_long = df_unido.melt(id_vars=['ID', 'Regiao', 'Horario', 'Tecnico'], var_name='Data_Bruta', value_name='Status')
    df_long['Data'] = pd.to_datetime(df_long['Data_Bruta'], errors='coerce')
    df_long = df_long.dropna(subset=['Data'])
    
    def mapear_total(row):
        st_val = str(row['Status']).upper().strip()
        reg = str(row['Regiao'])
        nome = str(row['Tecnico'])
        
        if 'INT-' in reg or 'INTERIOR' in reg: grupo = 'INTERIOR'
        elif 'NOR-' in reg: grupo = 'NORDESTE'
        elif 'SUL-' in reg: grupo = 'SUL'
        elif 'SP-' in reg: grupo = 'SÃO PAULO'
        else: grupo = 'OUTROS'
        
        is_gestao = any(x in nome for x in ['SUPERVISOR', 'N3', 'COORDENADOR', 'GESTOR'])
        is_fup = st_val == 'FUP'
        is_trabalho = st_val in ['TBC', 'TBM', 'TBA'] and not is_gestao and not is_fup
        is_abs = st_val in ['VAGA', 'FT', 'LM', 'FR', 'FALTA', 'FÉRIAS', 'LICENÇA MÉDICA']
        
        cr = 0
        if is_trabalho:
            cr = 4 if grupo == 'SÃO PAULO' else 3
            
        return pd.Series([st_val, grupo, is_trabalho, is_abs, cr, is_gestao])

    df_long[['ST_LIMPO', 'Grupo_Regiao', 'Is_Ativo', 'Is_Abs', 'CR', 'Is_Gestao']] = df_long.apply(mapear_total, axis=1)
    return df_long

# 3. INTERFACE
arquivo = st.sidebar.file_uploader("📂 Planilha ESCALA 2026", type=['xlsx'])

if arquivo:
    df_base = processar_excel(arquivo)
    menu = st.sidebar.radio("Navegação:", ["📈 Painel de Produtividade", "📅 Escala Mensal", "👤 Área do Técnico", "📋 Espelho de Ponto"])
    data_sel = st.sidebar.date_input("Dia para análise:", datetime(2026, 4, 13))
    
    df_dia = df_base[(df_base['Data'].dt.date == data_sel)]

    if menu == "📈 Painel de Produtividade":
        st.title(f"📊 Dashboard de Produtividade - {data_sel.strftime('%d/%m/%Y')}")
        
        c_resumo, c_detalhe = st.columns([1, 2.5]) # Aumentei o espaço do detalhe
        
        with c_resumo:
            st.markdown('<div class="header-abs">INDICADORES DE EQUIPE</div>', unsafe_allow_html=True)
            df_dash = df_dia[df_dia['Is_Gestao'] == False]
            
            # Absenteísmo
            vagas = len(df_dash[df_dash['ST_LIMPO'] == 'VAGA'])
            faltas = len(df_dash[df_dash['ST_LIMPO'].isin(['FT', 'FALTA'])])
            lm = len(df_dash[df_dash['ST_LIMPO'].isin(['LM', 'LICENÇA MÉDICA'])])
            ferias = len(df_dash[df_dash['ST_LIMPO'].isin(['FR', 'FÉRIAS'])])
            total_abs = vagas + faltas + lm + ferias
            
            st.markdown(f'<div class="metric-row header-abs">TOTAL ABSENTEÍSMO! <span>{total_abs}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row vaga">VAGA <span>{vagas}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row falta">FALTA <span>{faltas}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row lm">LICENÇA MÉDICA <span>{lm}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row ferias">FÉRIAS <span>{ferias}</span></div>', unsafe_allow_html=True)
            
            # Operacional
            folgas = len(df_dash[df_dash['ST_LIMPO'].isin(['FG', 'FOLGA'])])
            bh = len(df_dash[df_dash['ST_LIMPO'] == 'BH'])
            tr = len(df_dash[df_dash['ST_LIMPO'].isin(['TR', 'TREINAMENTO'])])
            pv = len(df_dash[df_dash['ST_LIMPO'] == 'PV'])
            ativos = int(df_dash['Is_Ativo'].sum())
            
            st.markdown(f'<div class="metric-row folga">FOLGA <span>{folgas}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row bh">BANCO DE HORAS <span>{bh}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row tr">TREINAMENTO <span>{tr}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row pv">PREVENTIVA <span>{pv}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row trabalhando">EQUIPE TRABALHANDO <span>{ativos}</span></div>', unsafe_allow_html=True)
            
            # Headcounts
            hc_total_dia = len(df_dash) - folgas - bh
            pct_ativa = (ativos / hc_total_dia * 100) if hc_total_dia > 0 else 0
            st.markdown(f'<div class="metric-row headcount">HEADCOUNT TOTAL DO DIA <span>{hc_total_dia}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row headcount">HEADCOUNT DIA ATIVO <span>{ativos}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row headcount">% EQUIPE ATIVA <span>{pct_ativa:.1f}%</span></div>', unsafe_allow_html=True)

        with c_detalhe:
            # PRODUTIVIDADE TOTAL
            total_cr = int(df_dash['CR'].sum())
            st.markdown(f'<div class="metric-row produtividade">PRODUTIVIDADE TOTAL (CAPACITY) <span>{total_cr}</span></div>', unsafe_allow_html=True)
            
            # Listagem Regional com nomes completos e sem cortes
            regionais = [('SÃO PAULO', 'SÃO PAULO'), ('INTERIOR', 'INTERIOR'), ('SUL', 'SUL'), ('NORDESTE', 'NORDESTE')]
            
            for label, busca in regionais:
                df_reg = df_dash[df_dash['Grupo_Regiao'] == busca]
                h_reg = int(df_reg['Is_Ativo'].sum())
                c_reg = int(df_reg['CR'].sum())
                p_reg = (c_reg / total_cr * 100) if total_cr > 0 else 0
                
                # Container para cada regional
                with st.container():
                    col_a, col_b, col_c = st.columns([1.2, 1, 1])
                    col_a.markdown(f'<div class="metric-row folga">HEADCOUNT {label} <span>{h_reg}</span></div>', unsafe_allow_html=True)
                    col_b.markdown(f'<div class="metric-row headcount">CALL RATE {label} <span>{c_reg}</span></div>', unsafe_allow_html=True)
                    col_c.markdown(f'<div class="metric-row tr">% CALL RATE {label} <span>{p_reg:.1f}%</span></div>', unsafe_allow_html=True)

            st.divider()
            st.subheader("📍 Monitoramento Sub-regiões São Paulo")
            sub_sp = {"SP-CENTRO": 4, "SP-LESTE": 8, "SP-NORTE": 6, "SP-OESTE": 8, "SP-SUL": 7, "SP-ABC": 4}
            cols_sp = st.columns(3)
            for i, (sub, meta) in enumerate(sub_sp.items()):
                val_sub = int(df_dash[(df_dash['Grupo_Regiao'] == 'SÃO PAULO') & (df_dash['Regiao'].str.contains(sub))]['Is_Ativo'].sum())
                icon = "✅" if val_sub >= meta else "⚠️" if val_sub > 0 else "❌"
                cols_sp[i%3].markdown(f'<div class="metric-row sub-sp">{icon} {sub} <span>{val_sub} / {meta}</span></div>', unsafe_allow_html=True)

    # --- AS DEMAIS VISÕES CONTINUAM ATIVAS ---
    elif menu == "📅 Escala Mensal":
        mes = st.sidebar.slider("Mês", 1, 12, 4)
        df_m = df_base[df_base['Data'].dt.month == mes]
        df_p = df_m.pivot(index=['ID', 'Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status').sort_index(level='ID')
        st.dataframe(df_p, height=600)
