import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Escala Field Service", layout="wide")

# 2. FUNÇÃO PARA GERAR DADOS (SIMULANDO SUA PLANILHA)
@st.cache_data
def gerar_dados_ficticios():
    datas = pd.date_range(start='2026-01-01', end='2026-12-31')
    # Simulando 80 técnicos com suas regiões
    tecnicos = []
    regioes_lista = ['SP-NORTE', 'SP-SUL', 'SP-ABC', 'SUL-POA', 'SUL-CTB', 'NOR-FORTALEZA']
    
    for i in range(1, 81):
        reg = regioes_lista[i % len(regioes_lista)]
        tecnicos.append({'Nome': f'Tecnico {i:02d}', 'Regiao': reg})
    
    base = []
    for t in tecnicos:
        for d in datas:
            # Lógica simples: Sab/Dom é FG, resto é TB
            status = 'FG' if d.weekday() >= 5 else 'TB'
            base.append({
                'Data': d,
                'Tecnico': t['Nome'],
                'Regiao': t['Regiao'],
                'Status': status
            })
    return pd.DataFrame(base)

df_base = gerar_dados_ficticios()

# 3. FUNÇÃO DE ESTILO (CORRIGIDA)
def style_status(val):
    color_map = {
        'TB': 'background-color: #C8E6C9; color: black;', # Verde
        'FG': 'background-color: #BBDEFB; color: black;', # Azul
        'LM': 'background-color: #FFCDD2; color: black;', # Vermelho
        'FT': 'background-color: #EF9A9A; color: black;', # Vermelho Forte
        'TR': 'background-color: #FFF9C4; color: black;', # Amarelo
        'PV': 'background-color: #E1BEE7; color: black;'  # Roxo
    }
    return color_map.get(val, '')

# 4. BARRA LATERAL (MENU)
st.sidebar.title("Configurações")
visao = st.sidebar.selectbox("Escolha a Visão:", ["Semanal (Gestor)", "Mensal (Gestor)", "Espelho de Ponto (28-27)", "Anual"])
filtro_regiao = st.sidebar.multiselect("Filtrar por Região:", df_base['Regiao'].unique(), default=df_base['Regiao'].unique())

# Filtrando a base global pelas regiões selecionadas
df_filtrado = df_base[df_base['Regiao'].isin(filtro_regiao)]

# 5. LÓGICA DAS VISÕES
if visao == "Semanal (Gestor)":
    st.header("📅 Visão Semanal Empilhada")
    data_ref = st.date_input("Ver semana do dia:", datetime(2026, 4, 13))
    
    # Cálculo do intervalo da semana
    inicio = data_ref - timedelta(days=data_ref.weekday())
    fim = inicio + timedelta(days=6)
    
    # Filtrar e Pivotar
    mask = (df_filtrado['Data'].dt.date >= inicio) & (df_filtrado['Data'].dt.date <= fim)
    df_week = df_filtrado[mask].pivot(index=['Regiao', 'Tecnico'], columns='Data', values='Status')
    
    # Formatar cabeçalho: "seg 13/04"
    df_week.columns = [f"{d.strftime('%a')} {d.strftime('%d/%m')}" for d in df_week.columns]
    
    st.dataframe(df_week.style.applymap(style_status), use_container_width=True)

elif visao == "Mensal (Gestor)":
    mes = st.sidebar.slider("Mês:", 1, 12, 4)
    st.header(f"📆 Visão Mensal Empilhada - Mês {mes}")
    
    mask = (df_filtrado['Data'].dt.month == mes)
    df_month = df_filtrado[mask].pivot(index=['Regiao', 'Tecnico'], columns='Data', values='Status')
    
    # Formatar cabeçalho
    df_month.columns = [f"{d.strftime('%a %d/%m')}" for d in df_month.columns]
    
    st.dataframe(df_month.style.applymap(style_status), height=600)

elif visao == "Espelho de Ponto (28-27)":
    st.header("📋 Conferência de Espelho de Ponto (28 a 27)")
    
    # Seletores específicos para o Ponto
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        tecnico_sel = st.selectbox("Selecione o Técnico:", df_filtrado['Tecnico'].unique())
    with col_p2:
        mes_ponto = st.selectbox("Mês de Fechamento:", ["Abril (28/03 a 27/04)", "Maio (28/04 a 27/05)"])

    # Lógica de datas do ponto
    if "Abril" in mes_ponto:
        d_ini, d_fim = datetime(2026, 3, 28), datetime(2026, 4, 27)
    else:
        d_ini, d_fim = datetime(2026, 4, 28), datetime(2026, 5, 27)

    mask_ponto = (df_filtrado['Data'] >= d_ini) & (df_filtrado['Data'] <= d_fim) & (df_filtrado['Tecnico'] == tecnico_sel)
    df_resumo = df_filtrado[mask_ponto].copy()
    
    # Adicionando coluna amigável para o técnico
    df_resumo['Dia da Semana'] = df_resumo['Data'].dt.strftime('%A')
    df_resumo['Data Formatada'] = df_resumo['Data'].dt.strftime('%d/%m/%Y')
    
    # Mostrar Resumo de Contagem
    c1, c2, c3 = st.columns(3)
    c1.metric("Dias de Trabalho (TB)", len(df_resumo[df_resumo['Status'] == 'TB']))
    c2.metric("Folgas (FG)", len(df_resumo[df_resumo['Status'] == 'FG']))
    c3.metric("Afastamentos/Faltas", len(df_resumo[df_resumo['Status'].isin(['FT', 'LM'])]))

    # Tabela do Espelho
    st.table(df_resumo[['Data Formatada', 'Dia da Semana', 'Status']].set_index('Data Formatada').style.applymap(style_status))

elif visao == "Anual":
    st.header("🗓️ Visão Anual Completa")
    st.warning("Esta visão contém muitos dados. Use a barra de rolagem lateral.")
    
    df_year = df_filtrado.pivot(index=['Regiao', 'Tecnico'], columns='Data', values='Status')
    st.dataframe(df_year.style.applymap(style_status), height=600)
