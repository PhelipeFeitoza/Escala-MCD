import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import calendar

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Command Center - Field Service McDonalds", layout="wide")

# CSS CUSTOMIZADO PARA CORES E CONTRASTE
st.markdown("""
<style>
    .metric-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 15px; border-bottom: 1px solid #ccc; font-weight: 800; color: black !important; font-size: 13px; margin-bottom: 2px; border-radius: 4px; }
    .header-abs { background-color: #f4b084; text-align: center; font-weight: 900; font-size: 16px; padding: 10px; color: black !important; }
    .vaga { background-color: #d9d9d9; } .falta { background-color: #ff5252; }
    .lm { background-color: #9bc2e6; } .ferias { background-color: #c5e0b4; }
    .folga { background-color: #8faadc; } .bh { background-color: #fff2cc; }
    .tr { background-color: #ffe699; } .pv { background-color: #e2efda; }
    .trabalhando { background-color: #a9d08e; } .headcount { background-color: #ffd966; }
    .produtividade { background-color: #7030a0; color: white !important; font-size: 18px; padding: 12px; }
    .sub-sp-card { padding: 12px; border-radius: 8px; border: 1px solid #999; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: black !important; font-weight: 900; }
</style>
""", unsafe_allow_html=True)

# 2. PROCESSAMENTO DE DADOS (LÓGICA BLINDADA)
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
        
        # Identificação de Regional
        if 'INT-' in reg or 'INTERIOR' in reg: grupo = 'INTERIOR'
        elif 'NOR-' in reg: grupo = 'NORDESTE'
        elif 'SUL-' in reg: grupo = 'SUL'
        elif 'SP-' in reg: grupo = 'SÃO PAULO'
        else: grupo = 'OUTROS'
        
        # Regras de Exclusão
        is_gestao = any(x in nome for x in ['SUPERVISOR', 'N3', 'COORDENADOR', 'GESTOR'])
        is_fup = st_val == 'FUP'
        
        # Trabalho Ativo (TBC, TBM, TBA)
        is_trabalho = st_val in ['TBC', 'TBM', 'TBA'] and not is_gestao and not is_fup
        is_abs = st_val in ['VAGA', 'FT', 'LM', 'FR', 'FALTA', 'FÉRIAS', 'LICENÇA MÉDICA']
        
        cr = 0
        if is_trabalho:
            cr = 4 if grupo == 'SÃO PAULO' else 3
            
        return pd.Series([st_val, grupo, is_trabalho, is_abs, cr, is_gestao])

    df_long[['ST_LIMPO', 'Grupo_Regiao', 'Is_Ativo', 'Is_Abs', 'CR', 'Is_Gestao']] = df_long.apply(mapear_total, axis=1)
    return df_long

def style_status(val):
    if not isinstance(val, str): return ''
    v = val.upper()
    bg = "transparent"
    if any(s in v for s in ['TBC', 'TBM', 'TBA', 'FUP']): bg = "#C8E6C9"
    elif 'FG' in v or 'BH' in v: bg = "#BBDEFB"
    elif 'LM' in v or 'FT' in v: bg = "#FFCDD2"
    elif 'TR' in v: bg = "#FFE699"
    elif 'PV' in v: bg = "#E2EFDA"
    return f'background-color: {bg}; color: black; font-weight: bold; border: 0.1px solid #ddd;'

# 3. INTERFACE PRINCIPAL
arquivo = st.sidebar.file_uploader("📂 Suba a Planilha ESCALA 2026", type=['xlsx'])

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
    
    data_sel = st.sidebar.date_input("Data de Análise:", datetime(2026, 4, 13))
    df_dia = df_base[df_base['Data'].dt.date == data_sel]
    df_dash = df_dia[df_dia['Is_Gestao'] == False]

    # --- VISÃO 1: PAINEL DE PRODUTIVIDADE ---
    if menu == "📈 Painel de Produtividade":
        st.title(f"📊 Dashboard Operacional - {data_sel.strftime('%d/%m/%Y')}")
        c_resumo, c_detalhe = st.columns([1, 2.5])
        
        with c_resumo:
            st.markdown('<div class="header-abs">INDICADORES DE EQUIPE</div>', unsafe_allow_html=True)
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
            
            folgas = len(df_dash[df_dash['ST_LIMPO'].isin(['FG', 'FOLGA'])])
            bh = len(df_dash[df_dash['ST_LIMPO'] == 'BH'])
            ativos = int(df_dash['Is_Ativo'].sum())
            
            st.markdown(f'<div class="metric-row folga">FOLGA <span>{folgas}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row bh">BANCO DE HORAS <span>{bh}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row trabalhando">EQUIPE TRABALHANDO <span>{ativos}</span></div>', unsafe_allow_html=True)
            
            hc_total_dia = len(df_dash) - folgas - bh
            pct_ativa = (ativos / hc_total_dia * 100) if hc_total_dia > 0 else 0
            st.markdown(f'<div class="metric-row headcount">HEADCOUNT TOTAL DO DIA <span>{hc_total_dia}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row headcount">HEADCOUNT DIA ATIVO <span>{ativos}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row headcount">% EQUIPE ATIVA <span>{pct_ativa:.1f}%</span></div>', unsafe_allow_html=True)

        with c_detalhe:
            total_cr = int(df_dash['CR'].sum())
            st.markdown(f'<div class="metric-row produtividade">PRODUTIVIDADE TOTAL (CAPACITY) <span>{total_cr}</span></div>', unsafe_allow_html=True)
            for label, busca in [('SÃO PAULO', 'SÃO PAULO'), ('INTERIOR', 'INTERIOR'), ('SUL', 'SUL'), ('NORDESTE', 'NORDESTE')]:
                df_reg = df_dash[df_dash['Grupo_Regiao'] == busca]
                h_reg, c_reg = int(df_reg['Is_Ativo'].sum()), int(df_reg['CR'].sum())
                p_reg = (c_reg / total_cr * 100) if total_cr > 0 else 0
                ca, cb, cc = st.columns([1.2, 1, 1])
                ca.markdown(f'<div class="metric-row folga">HEADCOUNT {label} <span>{h_reg}</span></div>', unsafe_allow_html=True)
                cb.markdown(f'<div class="metric-row headcount">CALL RATE {label} <span>{c_reg}</span></div>', unsafe_allow_html=True)
                cc.markdown(f'<div class="metric-row tr">% CALL RATE {label} <span>{p_reg:.1f}%</span></div>', unsafe_allow_html=True)

            st.divider()
            st.subheader("📍 Monitoramento Sub-regiões São Paulo")
            
            # Definição das metas
            sub_sp = {"SP-CENTRO": 4, "SP-LESTE": 8, "SP-NORTE": 6, "SP-OESTE": 8, "SP-SUL": 7, "SP-ABC": 4}
            
            # Função para calcular a cor do degrade baseada na meta
            def get_color_gradient(atual, meta):
                percent = (atual / meta) if meta > 0 else 0
                if percent >= 1.0: return "#c8e6c9", "✅" # Verde Sólido
                if percent >= 0.75: return "#e8f5e9", "💡" # Verde Água/Claro
                if percent >= 0.50: return "#fff9c4", "⚠️" # Amarelo
                if percent >= 0.25: return "#ffe0b2", "🟠" # Laranja
                return "#ffcdd2", "🚨" # Vermelho (Crítico)

            cols_sp = st.columns(3)
            
            # Ordenando as sub-regiões para visualização
            for i, (sub, meta) in enumerate(sub_sp.items()):
                # Filtro preciso: Somente técnicos do grupo SP que contenham a sub-região no nome
                val_sub = int(df_dash[(df_dash['Grupo_Regiao'] == 'SÃO PAULO') & 
                                      (df_base['Regiao'].str.contains(sub))]['Is_Ativo'].sum())
                
                # Obtem cor e ícone baseados no desempenho
                bg_color, icon = get_color_gradient(val_sub, meta)
                
                # Renderização do Card com degrade
                cols_sp[i%3].markdown(f"""
                <div style="
                    background-color: {bg_color}; 
                    padding: 12px; 
                    border-radius: 8px; 
                    border: 1px solid #999; 
                    margin-bottom: 10px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
                ">
                    <span style="color: black; font-weight: 900; font-size: 13px;">{icon} {sub}</span>
                    <span style="color: black; font-weight: 900; font-size: 14px;">{val_sub} / {meta}</span>
                </div>
                """, unsafe_allow_html=True)

    # --- VISÃO 2: SEMANAL ---
    elif menu == "📅 Escala Semanal":
        st.title("Escala Semanal")
        data_ini = st.sidebar.date_input("Início da semana:", datetime(2026, 4, 13))
        df_s = df_base[(df_base['Data'].dt.date >= data_ini) & (df_base['Data'].dt.date <= data_ini + timedelta(days=6))]
        df_p = df_s.pivot(index=['ID', 'Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status').sort_index(level='ID')
        df_p.columns = [f"{d.strftime('%a %d/%m')}" for d in df_p.columns]
        st.dataframe(df_p.style.map(style_status), use_container_width=True)

    # --- VISÃO 3: MENSAL ---
    elif menu == "📆 Escala Mensal":
        mes = st.sidebar.slider("Mês", 1, 12, 4)
        df_m = df_base[df_base['Data'].dt.month == mes]
        df_p = df_m.pivot(index=['ID', 'Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status').sort_index(level='ID')
        df_p.columns = [f"{d.strftime('%d/%m')}" for d in df_p.columns]
        st.dataframe(df_p.style.map(style_status), height=600)

    # --- VISÃO 4: ANUAL ---
    elif menu == "🗓️ Escala Anual":
        st.title("Escala Anual Completa")
        df_p = df_base.pivot(index=['ID', 'Regiao', 'Tecnico'], columns='Data', values='Status').sort_index(level='ID')
        st.dataframe(df_p.style.map(style_status), height=600)

    # --- VISÃO 5: CALENDÁRIO TÉCNICO ---
    elif menu == "👤 Área do Técnico":
        tec = st.selectbox("Selecione seu Nome:", sorted(df_base['Tecnico'].unique()))
        mes = st.selectbox("Mês:", range(1, 13), index=3, format_func=lambda x: calendar.month_name[x])
        cal = calendar.monthcalendar(2026, mes)
        df_cal = pd.DataFrame(cal, columns=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']).astype(object)
        for r in range(len(df_cal)):
            for c in range(7):
                dia = df_cal.iloc[r, c]
                if dia != 0:
                    dt = datetime(2026, mes, dia)
                    res = df_base[(df_base['Tecnico'] == tec) & (df_base['Data'] == dt)]['Status'].values
                    df_cal.iloc[r, c] = f"{dia} - {res[0]}" if len(res)>0 else f"{dia}"
                else: df_cal.iloc[r, c] = ""
        st.table(df_cal.style.map(style_status))

    # --- VISÃO 6: ESPELHO DE PONTO ---
    elif menu == "📋 Espelho de Ponto":
        tec = st.selectbox("Técnico:", sorted(df_base['Tecnico'].unique()))
        mes_f = st.sidebar.selectbox("Mês de Fechamento (Fim dia 27):", range(1, 13), index=3)
        fim = datetime(2026, mes_f, 27)
        ini = (fim - timedelta(days=30)).replace(day=28)
        df_p = df_base[(df_base['Data'] >= ini) & (df_base['Data'] <= fim) & (df_base['Tecnico'] == tec)].copy()
        df_p['Dia'] = df_p['Data'].dt.strftime('%a %d/%m')
        st.table(df_p[['Dia', 'Status']].set_index('Dia').style.map(style_status))

else:
    st.info("Suba a planilha de escala para ativar o Command Center.")
