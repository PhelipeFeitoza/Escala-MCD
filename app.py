import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import calendar

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Escala Field Service", layout="wide")

# 2. FUNÇÃO PARA GERAR DADOS (SIMULANDO SUA PLANILHA)
@st.cache_data
def gerar_dados_ficticios():
    datas = pd.date_range(start='2026-01-01', end='2026-12-31')
    tecnicos = []
    regioes_lista = ['SP-NORTE', 'SP-SUL', 'SP-ABC', 'SUL-POA', 'SUL-CTB', 'NOR-FORTALEZA']
    
    for i in range(1, 81):
        reg = regioes_lista[i % len(regioes_lista)]
        tecnicos.append({'Nome': f'Tecnico {i:02d}', 'Regiao': reg})
    
    base = []
    for t in tecnicos:
        for d in datas:
            status = 'FG' if d.weekday() >= 5 else 'TB'
            base.append({'Data': d, 'Tecnico': t['Nome'], 'Regiao': t['Regiao'], 'Status': status})
    return pd.DataFrame(base)

df_base = gerar_dados_ficticios()

# 3. FUNÇÃO DE ESTILO
def style_status(val):
    if not isinstance(val, str): return ''
    color_map = {
        'TB': 'background-color: #C8E6C9; color: black;', # Verde
        'FG': 'background-color: #BBDEFB; color: black;', # Azul
        'LM': 'background-color: #FFCDD2; color: black;', # Vermelho
        'FT': 'background-color: #EF9A9A; color: black;', # Vermelho Forte
        'TR': 'background-color: #FFF9C4; color: black;', # Amarelo
        'PV': 'background-color: #E1BEE7; color: black;'  # Roxo
    }
    # Busca a sigla no texto (ex: "15 - TB")
    for sigla in color_map:
        if sigla in val:
            return color_map[sigla]
    return ''

# 4. BARRA LATERAL
st.sidebar.title("Configurações")
visao = st.sidebar.selectbox("Escolha a Visão:", 
    ["Calendário (Individual Técnico)", "Mensal (Empilhado Gestor)", "Semanal (Empilhado Gestor)", "Espelho de Ponto (28-27)"])

# 5. LÓGICA DAS VISÕES

if visao == "Calendário (Individual Técnico)":
    st.header("🗓️ Meu Calendário Mensal")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        tecnico_sel = st.selectbox("Selecione o Técnico:", df_base['Nome'].unique())
    with col_t2:
        mes_sel = st.selectbox("Selecione o Mês:", range(1, 13), index=datetime.now().month - 1, format_func=lambda x: calendar.month_name[x])
    
    ano_sel = 2026
    
    # Gerar a matriz do calendário
    cal = calendar.monthcalendar(ano_sel, mes_sel)
    df_cal = pd.DataFrame(cal, columns=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'])
    
    # Preencher a matriz com o Status
    for row in range(len(df_cal)):
        for col in range(7):
            dia = df_cal.iloc[row, col]
            if dia != 0:
                data_buscada = datetime(ano_sel, mes_sel, dia)
                status = df_base[(df_base['Tecnico'] == tecnico_sel) & (df_base['Data'] == data_buscada)]['Status'].values[0]
                df_cal.iloc[row, col] = f"{dia} - {status}"
            else:
                df_cal.iloc[row, col] = ""

    # Aplicar Estilo e exibir
    st.table(df_cal.style.applymap(style_status))
    st.info("💡 Legenda: TB (Trabalho), FG (Folga), LM (Licença Médica), PV (Preventiva), TR (Treinamento)")

elif visao == "Mensal (Empilhado Gestor)":
    mes = st.sidebar.slider("Mês:", 1, 12, 4)
    st.header(f"📆 Visão Mensal Gestor - Mês {mes}")
    df_month = df_base[df_base['Data'].dt.month == mes].pivot(index=['Regiao', 'Tecnico'], columns='Data', values='Status')
    df_month.columns = [f"{d.strftime('%a %d/%m')}" for d in df_month.columns]
    # Usando map no lugar de applymap para evitar o erro de versão
    st.dataframe(df_month.style.map(style_status), height=600)

elif visao == "Semanal (Empilhado Gestor)":
    st.header("📅 Visão Semanal Gestor")
    data_ref = st.date_input("Semana do dia:", datetime(2026, 4, 13))
    ini = data_ref - timedelta(days=data_ref.weekday())
    fim = ini + timedelta(days=6)
    mask = (df_base['Data'].dt.date >= ini) & (df_base['Data'].dt.date <= fim)
    df_week = df_base[mask].pivot(index=['Regiao', 'Tecnico'], columns='Data', values='Status')
    df_week.columns = [f"{d.strftime('%a %d/%m')}" for d in df_week.columns]
    st.dataframe(df_week.style.map(style_status), use_container_width=True)

elif visao == "Espelho de Ponto (28-27)":
    st.header("📋 Conferência de Espelho de Ponto (28 a 27)")
    tecnico_sel = st.selectbox("Selecione o Técnico:", df_base['Tecnico'].unique())
    mes_ponto = st.selectbox("Mês de Fechamento:", ["Abril (28/03 a 27/04)", "Maio (28/04 a 27/05)"])

    if "Abril" in mes_ponto:
        d_ini, d_fim = datetime(2026, 3, 28), datetime(2026, 4, 27)
    else:
        d_ini, d_fim = datetime(2026, 4, 28), datetime(2026, 5, 27)

    df_ponto = df_base[(df_base['Data'] >= d_ini) & (df_base['Data'] <= d_fim) & (df_base['Tecnico'] == tecnico_sel)].copy()
    df_ponto['Dia'] = df_ponto['Data'].dt.strftime('%a %d/%m')
    
    st.table(df_ponto[['Dia', 'Status']].set_index('Dia').style.map(style_status))
