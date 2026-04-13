import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import calendar

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Command Center - Field Service McDonalds", layout="wide")

# CSS PARA MÁXIMO CONTRASTE E FIDELIDADE AO LAYOUT EXCEL
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

# 2. PROCESSAMENTO DE DADOS
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

# 3. INTERFACE
arquivo = st.sidebar.file_uploader("📂 Suba a Planilha ESCALA 2026", type=['xlsx'])

if arquivo:
    df_base = processar_excel(arquivo)
    menu = st.sidebar.radio("Navegação:", ["📈 Painel de Produtividade", "📅 Escala Semanal", "📆 Escala Mensal", "🗓️ Escala Anual", "👤 Área do Técnico", "📋 Espelho de Ponto"])
    data_sel = st.sidebar.date_input("Data de referência:", df_base['Data'].min())
    
    if menu == "📈 Painel de Produtividade":
        st.title(f"📊 Dashboard Operacional - {data_sel.strftime('%d/%m/%Y')}")
        df_dia = df_base[df_base['Data'].dt.date == data_sel]
        df_dash = df_dia[df_dia['Is_Gestao'] == False]
        c_res, c_det = st.columns([1, 2.5])
        with c_res:
            st.markdown('<div class="header-abs">INDICADORES DE EQUIPE</div>', unsafe_allow_html=True)
            v = len(df_dash[df_dash['ST_LIMPO'] == 'VAGA']); f = len(df_dash[df_dash['ST_LIMPO'].isin(['FT', 'FALTA'])])
            l = len(df_dash[df_dash['ST_LIMPO'].isin(['LM', 'LICENÇA MÉDICA'])]); fr = len(df_dash[df_dash['ST_LIMPO'].isin(['FR', 'FÉRIAS'])])
            st.markdown(f'<div class="metric-row header-abs">TOTAL ABSENTEÍSMO! <span>{v+f+l+fr}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row vaga">VAGA <span>{v}</span></div>', unsafe_allow_html=True); st.markdown(f'<div class="metric-row falta">FALTA <span>{f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row lm">LICENÇA MÉDICA <span>{l}</span></div>', unsafe_allow_html=True); st.markdown(f'<div class="metric-row ferias">FÉRIAS <span>{fr}</span></div>', unsafe_allow_html=True)
            folgas = int(df_dash['Is_Folga'].sum()); tr = len(df_dash[df_dash['ST_LIMPO'].isin(['TR', 'TREINAMENTO'])]); pv = len(df_dash[df_dash['ST_LIMPO'] == 'PV']); ativos = int(df_dash['Is_Ativo'].sum())
            st.markdown(f'<div class="metric-row folga">FOLGA / BH <span>{folgas}</span></div>', unsafe_allow_html=True); st.markdown(f'<div class="metric-row tr">TREINAMENTO <span>{tr}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row pv">PREVENTIVA <span>{pv}</span></div>', unsafe_allow_html=True); st.markdown(f'<div class="metric-row trabalhando">EQUIPE TRABALHANDO <span>{ativos}</span></div>', unsafe_allow_html=True)
            hc_dia = len(df_dash) - folgas; pct = (ativos / hc_dia * 100) if hc_dia > 0 else 0
            st.markdown(f'<div class="metric-row headcount">HC TOTAL DO DIA <span>{hc_dia}</span></div>', unsafe_allow_html=True); st.markdown(f'<div class="metric-row headcount">HC DIA ATIVO <span>{ativos}</span></div>', unsafe_allow_html=True); st.markdown(f'<div class="metric-row headcount">% EQUIPE ATIVA <span>{pct:.1f}%</span></div>', unsafe_allow_html=True)
        with c_det:
            total_cr = int(df_dash['CR'].sum())
            st.markdown(f'<div class="metric-row produtividade">PRODUTIVIDADE TOTAL (CAPACITY) <span>{total_cr}</span></div>', unsafe_allow_html=True)
            for label, busca in [('SÃO PAULO', 'SÃO PAULO'), ('INTERIOR', 'INTERIOR'), ('SUL', 'SUL'), ('NORDESTE', 'NORDESTE')]:
                df_r = df_dash[df_dash['Grupo_Regiao'] == busca]
                h_r, c_r = int(df_r['Is_Ativo'].sum()), int(df_r['CR'].sum())
                ca, cb, cc = st.columns([1.2, 1, 1])
                ca.markdown(f'<div class="metric-row folga">HEADCOUNT {label} <span>{h_r}</span></div>', unsafe_allow_html=True)
                cb.markdown(f'<div class="metric-row headcount">CALL RATE {label} <span>{c_r}</span></div>', unsafe_allow_html=True)
                cc.markdown(f'<div class="metric-row tr">% CALL RATE {label} <span>{(c_r/total_cr*100 if total_cr>0 else 0):.1f}%</span></div>', unsafe_allow_html=True)
            st.divider(); st.subheader("📍 Monitoramento Sub-regiões SP (Degrade)")
            sub_sp = {"SP-CENTRO": 4, "SP-LESTE": 8, "SP-NORTE": 6, "SP-OESTE": 8, "SP-SUL": 7, "SP-ABC": 4}
            def get_color(at, mt):
                ratio = at/mt if mt > 0 else 0
                if ratio >= 1.0: return "#c8e6c9", "✅"
                if ratio >= 0.5: return "#fff9c4", "⚠️"
                return "#ffcdd2", "🚨"
            c_sp = st.columns(3)
            for i, (sub, meta) in enumerate(sub_sp.items()):
                val = int(df_dash[(df_dash['Grupo_Regiao'] == 'SÃO PAULO') & (df_dash['Regiao'].str.contains(sub))]['Is_Ativo'].sum())
                bg, icon = get_color(val, meta)
                c_sp[i%3].markdown(f'<div class="sub-sp-card" style="background-color: {bg};"><span>{icon} {sub}</span><span>{val} / {meta}</span></div>', unsafe_allow_html=True)

    elif menu == "📅 Escala Semanal":
        data_ini = st.sidebar.date_input("Início da semana:", data_sel)
        df_s = df_base[(df_base['Data'].dt.date >= data_ini) & (df_base['Data'].dt.date <= data_ini + timedelta(days=6))]
        df_p = df_s.pivot(index=['ID', 'Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status').sort_index(level='ID')
        df_p.columns = [f"{d.strftime('%a %d/%m')}" for d in df_p.columns]
        st.dataframe(df_p.style.map(style_status), use_container_width=True)

    elif menu == "📆 Escala Mensal":
        mes_sel = st.sidebar.slider("Mês:", 1, 12, int(data_sel.month))
        df_m = df_base[df_base['Data'].dt.month == mes_sel]
        df_p = df_m.pivot(index=['ID', 'Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status').sort_index(level='ID')
        df_p.columns = [f"{d.strftime('%d/%m')}" for d in df_p.columns]
        st.dataframe(df_p.style.map(style_status), height=600, use_container_width=True)

    elif menu == "🗓️ Escala Anual":
        st.title("Escala Anual Completa")
        df_anual = df_base.pivot(index=['ID', 'Regiao', 'Tecnico'], columns='Data', values='Status').sort_index(level='ID')
        st.dataframe(df_anual.style.map(style_status), height=600)

    elif menu == "👤 Área do Técnico":
    st.title("Meu Calendário Mensal")
    tec_escolha = st.selectbox("Busque seu nome:", sorted(df_base['Tecnico'].unique()))
    mes_escolha = st.selectbox("Escolha o Mês:", range(1, 13), index=int(data_sel.month)-1, format_func=lambda x: calendar.month_name[x])

    # Garantir que o calendário começa na segunda-feira
    calendar.setfirstweekday(calendar.MONDAY)

    # Pegar o ano da data selecionada (ou o máximo do DF)
    ano_atual = int(data_sel.year)

    # Gerar matriz do mês
    cal_matriz = calendar.monthcalendar(ano_atual, mes_escolha)
    df_grid = pd.DataFrame(cal_matriz, columns=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']).astype(object)

    # Filtrar dados do técnico para o mês
    df_tec_mes = df_base[(df_base['Tecnico'] == tec_escolha) & (df_base['Data'].dt.month == mes_escolha) & (df_base['Data'].dt.year == ano_atual)]

    # Preencher a matriz com status
    for r in range(len(df_grid)):
        for c in range(7):
            dia_num = df_grid.iloc[r, c]
            if dia_num != 0:
                dia_match = df_tec_mes[df_tec_mes['Data'].dt.day == dia_num]
                status = str(dia_match['Status'].values[0]) if not dia_match.empty else "---"
                df_grid.iloc[r, c] = f"{dia_num} - {status}"
            else:
                df_grid.iloc[r, c] = ""

    st.table(df_grid.style.map(style_status))

    elif menu == "📋 Espelho de Ponto":
        tec_ponto = st.selectbox("Técnico:", sorted(df_base['Tecnico'].unique()))
        mes_f = st.sidebar.selectbox("Mês Ponto (Dia 27):", range(1, 13), index=int(data_sel.month)-1)
        hoje = datetime(2026, mes_f, 27)
        inicio = (hoje - timedelta(days=31)).replace(day=28)
        df_ponto = df_base[(df_base['Tecnico'] == tec_ponto) & (df_base['Data'].dt.date >= inicio.date()) & (df_base['Data'].dt.date <= hoje.date())]
        df_ponto['Dia'] = df_ponto['Data'].dt.strftime('%a %d/%m')
        st.table(df_ponto[['Dia', 'Status']].set_index('Dia').style.map(style_status))
else:
    st.info("👋 Suba a planilha de escala para ativar o sistema.")
