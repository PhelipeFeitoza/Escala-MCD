import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import calendar

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Command Center - Field Service McDonalds", layout="wide")

# 2. ESTILIZAÇÃO E PALETA DE CORES (CONFORME LEGENDA)
st.markdown("""
<style>
    .metric-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 15px; border-bottom: 1px solid #ccc; font-weight: 800; color: black !important; font-size: 13px; border-radius: 4px; }
    .header-abs { background-color: #f4b084; text-align: center; font-weight: 900; font-size: 16px; padding: 10px; color: black !important; border: 1px solid #333; }
    .produtividade { background-color: #7030a0; color: white !important; font-size: 18px; padding: 12px; border-radius: 5px; text-align: center; }
    .sub-sp-card { padding: 10px; border-radius: 8px; border: 1px solid #777; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; color: black !important; font-weight: 900; font-size: 12px; }
    /* Estilo para tabelas e dataframes */
    .stTable td { font-weight: bold !important; color: black !important; }
</style>
""", unsafe_allow_html=True)

def style_status(val):
    if not isinstance(val, str): return ''
    v = val.upper().strip()
    bg = "#ffffff" # Default
    color = "black"
    
    # Cores baseadas na paleta do print "LEGENDA"
    if v == 'VAGA': bg = "#d9d9d9"
    elif v == 'FT': bg = "#ff0000"; color = "black"
    elif v == 'LM': bg = "#00ffff" # Cyan/Light Blue
    elif v == 'FR': bg = "#cc99ff" # Purple
    elif v == 'FG': bg = "#5b9bd5" # Steel Blue
    elif v == 'BH': bg = "#deeaf6" # Very Light Blue
    elif v == 'TR': bg = "#ffeb3b" # Yellow
    elif v == 'PV': bg = "#c5e0b4" # Light Green
    elif v in ['TB', 'TBC', 'TBM', 'TBA']: bg = "#e2efda" # Sage Green
    elif v == 'TBH': bg = "#ebf1de" # Light Mint
    elif v == 'HE': bg = "#f4b084" # Orange
    elif 'TARDE' in v: bg = "#fce4d6"
    elif 'MANHÃ' in v: bg = "#fff2cc"
    elif 'FUP' in v: bg = "#e2efda" # Segue cor de trabalho
    
    return f'background-color: {bg}; color: {color}; font-weight: bold; border: 0.5px solid #999;'

# 3. LÓGICA DE PROCESSAMENTO DE DADOS
@st.cache_data
def processar_excel(file):
    df = pd.read_excel(file, engine='openpyxl')
    
    # Mapeamento A(0)=ID, C(2)=Região, D(3)=Horário, E(4)=Técnico
    info = df.iloc[:, [0, 2, 3, 4]].copy()
    info.columns = ['ID', 'Regiao', 'Horario', 'Tecnico']
    
    # Limpeza
    info['Regiao'] = info['Regiao'].astype(str).str.upper().str.strip()
    info['Tecnico'] = info['Tecnico'].astype(str).str.strip()
    
    # Transformação de colunas de data em linhas
    datas_cols = df.iloc[:, 5:]
    df_long = pd.concat([info, datas_cols], axis=1).melt(
        id_vars=['ID', 'Regiao', 'Horario', 'Tecnico'], 
        var_name='Data_Original', value_name='Status'
    )
    
    # Garantir que a coluna Data seja datetime pura
    df_long['Data'] = pd.to_datetime(df_long['Data_Original'], errors='coerce')
    df_long = df_long.dropna(subset=['Data'])
    
    # Mapeamento de Regras de Negócio
    def aplicar_regras(row):
        st_val = str(row['Status']).upper().strip()
        reg = str(row['Regiao'])
        nome = str(row['Tecnico']).upper()
        
        # 1. Grupo de Regional (Filtro por Prefixo)
        if reg.startswith('INT-') or 'INTERIOR' in reg: grupo = 'INTERIOR'
        elif reg.startswith('NOR-'): grupo = 'NORDESTE'
        elif reg.startswith('SUL-'): grupo = 'SUL'
        elif reg.startswith('SP-'): grupo = 'SÃO PAULO'
        else: grupo = 'OUTROS'
        
        # 2. Exclusões de Gestão/Cargos (Somente time técnico conta para HC Ativo)
        is_excluido = any(x in nome for x in ['SUPERVISOR', 'N3', 'COORDENADOR', 'GESTOR', 'BACKOFFICE'])
        is_fup = (st_val == 'FUP')
        
        # 3. Status Ativo (Trabalho em Campo)
        # TB, TBC, TBM, TBA contam. TBH (Home) não conta no HC Ativo de campo.
        is_ativo = st_val in ['TB', 'TBC', 'TBM', 'TBA'] and not is_excluido and not is_fup
        
        # 4. Status Absenteísmo
        is_abs = st_val in ['VAGA', 'FT', 'LM', 'FR', 'FALTA', 'FÉRIAS', 'LICENÇA MÉDICA']
        
        # 5. Capacity (SP=4, Resto=3)
        cr = 0
        if is_ativo:
            cr = 4 if grupo == 'SÃO PAULO' else 3
            
        return pd.Series([st_val, grupo, is_ativo, is_abs, cr, is_excluido])

    new_cols = ['ST_LIMPO', 'Grupo_Regiao', 'Is_Ativo', 'Is_Abs', 'CR', 'Is_Gestao']
    df_long[new_cols] = df_long.apply(aplicar_regras, axis=1)
    
    return df_long

# 4. INTERFACE
arquivo = st.sidebar.file_uploader("📂 Upload Planilha ESCALA 2026", type=['xlsx'])

if arquivo:
    df_base = processar_excel(arquivo)
    
    menu = st.sidebar.radio("Navegação:", [
        "📈 Painel de Produtividade", "📅 Escala Semanal", "📆 Escala Mensal", 
        "🗓️ Escala Anual", "👤 Área do Técnico", "📋 Espelho de Ponto"
    ])
    
    data_sel = st.sidebar.date_input("Selecione o dia:", df_base['Data'].min())
    
    # --- VISÃO 1: PAINEL DE PRODUTIVIDADE ---
    if menu == "📈 Painel de Produtividade":
        st.title(f"📊 Dashboard Operacional - {data_sel.strftime('%d/%m/%Y')}")
        df_dia = df_base[df_base['Data'].dt.date == data_sel]
        df_dash = df_dia[df_dia['Is_Gestao'] == False]
        
        col_l, col_r = st.columns([1, 2.5])
        
        with col_l:
            st.markdown('<div class="header-abs">INDICADORES DE EQUIPE</div>', unsafe_allow_html=True)
            v = len(df_dash[df_dash['ST_LIMPO'] == 'VAGA'])
            f = len(df_dash[df_dash['ST_LIMPO'].isin(['FT', 'FALTA'])])
            l = len(df_dash[df_dash['ST_LIMPO'].isin(['LM', 'LICENÇA MÉDICA'])])
            fr = len(df_dash[df_dash['ST_LIMPO'].isin(['FR', 'FÉRIAS'])])
            t_abs = v + f + l + fr
            
            st.markdown(f'<div class="metric-row header-abs">TOTAL ABSENTEÍSMO! <span>{t_abs}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row vaga">VAGA <span>{v}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row falta">FALTA <span>{f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row lm">LICENÇA MÉDICA <span>{l}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row ferias">FÉRIAS <span>{fr}</span></div>', unsafe_allow_html=True)
            
            folgas = len(df_dash[df_dash['ST_LIMPO'].isin(['FG', 'FOLGA', 'BH'])])
            ativos = int(df_dash['Is_Ativo'].sum())
            hc_dia = len(df_dash) - folgas
            
            st.markdown(f'<div class="metric-row folga">FOLGA / BH <span>{folgas}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row trabalhando">EQUIPE TRABALHANDO <span>{ativos}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row headcount">HEADCOUNT TOTAL DO DIA <span>{hc_dia}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-row headcount">HEADCOUNT DIA ATIVO <span>{ativos}</span></div>', unsafe_allow_html=True)

        with col_r:
            total_cr = int(df_dash['CR'].sum())
            st.markdown(f'<div class="produtividade">PRODUTIVIDADE TOTAL (CAPACITY): {total_cr}</div>', unsafe_allow_html=True)
            
            regionais = [('SÃO PAULO', 'SÃO PAULO'), ('INTERIOR', 'INTERIOR'), ('SUL', 'SUL'), ('NORDESTE', 'NORDESTE')]
            for nome, busca in regionais:
                df_reg = df_dash[df_dash['Grupo_Regiao'] == busca]
                h = int(df_reg['Is_Ativo'].sum())
                c = int(df_reg['CR'].sum())
                p = (c / total_cr * 100) if total_cr > 0 else 0
                
                c1, c2, c3 = st.columns([1.2, 1, 1])
                c1.markdown(f'<div class="metric-row folga">HEADCOUNT {nome} <span>{h}</span></div>', unsafe_allow_html=True)
                c2.markdown(f'<div class="metric-row headcount">CALL RATE {nome} <span>{c}</span></div>', unsafe_allow_html=True)
                c3.markdown(f'<div class="metric-row tr">% CALL RATE {nome} <span>{p:.1f}%</span></div>', unsafe_allow_html=True)

            st.divider()
            st.subheader("📍 Monitoramento Sub-regiões São Paulo")
            sub_sp = {"SP-CENTRO": 4, "SP-LESTE": 8, "SP-NORTE": 6, "SP-OESTE": 8, "SP-SUL": 7, "SP-ABC": 4}
            
            def get_card_color(at, mt):
                ratio = at/mt if mt > 0 else 0
                if ratio >= 1.0: return "#c6e0b4", "✅" # Verde
                if ratio >= 0.5: return "#fff2cc", "⚠️" # Amarelo
                return "#ffcdd2", "🚨" # Vermelho
            
            c_sp = st.columns(3)
            for i, (sub, meta) in enumerate(sub_sp.items()):
                # Filtro isolado para sub-região
                val = int(df_dash[(df_dash['Grupo_Regiao'] == 'SÃO PAULO') & (df_dash['Regiao'].str.contains(sub))]['Is_Ativo'].sum())
                cor, icon = get_card_color(val, meta)
                c_sp[i%3].markdown(f'<div class="sub-sp-card" style="background-color: {cor};"><span>{icon} {sub}</span><span>{val} / {meta}</span></div>', unsafe_allow_html=True)

    # --- VISÃO 2: SEMANAL ---
    elif menu == "📅 Escala Semanal":
        st.title("Escala Semanal")
        df_p = df_base[(df_base['Data'] >= pd.Timestamp(data_sel)) & (df_base['Data'] <= pd.Timestamp(data_sel) + timedelta(days=6))]
        df_p = df_p.pivot(index=['ID', 'Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status').sort_index(level='ID')
        df_p.columns = [d.strftime('%a %d/%m') for d in df_p.columns]
        st.dataframe(df_p.style.map(style_status), use_container_width=True)

    # --- VISÃO 3: MENSAL ---
    elif menu == "📆 Escala Mensal":
        mes = st.sidebar.slider("Mês", 1, 12, int(data_sel.month))
        df_m = df_base[df_base['Data'].dt.month == mes]
        df_p = df_m.pivot(index=['ID', 'Regiao', 'Tecnico', 'Horario'], columns='Data', values='Status').sort_index(level='ID')
        df_p.columns = [d.strftime('%d/%m') for d in df_p.columns]
        st.dataframe(df_p.style.map(style_status), height=600, use_container_width=True)

    # --- VISÃO 4: ANUAL ---
    elif menu == "🗓️ Escala Anual":
        st.title("Escala Anual Completa")
        df_a = df_base.pivot(index=['ID', 'Regiao', 'Tecnico'], columns='Data', values='Status').sort_index(level='ID')
        st.dataframe(df_a.style.map(style_status), height=600)

    # --- VISÃO 5: CALENDÁRIO TÉCNICO (GRID) ---
    elif menu == "👤 Área do Técnico":
        st.title("Meu Calendário Mensal")
        tec_lista = sorted(df_base['Tecnico'].unique())
        tec_nome = st.selectbox("Selecione seu nome:", tec_lista)
        mes_f = st.selectbox("Mês:", range(1, 13), index=int(data_sel.month)-1, format_func=lambda x: calendar.month_name[x])
        
        ano = df_base['Data'].dt.year.max()
        cal_m = calendar.monthcalendar(int(ano), mes_f)
        df_grid = pd.DataFrame(cal_m, columns=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']).astype(object)
        
        for r in range(len(df_grid)):
            for c in range(7):
                dia = df_grid.iloc[r, c]
                if dia != 0:
                    # Comparação de data pura (YYYY-MM-DD)
                    data_alvo = datetime(int(ano), mes_f, dia).date()
                    match = df_base[(df_base['Tecnico'] == tec_nome) & (df_base['Data'].dt.date == data_alvo)]
                    status = match['Status'].values[0] if not match.empty else ""
                    df_grid.iloc[r, c] = f"{dia} - {status}"
                else: df_grid.iloc[r, c] = ""
        st.table(df_grid.style.map(style_status))

    # --- VISÃO 6: ESPELHO DE PONTO ---
    elif menu == "📋 Espelho de Ponto":
        tec_p = st.selectbox("Técnico:", sorted(df_base['Tecnico'].unique()))
        mes_fech = st.sidebar.selectbox("Mês de Fechamento (Dia 27):", range(1, 13), index=int(data_sel.month)-1)
        fim_p = datetime(2026, mes_fech, 27).date()
        ini_p = (datetime(2026, mes_fech, 27) - timedelta(days=30)).replace(day=28).date()
        
        st.subheader(f"Período: {ini_p.strftime('%d/%m/%Y')} a {fim_p.strftime('%d/%m/%Y')}")
        df_ponto = df_base[(df_base['Tecnico'] == tec_p) & (df_base['Data'].dt.date >= ini_p) & (df_base['Data'].dt.date <= fim_p)]
        df_ponto = df_ponto.copy()
        df_ponto['Dia Semana'] = df_ponto['Data'].dt.strftime('%a %d/%m')
        st.table(df_ponto[['Dia Semana', 'Status']].set_index('Dia Semana').style.map(style_status))

else:
    st.info("Aguardando upload da planilha ESCALA 2026...")
